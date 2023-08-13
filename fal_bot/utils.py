import json
from typing import Any, Awaitable, Callable

import discord
from discord import app_commands
from httpx import HTTPStatusError


def wrap_source_code(source: str) -> str:
    if len(source) >= 1500:
        source = source[:300] + "[...]" + source[-1200:]

    return f"```\n{source}```"


def on_error(
    interaction: discord.Interaction,
) -> Callable[[HTTPStatusError], Awaitable[None]]:
    async def callback(exception: HTTPStatusError):
        data = exception.response.json()

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
