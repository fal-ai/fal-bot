import asyncio
from argparse import ArgumentParser

from fal_bot import config
from fal_bot.bot import client


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--token",
        type=str,
        help="Overwrite discord bot token",
        default=config.DISCORD_TOKEN,
    )
    parser.add_argument(
        "--sync-only",
        help="Only sync slash commands",
        action="store_true",
    )

    options = parser.parse_args()
    if options.sync_only:
        asyncio.run(client.sync_commands(options.token))
    else:
        client.run(options.token)


if __name__ == "__main__":
    main()
