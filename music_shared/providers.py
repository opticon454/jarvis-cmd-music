"""Which music service plays a request. Pure logic, so it is tested without a node."""

from __future__ import annotations

from typing import Callable, Optional

# id -> how it is spoken. A provider package supplies the command "<id>_play" taking query, kind and artist.
PROVIDERS = {"spotify": "Spotify", "youtube_music": "YouTube Music", "tidal": "Tidal"}


def command_for(provider: str) -> str:
    return f"{provider}_play"


def normalise(value: Optional[str]) -> Optional[str]:
    """'YouTube Music', 'youtube-music' and 'youtube_music' are the same service; unknown names give None."""
    key = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return key if key in PROVIDERS else None


def choose(said: Optional[str], user_default: Optional[str], household_default: Optional[str]) -> list[str]:
    """Providers to try, in order. A named service is the only one tried (the user asked for it by name); otherwise the
    user's own default, then the household's, then every known service in turn so a lone installed one still works."""
    named = normalise(said)
    if named:
        return [named]
    first = [p for p in (normalise(user_default), normalise(household_default)) if p]
    return [*dict.fromkeys(first)] or list(PROVIDERS)


def run_first_installed(order: list[str], invoke: Callable[[str], object]) -> tuple[Optional[str], object]:
    """Run the first provider whose command exists (invoke returns None when it does not)."""
    for provider in order:
        response = invoke(command_for(provider))
        if response is not None:
            return provider, response
    return None, None
