"""Controller layer for Groovy Player.

Contains:
- AdminController
- UserController
"""

from __future__ import annotations

from backend_groovy_player import MusicPlayer, Song


class AdminController:
    def __init__(self, player: MusicPlayer):
        self.player = player

    def list_songs(self):
        return self.player.library.get_all()

    def add_song(self, title, artist, genre, album, year, duration, file_path):
        # Prevent duplicate songs in library
        try:
            if self.player.library_has_duplicate(title, artist, file_path):
                return False, "Duplicate song detected (already exists in Library)."
        except Exception:
            # If duplicate check fails for any reason, continue (fail-open) to avoid blocking.
            pass

        try:
            song = Song(self.player.get_next_id(), title, artist, genre, album,
                        int(year) if year else None, duration, file_path)
            self.player.library.add(song)
            # persist library
            try:
                self.player.save_library()
            except Exception:
                pass
            return True, "Song added"
        except Exception as e:
            return False, str(e)

    def delete_song(self, song_id):
        ok = self.player.library.delete(song_id)

        # also remove from ALL playlists (ignore if not present)
        try:
            self.player.remove_song_from_all_playlists(song_id)
        except Exception:
            pass

        # persist library
        try:
            self.player.save_library()
        except Exception:
            pass
        return ok


class UserController:
    """Contains user-facing operations (search, playlists, favs, history)."""
    def __init__(self, player: MusicPlayer):
        self.player = player

    def search(self, keyword):
        return self.player.library.search(keyword)

    # ---- multi-playlist operations ----
    def create_playlist(self, name: str):
        return self.player.create_playlist(name)

    def get_playlists(self):
        return self.player.get_playlist_names()

    def get_playlist_songs(self, playlist_name: str):
        pll = self.player.get_playlist(playlist_name)
        return pll.get_all() if pll else []

    def add_to_playlist(self, song_id, playlist_name="My Playlist"):
        return self.player.add_to_playlist(playlist_name, song_id)
    def remove_from_playlist(self, song_id, playlist_name):
        return self.player.remove_from_playlist(playlist_name, song_id)


    # ---- favorites & history ----
    def toggle_favorite(self, song_id):
        if song_id in self.player.favorites:
            self.player.favorites.remove(song_id)
            return False
        self.player.favorites.add(song_id)
        return True

    def get_favorites(self):
        return [s for s in self.player.library.get_all() if s.id in self.player.favorites]

    def get_history(self):
        return list(reversed(self.player.history.get_all()))
