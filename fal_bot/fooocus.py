import time
from dataclasses import dataclass
from typing import Any, Literal

import discord
from discord import app_commands

from fal_bot import config, utils
from fal_bot.consts import FOOOCUS_ASPECT_RATIOS, FOOOCUS_STYLES
from fal_bot.queue_client import InProgress, Queued, queue_client

FOOOCUS_BASE_URL = "https://110602490-fooocus.gateway.alpha.fal.ai"

DEFAULT_STYLES = FOOOCUS_STYLES[:24]
KEEP_STYLE = "keep"


def style_selector() -> list[discord.SelectOption]:
    options = [
        discord.SelectOption(
            label="Keep current style",
            value=KEEP_STYLE,
        )
    ]
    for style in DEFAULT_STYLES:
        options.append(
            discord.SelectOption(
                label=" ".join(style.split("-")).title(),
                value=style,
            )
        )

    return options


@dataclass
class RegenerateView(discord.ui.View):
    original_interaction: discord.Interaction
    options: dict[str, Any]

    def __post_init__(self) -> None:
        super().__init__()

    async def remove_view(self) -> None:
        await self.original_interaction.edit_original_response(view=None)

    async def on_timeout(self) -> None:
        await self.remove_view()
        await super().on_timeout()

    @discord.ui.select(
        placeholder="Change style",
        min_values=1,
        max_values=1,
        options=style_selector(),
    )
    async def with_style(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ):
        await self.remove_view()

        [style] = select.values
        if style == KEEP_STYLE:
            style = self.style

        await command.callback(interaction, **self.options)


@app_commands.command(
    name="generate",
    description="Text to image generation with Fooocus.",
)
@app_commands.autocomplete(style=utils.autocomplete_from(FOOOCUS_STYLES))
@app_commands.autocomplete(aspect_ratio=utils.autocomplete_from(FOOOCUS_ASPECT_RATIOS))
async def command(
    interaction: discord.Interaction,
    prompt: str,
    style: str = "cinematic-default",
    mode: Literal["Speed", "Quality"] = "Speed",
    aspect_ratio: str = "1024x1024",
):
    await interaction.response.send_message("Your request has been received.")
    async with queue_client(
        FOOOCUS_BASE_URL,
        on_error=utils.on_error(interaction),
    ) as client:
        request_handle = await client.submit(
            data={
                "prompt": prompt,
                "style": style,
                "performance": mode,
                "aspect_ratio": aspect_ratio.replace("x", "×"),
            }
        )

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
                    if formatted_logs := utils.format_logs(logs):
                        message += "\n" + utils.wrap_source_code(formatted_logs)

                    await interaction.edit_original_response(content=message)

            iteration_id += 1

        result = await client.result(request_handle)
        image_url = result["images"][0]["url"]
        embed = discord.Embed(
            title="Fooocus Image",
            description=f"For the full resolution image, click [here]({image_url}).",
        )
        embed.add_field(name="Prompt", value=prompt, inline=False)
        embed.add_field(name="Style", value=style)
        embed.add_field(
            name="Total time taken",
            value=f"{time.monotonic() - time_start:.2f}s",
        )
        embed.add_field(name="Mode", value=mode)
        embed.add_field(name="Aspect ratio", value=aspect_ratio)
        embed.set_image(url=image_url)
        embed.set_footer(
            text="Powered by serverless.fal.ai",
            icon_url=config.FALAI_LOGO_URL,
        )

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=RegenerateView(
                interaction,
                options={
                    "prompt": prompt,
                    "style": style,
                    "mode": mode,
                    "aspect_ratio": aspect_ratio,
                },
            ),
        )
