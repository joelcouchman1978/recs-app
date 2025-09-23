import re
from .settings import settings


_patterns = [re.compile(p, re.IGNORECASE) for p in settings.spoiler_denylist]


class SpoilerError(ValueError):
    pass


def assert_no_spoilers(text: str) -> None:
    if not text:
        return
    for pat in _patterns:
        if pat.search(text):
            raise SpoilerError(f"Spoiler pattern matched: {pat.pattern}")

