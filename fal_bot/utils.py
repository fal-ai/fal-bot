from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import discord
from discord import app_commands
from httpx import HTTPStatusError

from fal_bot import config
from fal_bot.queue_client import (
    InProgress,
    Queued,
    queue_client,
)


def wrap_source_code(source: str) -> str:
    if len(source) >= 1500:
        source = source[:300] + "[...]" + source[-1200:]

    return f"```\n{source}```"


def on_error(
    interaction: discord.Interaction,
) -> Callable[[HTTPStatusError], Awaitable[None]]:
    async def callback(exception: HTTPStatusError):
        try:
            data = exception.response.json()
        except json.JSONDecodeError:
            data = {"error": exception.response.text}

        message = "Something went wrong during your request.\n"
        message += wrap_source_code(json.dumps(data, indent=4))
        await interaction.edit_original_response(content=message)

    return callback


def format_logs(logs: list[dict[str, Any]], *, max_lines: int = 10) -> str:
    return "\n".join(
        [
            f"{log['message']}"
            for log in logs[-max_lines * 2 :]
            if log["message"].strip()
        ][-max_lines:]
    )


def autocomplete_from(
    options: list[str],
) -> Callable[[discord.Interaction, str], Awaitable[list[app_commands.Choice[str]]]]:
    _max_options = 25

    async def autocomplete(
        interaction: discord.Interaction,
        current: str,
    ):
        if not current:
            return [
                app_commands.Choice(
                    name=choice,
                    value=choice,
                )
                for choice in options[:_max_options]
            ]
        else:
            return [
                app_commands.Choice(
                    name=choice,
                    value=choice,
                )
                for choice in options
                if current.lower() in choice.lower()
            ]

    return autocomplete


async def submit_interactive_task(
    interaction: discord.Interaction,
    url: str,
    /,
    **data,
) -> dict[str, Any]:
    async with queue_client(
        url,
        on_error=on_error(interaction),
    ) as client:
        request_handle = await client.submit(data)
        time_start = time.monotonic()

        iteration_id = 0
        async for status in client.poll_until_ready(request_handle):
            match status:
                case Queued(position):
                    message = "Your request is in queue. "
                    message += f"Position: {position + 1}"
                    await interaction.edit_original_response(content=message)
                case InProgress(logs):
                    message = "Your request is in progress "
                    message += "🏃‍♂️" if iteration_id % 2 == 0 else "🚶"
                    message += f"(running for {time.monotonic() - time_start:.2f}s)"
                    message += "."
                    if formatted_logs := format_logs(logs):
                        message += "\n" + wrap_source_code(formatted_logs)

                    await interaction.edit_original_response(content=message)

            iteration_id += 1

        result = await client.result(request_handle)
        return result


def make_prompted_image_embed(
    title: str,
    image_url: str,
    prompt: str,
    fields: dict[str, Any],
):
    embed = discord.Embed(
        title=title,
        description=f"For the full resolution image, click [here]({image_url}).",
    )
    embed.add_field(name="Prompt", value=prompt, inline=False)

    for parameter, value in fields.items():
        embed.add_field(name=parameter, value=value)

    embed.set_image(url=image_url)
    embed.set_footer(
        text="Powered by serverless.fal.ai",
        icon_url=config.FALAI_LOGO_URL,
    )
    return embed


@dataclass
class Timed:
    elapsed: float | None = field(init=False, default=None)
    _start_time: float | None = field(init=False, default=None, repr=False)

    def __enter__(self) -> Timed:
        self._start_time = time.monotonic()
        return self

    def __exit__(self, *args):
        self.elapsed = time.monotonic() - self._start_time
