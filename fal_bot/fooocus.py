import asyncio
import time
from functools import partial

import discord
import httpx
from discord import app_commands

from fal_bot import config, utils

API_BASE = "https://110602490-fooocus.gateway.alpha.fal.ai"

AVAILABLE_STYLES = [
    "sai-base",
    "cinematic-default",
    "sai-3d-model",
    "sai-analog film",
    "sai-anime",
    "sai-cinematic",
    "sai-comic book",
    "sai-craft clay",
    "sai-digital art",
    "sai-enhance",
    "sai-fantasy art",
    "sai-isometric",
    "sai-line art",
    "sai-lowpoly",
    "sai-neonpunk",
    "sai-origami",
    "sai-photographic",
    "sai-pixel art",
    "sai-texture",
    "ads-advertising",
    "ads-automotive",
    "ads-corporate",
    "ads-fashion editorial",
    "ads-food photography",
    "ads-luxury",
    "ads-real estate",
    "ads-retail",
    "artstyle-abstract",
    "artstyle-abstract expressionism",
    "artstyle-art deco",
    "artstyle-art nouveau",
    "artstyle-constructivist",
    "artstyle-cubist",
    "artstyle-expressionist",
    "artstyle-graffiti",
    "artstyle-hyperrealism",
    "artstyle-impressionist",
    "artstyle-pointillism",
    "artstyle-pop art",
    "artstyle-psychedelic",
    "artstyle-renaissance",
    "artstyle-steampunk",
    "artstyle-surrealist",
    "artstyle-typography",
    "artstyle-watercolor",
    "futuristic-biomechanical",
    "futuristic-biomechanical cyberpunk",
    "futuristic-cybernetic",
    "futuristic-cybernetic robot",
    "futuristic-cyberpunk cityscape",
    "futuristic-futuristic",
    "futuristic-retro cyberpunk",
    "futuristic-retro futurism",
    "futuristic-sci-fi",
    "futuristic-vaporwave",
    "game-bubble bobble",
    "game-cyberpunk game",
    "game-fighting game",
    "game-gta",
    "game-mario",
    "game-minecraft",
    "game-pokemon",
    "game-retro arcade",
    "game-retro game",
    "game-rpg fantasy game",
    "game-strategy game",
    "game-streetfighter",
    "game-zelda",
    "misc-architectural",
    "misc-disco",
    "misc-dreamscape",
    "misc-dystopian",
    "misc-fairy tale",
    "misc-gothic",
    "misc-grunge",
    "misc-horror",
    "misc-kawaii",
    "misc-lovecraftian",
    "misc-macabre",
    "misc-manga",
    "misc-metropolis",
    "misc-minimalist",
    "misc-monochrome",
    "misc-nautical",
    "misc-space",
    "misc-stained glass",
    "misc-techwear fashion",
    "misc-tribal",
    "misc-zentangle",
    "papercraft-collage",
    "papercraft-flat papercut",
    "papercraft-kirigami",
    "papercraft-paper mache",
    "papercraft-paper quilling",
    "papercraft-papercut collage",
    "papercraft-papercut shadow box",
    "papercraft-stacked papercut",
    "papercraft-thick layered papercut",
    "photo-alien",
    "photo-film noir",
    "photo-hdr",
    "photo-long exposure",
    "photo-neon noir",
    "photo-silhouette",
    "photo-tilt-shift",
]

DEFAULT_STYLES = AVAILABLE_STYLES[:25]


async def style_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    if not current:
        return [
            app_commands.Choice(name=choice, value=choice) for choice in DEFAULT_STYLES
        ]
    else:
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in AVAILABLE_STYLES
            if current.lower() in choice.lower()
        ]


