import pytest

from commands.play_music import command as mod
from commands.play_music.command import PlayMusicCommand
from jarvis_command_sdk import CommandResponse, IJarvisCommand
from music_shared.providers import PROVIDERS, choose, command_for, normalise, run_first_installed


class TestChoose:
    def test_a_named_service_is_the_only_one_tried(self):
        assert choose("Tidal", "spotify", "youtube_music") == ["tidal"]
        assert choose("YouTube Music", None, None) == ["youtube_music"]

    def test_user_default_then_household_then_everything(self):
        assert choose(None, "tidal", "spotify") == ["tidal", "spotify"]
        assert choose(None, None, "spotify") == ["spotify"]
        assert choose(None, "tidal", "tidal") == ["tidal"]
        assert choose(None, None, None) == list(PROVIDERS)

    def test_unknown_names_are_ignored(self):
        assert normalise("napster") is None and normalise("youtube-music") == "youtube_music"
        assert choose(None, "napster", "spotify") == ["spotify"]
        assert choose("napster", None, "spotify") == ["spotify"]  # the command rejects an unknown name before this


class TestRunFirstInstalled:
    def test_skips_providers_that_are_not_installed(self):
        seen = []

        def invoke(cmd):
            seen.append(cmd)
            return "ok" if cmd == "tidal_play" else None

        assert run_first_installed(["spotify", "tidal"], invoke) == ("tidal", "ok")
        assert seen == ["spotify_play", "tidal_play"]

    def test_nothing_installed(self):
        assert run_first_installed(["spotify"], lambda c: None) == (None, None)

    def test_command_name_contract(self):
        assert command_for("youtube_music") == "youtube_music_play"


class Fake:
    """invoke_command stand-in: `installed` maps a command name to its response."""

    def __init__(self, installed):
        self.installed, self.calls = installed, []

    def __call__(self, name, request_info, /, **args):
        self.calls.append((name, args))
        return self.installed.get(name)


def ok(msg):
    return CommandResponse.success_response(context_data={"message": msg}, wait_for_input=False)


@pytest.fixture
def make(monkeypatch):
    def build(installed, user=None, household=None):
        fake = Fake(installed)
        monkeypatch.setattr(mod, "invoke_command", fake)
        cmd = PlayMusicCommand()
        monkeypatch.setattr(cmd._storage, "get_secret",
                            lambda key, scope=None: {"MUSIC_USER_PROVIDER": user, "MUSIC_DEFAULT_PROVIDER": household}[key],
                            raising=False)
        return cmd, fake
    return build


class TestCommand:
    def test_interface(self):
        cmd = PlayMusicCommand()
        assert isinstance(cmd, IJarvisCommand) and cmd.command_name == "play_music"
        scopes = {s.key: s.scope for s in cmd.required_secrets}
        assert scopes == {"MUSIC_USER_PROVIDER": "user", "MUSIC_DEFAULT_PROVIDER": "integration"}
        assert all(s.enum_values == list(PROVIDERS) and not s.is_sensitive and not s.required for s in cmd.required_secrets)
        assert cmd.generate_adapter_examples() and cmd.generate_prompt_examples()

    def test_plays_on_the_default_service(self, make):
        cmd, fake = make({"tidal_play": ok("Playing Korn.")}, household="tidal")
        assert cmd.run(None, query="Korn", kind="artist").context_data["message"] == "Playing Korn."
        assert fake.calls == [("tidal_play", {"query": "Korn", "kind": "artist"})]

    def test_a_users_own_default_beats_the_households(self, make):
        cmd, fake = make({"spotify_play": ok("s"), "tidal_play": ok("t")}, user="tidal", household="spotify")
        cmd.run(None, query="Korn")
        assert fake.calls[0][0] == "tidal_play"

    def test_naming_a_service_wins_and_kind_defaults_to_auto(self, make):
        cmd, fake = make({"spotify_play": ok("s"), "tidal_play": ok("t")}, household="spotify")
        cmd.run(None, query="Korn", provider="tidal", artist="Korn")
        assert fake.calls == [("tidal_play", {"query": "Korn", "artist": "Korn"})]

    def test_no_default_uses_the_first_installed(self, make):
        cmd, fake = make({"tidal_play": ok("t")})
        cmd.run(None, query="x")
        assert [c[0] for c in fake.calls] == ["spotify_play", "youtube_music_play", "tidal_play"]

    def test_a_default_that_is_not_installed_says_so_and_does_not_play_elsewhere(self, make):
        cmd, fake = make({"spotify_play": ok("s")}, household="tidal")
        r = cmd.run(None, query="x")
        assert "Tidal isn't set up" in r.error_details and [c[0] for c in fake.calls] == ["tidal_play"]

    def test_a_users_default_that_is_not_installed_falls_back_to_the_households(self, make):
        cmd, fake = make({"spotify_play": ok("s")}, user="tidal", household="spotify")
        assert cmd.run(None, query="x").context_data["message"] == "s"
        assert [c[0] for c in fake.calls] == ["tidal_play", "spotify_play"]

    def test_a_named_service_is_never_swapped(self, make):
        cmd, fake = make({"spotify_play": ok("s")}, household="spotify")
        assert "Tidal isn't set up" in cmd.run(None, query="x", provider="tidal").error_details
        assert [c[0] for c in fake.calls] == ["tidal_play"]

    def test_nothing_installed(self, make):
        cmd, _ = make({})
        assert "music service isn't set up" in cmd.run(None, query="x").error_details

    def test_a_providers_own_error_is_passed_through(self, make):
        err = CommandResponse.error_response(error_details="Spotify rejected the client ID")
        cmd, _ = make({"spotify_play": err}, household="spotify")
        assert cmd.run(None, query="x").error_details == "Spotify rejected the client ID"

    def test_missing_query_and_unknown_service(self, make):
        cmd, fake = make({})
        assert "What would you like" in cmd.run(None).error_details
        assert "Napster" in cmd.run(None, query="x", provider="Napster").error_details and not fake.calls
