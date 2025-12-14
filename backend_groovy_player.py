from __future__ import annotations

import json
import os
import random


class Song:
    def __init__(self, id, title, artist, genre, album, year=None, duration=None, file_path=None):
        self.id = id
        self.title = title
        self.artist = artist
        self.genre = genre
        self.album = album
        self.year = year
        self.duration = duration  # optional string like "3:45"
        self.file_path = file_path

    def __str__(self):
        return f"{self.id}: {self.title} - {self.artist} ({self.genre})"


class User:
    def __init__(self, username, fullname):
        self.username = username
        self.fullname = fullname


class Node:
    def __init__(self, song):
        self.song = song
        self.prev = None
        self.next = None


class DoublyLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def add(self, song: Song):
        new_node = Node(song)
        if self.head is None:
            self.head = self.tail = new_node
        else:
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = new_node
        self.size += 1
        return True

    def delete(self, song_id):
        current = self.head
        while current:
            if current.song.id == song_id:
                if current.prev:
                    current.prev.next = current.next
                else:
                    self.head = current.next
                if current.next:
                    current.next.prev = current.prev
                else:
                    self.tail = current.prev
                self.size -= 1
                return True
            current = current.next
        return False

    def search(self, keyword):
        results = []
        current = self.head
        keyword = keyword.lower()
        while current:
            s = current.song
            if (keyword in (s.title or '').lower() or keyword in (s.artist or '').lower() or keyword in (s.genre or '').lower()):
                results.append(s)
            current = current.next
        return results

    def get_all(self):
        songs = []
        current = self.head
        while current:
            songs.append(current.song)
            current = current.next
        return songs

    def find_by_id(self, song_id):
        current = self.head
        while current:
            if current.song.id == song_id:
                return current.song
            current = current.next
        return None


class Queue:
    def __init__(self):
        self.items = []

    def enqueue(self, song):
        self.items.append(song)

    def dequeue(self):
        return self.items.pop(0) if self.items else None

    def get_all(self):
        return self.items.copy()


class Stack:
    def __init__(self):
        self.items = []

    def push(self, song):
        if len(self.items) >= 20:
            self.items.pop(0)
        self.items.append(song)

    def get_all(self):
        return self.items.copy()


class MusicPlayer:
    """Core player logic and in-memory data storage."""
    def __init__(self):
        self.library = DoublyLinkedList()

        # Multi-playlist: key=playlist name, value=DoublyLinkedList()
        self.playlists = {}
        self.current_playlist_name = "My Playlist"

        self.queue = Queue()
        self.history = Stack()
        self.favorites = set()
        self.current_song = None
        self.is_playing = False
        self.current_mode = "library"
        self.list_order = "asc"

        # Load saved data
        self.load_library()
        self.load_playlists()   # load playlists after library so IDs resolve correctly

        # Ensure at least one playlist exists
        if not self.playlists:
            self.playlists[self.current_playlist_name] = DoublyLinkedList()
            self.save_playlists()

    def get_next_id(self):
        songs = self.library.get_all()
        return max([s.id for s in songs], default=0) + 1

    def _norm(self, v):
        try:
            return (v or "").strip().lower()
        except Exception:
            return ""

    def library_has_duplicate(self, title: str, artist: str, file_path: str):
        """Cek duplikasi lagu di library.
        Prioritas: file_path sama (lebih akurat), lalu title+artist sama (case-insensitive).
        """
        t = self._norm(title)
        a = self._norm(artist)

        fp_in = None
        try:
            if file_path:
                fp_in = os.path.normcase(os.path.normpath(file_path))
        except Exception:
            fp_in = None

        for s in self.library.get_all():
            # check file path duplicate
            try:
                if fp_in and s.file_path:
                    fp2 = os.path.normcase(os.path.normpath(s.file_path))
                    if fp2 == fp_in:
                        return True
            except Exception:
                pass

            # check title+artist duplicate
            if t and a:
                if self._norm(s.title) == t and self._norm(s.artist) == a:
                    return True

        return False

    #  playlist persistence (multi-playlist) 
    def save_playlists(self):
        """Simpan semua playlist ke playlists.json sebagai dict {nama_playlist: [id_lagu, ...]}."""
        try:
            data = {}
            for name, dll in self.playlists.items():
                data[name] = [song.id for song in dll.get_all()]
            with open("playlists.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Failed to save playlists:", e)

    def load_playlists(self):
        """Muat semua playlist dari playlists.json. Jika hanya ada playlist.json lama, migrasikan."""
        try:
            # Migration: old single-playlist file
            if (not os.path.isfile("playlists.json")) and os.path.isfile("playlist.json"):
                with open("playlist.json", "r") as f:
                    ids = json.load(f)
                dll = DoublyLinkedList()
                seen = set()
                for song_id in ids:
                    if song_id in seen:
                        continue
                    seen.add(song_id)
                    song = self.library.find_by_id(song_id)
                    if song:
                        dll.add(song)
                self.playlists[self.current_playlist_name] = dll
                # save as new format
                self.save_playlists()
                return

            if not os.path.isfile("playlists.json"):
                return

            with open("playlists.json", "r") as f:
                data = json.load(f)

            # rebuild playlists using songs from library
            for name, ids in (data or {}).items():
                dll = DoublyLinkedList()
                seen = set()
                for song_id in ids:
                    if song_id in seen:
                        continue
                    seen.add(song_id)
                    song = self.library.find_by_id(song_id)
                    if song:
                        dll.add(song)
                self.playlists[name] = dll

        except Exception as e:
            print("Failed to load playlists:", e)

    def create_playlist(self, name: str):
        name = (name or "").strip()
        if not name:
            return False
        if name not in self.playlists:
            self.playlists[name] = DoublyLinkedList()
            self.save_playlists()
        return True

    def get_playlist_names(self):
        return list(self.playlists.keys())

    def get_playlist(self, name: str):
        return self.playlists.get(name)

    def add_to_playlist(self, playlist_name: str, song_id: int):
        if playlist_name not in self.playlists:
            self.create_playlist(playlist_name)

        song = self.library.find_by_id(song_id)
        if not song:
            return False

        # Prevent duplicates inside the same playlist
        try:
            if self.playlists[playlist_name].find_by_id(song_id) is not None:
                return False
        except Exception:
            pass

        self.playlists[playlist_name].add(song)
        self.save_playlists()
        return True
    def remove_from_playlist(self, playlist_name: str, song_id: int):
        """Hapus lagu (by id) dari playlist tertentu."""
        if playlist_name not in self.playlists:
            return False
        ok = self.playlists[playlist_name].delete(song_id)
        if ok:
            self.save_playlists()
        return ok


    def remove_song_from_all_playlists(self, song_id: int):
        """Hapus lagu (by id) dari semua playlist."""
        changed = False
        for name, dll in self.playlists.items():
            if dll.delete(song_id):
                changed = True
        if changed:
            self.save_playlists()
        return changed

