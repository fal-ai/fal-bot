import importlib

import discord
from discord import app_commands

from fal_bot.config import RAW_GUILD_ID

MODULES = [
    "fal_bot.fooocus",
]


class FalBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def load_module(self, module_name: str) -> None:
        module = importlib.import_module(module_name)
        self.tree.add_command(module.command)  # type: ignore

    async def setup_hook(self):
        for module in MODULES:
            await self.load_module(module)

        guild = discord.Object(id=int(RAW_GUILD_ID))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


client = FalBot()


@client.event
async def on_ready():
    print("------")
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print("------")


@client.tree.command()
async def hello(interaction: discord.Interaction):
    """Says hello!"""
    await interaction.response.send_message(f"Hi, {interaction.user.mention}")