class RegenerateView(discord.ui.View):
    def __init__(
        self,
        interaction: discord.Interaction,
        prompt: str,
        style: str,
        *args,
        **kwargs,
    ) -> None:
        self.original_interaction = interaction
        self.prompt = prompt
        self.style = style
        super().__init__(*args, **kwargs, timeout=60)

    async def remove_view(self) -> None:
        await self.original_interaction.edit_original_response(view=None)

    async def on_timeout(self) -> None:
        await self.remove_view()
        await super().on_timeout()

    async def with_style(
        self,
        select: discord.ui.Select,
        interaction: discord.Interaction,
    ):
        await self.remove_view()
        await command.callback(interaction, prompt=self.prompt, style=select.values[0])


@app_commands.command(
    name="generate",
    description="Text to image generation with Fooocus.",
)
@app_commands.autocomplete(style=style_autocomplete)
async def command(
    interaction: discord.Interaction,
    prompt: str,
    style: str = "cinematic-default",
):
    await interaction.response.send_message("Your request has been received.")
    async with httpx.AsyncClient(
        base_url=API_BASE,
        headers={"Authorization": f"Key {config.FAL_SECRET}"},
    ) as client:
        response = await client.post(
            "/fal/queue/submit/",
            json={
                "prompt": prompt,
                "style": style,
            },
        )
        if response.status_code != 200:
            await interaction.edit_original_response(
                content=f"Something went wrong.\n{utils.wrap_source_code(response.json())}"
            )
            return

        time_start = time.monotonic()
        request_id = response.json()["request_id"]
        iteration_id = 0
        while True:
            iteration_id += 1

            response = await client.get(f"/fal/queue/requests/{request_id}/status/")
            if response.status_code == 200:
                break
            elif response.status_code == 404:
                await interaction.edit_original_response(
                    content=f"Something went wrong.\n{utils.wrap_source_code(response.json())}"
                )
                return

            data = response.json()
            if data["status"] == "IN_QUEUE":
                queue_position = data["queue_position"]
                await interaction.edit_original_response(
                    content=f"Your request is in queue. Position: {queue_position + 1}"
                )
            elif data["status"] == "IN_PROGRESS":
                last_10_logs = [
                    f"{log['message']}"
                    for log in data["logs"][-30:]
                    if log["message"].strip()
                    if "Refiner" not in log["message"]
                ][-10:]
                message = "Your request is in progress "
                message += "🏃‍♂️" if iteration_id % 2 == 0 else "🚶"
                message += "."
                if last_10_logs:
                    message += "\n" + utils.wrap_source_code("\n".join(last_10_logs))

                await interaction.edit_original_response(content=message)

            await asyncio.sleep(0.2)

        result = await client.get(f"/fal/queue/requests/{request_id}/response/")
        if result.status_code != 200:
            await interaction.edit_original_response(
                content=f"Something went wrong.\n{utils.wrap_source_code(result.json())}"
            )
            return

        image_url = result.json()["images"][0]["url"]
        embed = discord.Embed(
            title="Fooocus Image",
            description=f"For the full resolution image, click [here]({image_url}).",
        )
        embed.add_field(name="Prompt", value=prompt, inline=False)
        embed.add_field(name="Style", value=style, inline=True)
        embed.add_field(
            name="Total time taken",
            value=f"{time.monotonic() - time_start:.2f}s",
            inline=True,
        )
        embed.set_image(url=image_url)
        embed.set_footer(
            text="Powered by serverless.fal.ai",
            icon_url="https://avatars.githubusercontent.com/u/74778219?s=200&v=4",
        )

        view = RegenerateView(
            interaction,
            prompt=prompt,
            style=style,
        )

        select = discord.ui.Select(
            placeholder="Change style",
            min_values=1,
            max_values=1,
        )
        select.add_option(
            label=f"{style} -- current",
            value=style,
        )
        for example_style in DEFAULT_STYLES[:-1]:
            if example_style == style:
                continue

            select.add_option(
                label=example_style,
                value=example_style,
            )
        select.callback = partial(view.with_style, select)
        view.add_item(select)

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=view,
        )