#  library persistence (optional helpers) 
    def save_library(self):
        """Simpan seluruh library ke songs.json (dipakai jika ingin persist library)."""
        try:
            data = []
            for s in self.library.get_all():
                data.append({
                    "id": s.id,
                    "title": s.title,
                    "artist": s.artist,
                    "genre": s.genre,
                    "album": s.album,
                    "year": s.year,
                    "duration": s.duration,
                    "file_path": s.file_path
                })
            with open("songs.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Failed to save library:", e)

    def load_library(self):
        try:
            with open("songs.json", "r") as f:
                data = json.load(f)

            for s in data:
                song = Song(
                    s.get("id"),
                    s.get("title"),
                    s.get("artist"),
                    s.get("genre"),
                    s.get("album"),
                    s.get("year"),
                    s.get("duration"),
                    s.get("file_path")
                )
                # avoid duplicates when loading (by id, file_path, or title+artist)
                if self.library.find_by_id(song.id) is None and (not self.library_has_duplicate(song.title, song.artist, song.file_path)):
                    self.library.add(song)

        except FileNotFoundError:
            pass  # tidak ada file? biarkan library kosong
        except Exception as e:
            print("Failed to load library:", e)

    #  navigation helpers 
    def find_similar_song(self, current_song):
        songs = self.library.get_all()
        candidates = [s for s in songs if s.id != current_song.id]
        if not candidates:
            return None
        same_artist = [s for s in candidates if s.artist == current_song.artist]
        if same_artist:
            return same_artist[0]
        same_genre = [s for s in candidates if s.genre == current_song.genre]
        if same_genre:
            return same_genre[0]
        return random.choice(candidates)

    def _get_ordered_list(self):
        """Return list following current_mode and list_order so next/prev follow visual order."""
        if self.current_mode == "playlist":
            pll = self.playlists.get(self.current_playlist_name)
            if pll is None:
                pll = self.playlists.get("My Playlist")
            base = pll.get_all() if pll else []
        else:
            base = self.library.get_all()
        if self.list_order == "desc":
            return list(reversed(base))
        return base

    def next_song(self):
        songs = self._get_ordered_list()
        if not songs or not self.current_song:
            return None
        try:
            idx = next(i for i, s in enumerate(songs) if s.id == self.current_song.id)
            if idx < len(songs) - 1:
                return songs[idx + 1]
        except StopIteration:
            pass
        # fallback: similar
        return self.find_similar_song(self.current_song) if self.current_song else None

    def prev_song(self):
        songs = self._get_ordered_list()
        if not songs or not self.current_song:
            return None
        try:
            idx = next(i for i, s in enumerate(songs) if s.id == self.current_song.id)
            if idx > 0:
                return songs[idx - 1]
        except StopIteration:
            pass
        # fallback: similar
        return self.find_similar_song(self.current_song) if self.current_song else None
