# jarvis-cmd-music

A [Jarvis](https://github.com/alexberardi/jarvis-server) Pantry package that makes "play Korn" work whichever music
service you use. It holds no catalogue and no login: it picks the service, then hands the request to that service's own
package.

## Choosing the service

In the app, open **Music** and pick from the two lists.

| Setting                         | Scope     | Meaning                                       |
| ------------------------------- | --------- | --------------------------------------------- |
| My default music service        | Per user  | Used when you ask. Overrides the household's. |
| Household default music service | Household | Used when you have not chosen your own.       |

The service is chosen in this order:

1. The one you name: "play Korn **on Tidal**".
2. Your own default.
3. The household default.
4. With none set, the first installed service (Spotify, YouTube Music, Tidal, Plex, Emby).

A service you name is never swapped: if its package is not installed, Jarvis says so. If your own default is not installed,
the household default is used; if neither is installed, Jarvis says so.

## Services

| Service       | Package                                                                | Command              |
| ------------- | ---------------------------------------------------------------------- | -------------------- |
| Spotify       | [jarvis-cmd-spotify](https://github.com/opticon454/jarvis-cmd-spotify) | `spotify_play`       |
| YouTube Music | not written yet                                                        | `youtube_music_play` |
| Tidal         | not written yet                                                        | `tidal_play`         |

## Writing a service package

Provide a command named `<id>_play`, where `<id>` is `spotify`, `youtube_music`, `tidal`, `plex` or `emby` (add a new id to
`PROVIDERS` in `music_shared/providers.py` and to the two `enum_values` lists). It takes:

| Parameter | Meaning                                                                                                 |
| --------- | ------------------------------------------------------------------------------------------------------- |
| `query`   | What to play.                                                                                           |
| `kind`    | Optional: `track`, `album`, `artist` or `playlist`. Left out when unsure: prefer an exact artist match. |
| `artist`  | Optional, narrows a song or album.                                                                      |

It returns a normal `CommandResponse`, which is spoken as it is.

## Tests

```bash
PYTHONPATH=/path/to/jarvis-command-sdk python3 -m pytest
```

The tests replace the command invoker, so no node, account or network is needed.

## Licence

Apache-2.0. Not affiliated with Spotify, YouTube, Google or TIDAL.
