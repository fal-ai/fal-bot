import json
from typing import Any

import discord
from httpx import HTTPStatusError


def wrap_source_code(source: str) -> str:
    if len(source) >= 1500:
        source = source[:300] + "[...]" + source[-1200:]

    return f"```\n{source}```"


def on_error(interaction: discord.Interaction):
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
