from dataclasses import dataclass
from typing import Any, Literal

import discord
from discord import app_commands

from fal_bot import utils
from fal_bot.consts import FOOOCUS_ASPECT_RATIOS, FOOOCUS_STYLES

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
    description="Generate an image from the given prompt with the Fooocus model.",
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
    with utils.Timed() as timer:
        result = await utils.submit_interactive_task(
            interaction,
            FOOOCUS_BASE_URL,
            prompt=prompt,
            style=style,
            performance=mode,
            aspect_ratio=aspect_ratio.replace("x", "×"),
        )

    embed = utils.make_prompted_image_embed(
        title="Fooocus Image",
        image_url=result["images"][0]["url"],
        prompt=prompt,
        fields={
            "Style": style,
            "Time Taken": f"{timer.elapsed:.2f}s",
            "Mode": mode,
            "Aspect Ratio": aspect_ratio,
        },
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
