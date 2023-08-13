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

    options = parser.parse_args()
    client.run(options.token)


if __name__ == "__main__":
    main()
