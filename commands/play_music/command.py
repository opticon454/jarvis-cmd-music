"""PlayMusicCommand: "play Korn" on whichever music service is the default.

It holds no catalogue or login. It picks the service (see music_shared.providers) and runs that service's own package
command, so adding a service means installing its package, nothing here.
"""

import sys
from pathlib import Path
from typing import Any, List, Optional

for _candidate in ("music_shared", "lib"):
    _lib_dir: str = str(Path.home() / ".jarvis" / "packages" / "music" / _candidate)
    if _lib_dir not in sys.path:
        sys.path.insert(0, _lib_dir)

from jarvis_command_sdk import (
    CommandExample,
    CommandResponse,
    IJarvisCommand,
    IJarvisSecret,
    JarvisParameter,
    JarvisSecret,
    JarvisStorage,
    RequestInformation,
    invoke_command,
)

from music_shared.providers import PROVIDERS, choose, normalise, run_first_installed

KINDS = ["track", "album", "artist", "playlist"]


class PlayMusicCommand(IJarvisCommand):
    """Voice play on the default music service."""

    def __init__(self) -> None:
        self._storage = JarvisStorage("music")

    @property
    def command_name(self) -> str:
        return "play_music"

    @property
    def description(self) -> str:
        return (
            "Play music: a song, album, artist or playlist, on the user's default music service. query is what to "
            "play. Only set provider when the user names a service (Spotify, YouTube Music, Tidal, Plex, Emby). Use for any "
            "'play ...' request about music, e.g. 'play Korn' or 'play Freak on a Leash by Korn'."
        )

    @property
    def associated_service(self) -> Optional[str]:
        return "Music"

    @property
    def keywords(self) -> List[str]:
        return ["play", "music", "song", "album", "artist", "playlist", "put on", "listen to"]

    @property
    def parameters(self) -> List[JarvisParameter]:
        return [
            JarvisParameter("query", "string", required=True,
                            description="What to play: a song, album, artist or playlist name, without the service"),
            JarvisParameter("kind", "string", required=False, enum_values=KINDS,
                            description="track, album, artist or playlist. Leave empty when unsure."),
            JarvisParameter("artist", "string", required=False,
                            description="The artist, when the user named one for a song or album"),
            JarvisParameter("provider", "string", required=False, enum_values=list(PROVIDERS),
                            description="Only when the user names a service: spotify, youtube_music, tidal, plex or emby"),
        ]

    @property
    def required_secrets(self) -> List[IJarvisSecret]:
        choices = list(PROVIDERS)
        return [
            JarvisSecret("MUSIC_USER_PROVIDER", "Your own default music service. Leave empty to use the household's.",
                         "user", "string", required=False, is_sensitive=False, friendly_name="My default music service",
                         enum_values=choices),
            JarvisSecret("MUSIC_DEFAULT_PROVIDER", "The household's default music service", "integration", "string",
                         required=False, is_sensitive=False, friendly_name="Household default music service",
                         enum_values=choices),
        ]

    @property
    def setup_guide(self) -> Optional[str]:
        return (
            "## Choose your music service\n\n"
            "Install the package for each service you use (Spotify, YouTube Music, Tidal), then pick the default here. "
            "\"Play Korn\" uses *your* default, then the household's. Naming a service (\"play Korn on Tidal\") always "
            "wins. With no default set, the first installed service is used.\n"
        )

    def generate_prompt_examples(self) -> List[CommandExample]:
        return [
            CommandExample("Play Korn", {"query": "Korn", "kind": "artist"}, is_primary=True),
            CommandExample("Play Freak on a Leash by Korn", {"query": "Freak on a Leash", "kind": "track", "artist": "Korn"}),
            CommandExample("Play Korn on Tidal", {"query": "Korn", "kind": "artist", "provider": "tidal"}),
        ]

    def generate_adapter_examples(self) -> List[CommandExample]:
        rows = [
            ("Play Metallica", "Metallica", "artist", None, None),
            ("Put on some Tame Impala", "Tame Impala", "artist", None, None),
            ("Play Bohemian Rhapsody", "Bohemian Rhapsody", "track", None, None),
            ("Play Back in Black by AC/DC", "Back in Black", "track", "AC/DC", None),
            ("Play the album Rumours", "Rumours", "album", None, None),
            ("Play my Chill Hits playlist", "Chill Hits", "playlist", None, None),
            ("I want to listen to Nirvana", "Nirvana", "artist", None, None),
            ("Play Hysteria by Muse on Tidal", "Hysteria", "track", "Muse", "tidal"),
            ("Play Daft Punk from YouTube Music", "Daft Punk", "artist", None, "youtube_music"),
        ]
        out = []
        for text, query, kind, artist, provider in rows:
            params = {"query": query, "kind": kind}
            if artist:
                params["artist"] = artist
            if provider:
                params["provider"] = provider
            out.append(CommandExample(text, params))
        return out

    def run(self, request_info: RequestInformation, **kwargs: Any) -> CommandResponse:
        query = str(kwargs.get("query") or "").strip()
        if not query:
            return CommandResponse.error_response(error_details="What would you like me to play?",
                                                  context_data={"error": "missing_query"})
        said = kwargs.get("provider")
        if said and not normalise(said):
            return CommandResponse.error_response(
                error_details=f"I don't know how to play from {said}. I can use {', '.join(PROVIDERS.values())}.",
                context_data={"error": "unknown_provider"})
        order = choose(said, self._storage.get_secret("MUSIC_USER_PROVIDER", "user"),
                       self._storage.get_secret("MUSIC_DEFAULT_PROVIDER", "integration"))
        args = {"query": query}
        if kwargs.get("kind"):  # left out when unsure: a provider decides (and its enum has no "auto")
            args["kind"] = kwargs["kind"]
        if kwargs.get("artist"):
            args["artist"] = kwargs["artist"]
        provider, response = run_first_installed(order, lambda cmd: invoke_command(cmd, request_info, **args))
        if response is None:
            names = " or ".join(PROVIDERS[p] for p in order[:2]) if len(order) < len(PROVIDERS) else "a music service"
            return CommandResponse.error_response(
                error_details=f"I can't play that because {names} isn't set up on this node. Install its package in the app.",
                context_data={"error": "no_provider"})
        return response
