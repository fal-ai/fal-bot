import pprint


def wrap_source_code(source: str) -> str:
    if not isinstance(source, str):
        source = pprint.pformat(source)

    if len(source) >= 1500:
        source = source[:300] + "[...]" + source[-1200:]

    return f"```\n{source}```"
