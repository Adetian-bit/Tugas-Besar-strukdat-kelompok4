import customtkinter as ctk 
from tkinter import messagebox, filedialog, simpledialog, StringVar
import random
import pygame
import os
import json
import time
import math

# safer init for pygame mixer
try:
    pygame.mixer.init()
except Exception:
    # If audio device unavailable (CI / headless), continue but playback will fail at runtime.
    pass


# BACKEND - MODELS & DS

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
                for song_id in ids:
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
                for song_id in ids:
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
        self.playlists[playlist_name].add(song)
        self.save_playlists()
        return True

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
                # avoid duplicate IDs if repeated load
                if self.library.find_by_id(song.id) is None:
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


# CONTROLLER

class AdminController:
    def __init__(self, player: MusicPlayer):
        self.player = player

    def list_songs(self):
        return self.player.library.get_all()

    def add_song(self, title, artist, genre, album, year, duration, file_path):
        try:
            song = Song(self.player.get_next_id(), title, artist, genre, album, int(year) if year else None, duration, file_path)
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

# UI - CUSTOMTKINTER

class MusicPlayerGUI:
    """The GUI composes the player and controllers. UI/UX methods are kept here."""
    def __init__(self):
        self.player = MusicPlayer()
        self.admin = AdminController(self.player)
        self.user = UserController(self.player)
        self.current_user = None
        self.play_buttons = {}
        self.admin_play_buttons = {}
        self.users = {
            "ade": User("ade", "Ade Tian"),
            "guest": User("guest", "Guest User"),
            "admin": User("admin", "Administrator"),
        }

        # Progress tracking
        self._progress_update_job = None
        self.current_song_length = 0.0  # seconds
        self.progress_value = 0.0

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.window = ctk.CTk()
        self.window.title("Groovy Music Player")
        self.window.geometry("1200x700")
        self.window.configure(fg_color="#0a0a0a")
        # UI attributes created later
        self.now_playing = None
        self.now_artist = None
        self.progress_bar = None
        self.progress_label_elapsed = None
        self.progress_label_total = None

        self.show_login()

    #  helpers 
    def clear_window(self):
        for w in self.window.winfo_children():
            w.destroy()
        self.window.update()

    #  Login / Role selection
    #  Login / Role selection dengan tampilan glassmorphism ungu/biru
    def show_login(self):
        self.clear_window()
        self.window.update()  # TAMBAHKAN INI untuk refresh
        
        # Set background window
        self.window.configure(fg_color="#1a1d2a")

        # Main frame dengan efek glassmorphism
        frame = ctk.CTkFrame(
            self.window, 
            width=450, 
            height=380, 
            corner_radius=15,
            fg_color=("#d8d8e8", "#2a2d3a"),
            border_width=2,
            border_color=("#a8a8d8", "#5a5d7a")
        )
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Spacing dari top
        spacer = ctk.CTkLabel(frame, text="", height=40, fg_color="transparent")
        spacer.pack()
        
        # Title
        ctk.CTkLabel(
            frame,
            text="Login",
            font=("Arial", 28, "bold"),
            text_color=("#2a2d3a", "#e8e8f8")
        ).pack(pady=10)

        # Input Username
        username_frame = ctk.CTkFrame(frame, fg_color="transparent")
        username_frame.pack(pady=10, padx=40)
        
        ctk.CTkLabel(
            username_frame, 
            text="👤", 
            font=("Arial", 16),
            width=30,
            text_color=("#6a6d8a", "#a8a8d8")
        ).pack(side="left", padx=(0, 10))
        
        self.username_entry = ctk.CTkEntry(
            username_frame,
            width=320,
            height=45,
            placeholder_text="Username",
            fg_color=("#e8e8f8", "#3a3d5a"),
            border_width=0,
            corner_radius=5,
            text_color=("#2a2d3a", "#e8e8f8"),
            placeholder_text_color=("#8a8da8", "#a8a8c8")
        )
        self.username_entry.pack(side="left")

        # Input Password
        password_frame = ctk.CTkFrame(frame, fg_color="transparent")
        password_frame.pack(pady=10, padx=40)
        
        ctk.CTkLabel(
            password_frame, 
            text="🔒", 
            font=("Arial", 16),
            width=30,
            text_color=("#6a6d8a", "#a8a8d8")
        ).pack(side="left", padx=(0, 10))
        
        self.password_entry = ctk.CTkEntry(
            password_frame,
            width=320,
            height=45,
            placeholder_text="Password",
            show="*",
            fg_color=("#e8e8f8", "#3a3d5a"),
            border_width=0,
            corner_radius=5,
            text_color=("#2a2d3a", "#e8e8f8"),
            placeholder_text_color=("#8a8da8", "#a8a8c8")
        )
        self.password_entry.pack(side="left")

        # Container untuk tombol Admin dan User
        button_container = ctk.CTkFrame(frame, fg_color="transparent")
        button_container.pack(pady=30, padx=40, fill="x")

        # Tombol Login Admin (perlu validasi username & password)
        admin_btn = ctk.CTkButton(
            button_container,
            text="LOGIN AS ADMIN",
            width=165,
            height=48,
            fg_color=("#6366f1", "#5a5dd1"),
            hover_color=("#4f46e5", "#4a4dc5"),
            corner_radius=5,
            font=("Arial", 12, "bold"),
            text_color="white",
            command=lambda: self.validate_and_login_smooth("admin")
        )
        admin_btn.pack(side="left", padx=(15, 10))

        # Tombol Login User (LANGSUNG MASUK tanpa validasi)
        user_btn = ctk.CTkButton(
            button_container,
            text="LOGIN AS USER",
            width=170,
            height=48,
            fg_color=("#6366f1", "#5a5dd1"),
            hover_color=("#4f46e5", "#4a4dc5"),
            corner_radius=5,
            font=("Arial", 12, "bold"),
            text_color="white",
            command=lambda: self.login_with_loading("guest")
        )
        user_btn.pack(side="left")

    # Fungsi validasi login dengan smooth transition
    def validate_and_login_smooth(self, role):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        # Validasi kredensial HANYA untuk admin
        if username == "admin" and password == "123":
            # Login berhasil - tampilkan loading
            self.login_with_loading(role)
        else:
            # Hapus error lama jika ada
            for widget in self.window.winfo_children():
                if isinstance(widget, ctk.CTkLabel):
                    try:
                        text = widget.cget("text")
                        if "salah" in text.lower() or "username" in text.lower():
                            widget.destroy()
                    except:
                        pass
            
            # Tampilkan pesan error LEBIH BAWAH dan TANPA background
            error_label = ctk.CTkLabel(
                self.window,
                text="Username dan Password belum diisi atau salah!",
                font=("Arial", 13, "bold"),
                text_color="#ff4444",
                fg_color="transparent"  # TRANSPARAN, bukan pakai warna
            )
            error_label.place(relx=0.5, rely=0.75, anchor="center")  # Lebih bawah lagi
            
            # Hapus pesan error setelah 3 detik
            self.window.after(3000, lambda: error_label.destroy() if error_label.winfo_exists() else None)

    # Fungsi untuk smooth loading transition
    def login_with_loading(self, role):
        # Clear semua error message dulu
        for widget in self.window.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                try:
                    text = widget.cget("text")
                    if "salah" in text.lower():
                        widget.destroy()
                except:
                    pass
        
        # Tampilkan loading indicator
        loading = ctk.CTkLabel(
            self.window,
            text="Loading...",
            font=("Arial", 18, "bold"),
            text_color="#6366f1",
            fg_color="transparent"  # TRANSPARAN
        )
        loading.place(relx=0.5, rely=0.75, anchor="center")
        self.window.update()
        
        # Delay sedikit untuk efek smooth (30ms lebih cepat)
        self.window.after(30, lambda: self._finish_login(role, loading))

    def _finish_login(self, role, loading_widget):
        # Hapus loading
        try:
            loading_widget.destroy()
        except:
            pass
        
        # Jalankan login
        self.do_login_direct(role)
   

    def save_library(self):
        # convenience wrapper delegating to player
        self.player.save_library()

    def load_library(self):
        self.player.load_library()

    # login user (tetap ada tapi aman - fallback ke guest jika combobox hilang)
    def do_login(self):
        username = None
        if hasattr(self, "login_user_cb"):
            try:
                username = self.login_user_cb.get()
            except Exception:
                username = None

        if not username:
            username = "guest"

        if username not in self.users:
            messagebox.showerror("Error", "User not found!")
            return

        self.current_user = self.users[username]
        if username == "admin":
            self.show_admin_page()
        else:
            self.show_user_page()


    def do_login_direct(self, username):
        if username not in self.users:
            messagebox.showerror("Error", "User not found!")
            return

        self.current_user = self.users[username]

        if username == "admin":
            self.show_admin_page()
        else:
            self.show_user_page()


    def logout(self):
        self.current_user = None
        
        # Stop music
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        
        # Stop progress updates
        if self._progress_update_job:
            try:
                self.window.after_cancel(self._progress_update_job)
            except Exception:
                pass
            self._progress_update_job = None
        
        # Show login dengan smooth transition
        self.window.after(10, self.show_login)

    def toggle_play(self, song):
        # Jika lagu ini sedang diputar → STOP
        if self.player.current_song == song and self.player.is_playing:
            self.stop_current()

            # Kembalikan ikon semua tombol ke ▶
            for btn in self.play_buttons.values():
                try:
                    btn.configure(text="▶")
                except Exception:
                    pass
            return

        # Jika lagu baru atau sedang pause → PLAY (ikuti mode view saat ini: library / playlist)
        self.play_song(song, self.player.current_mode)


    # ADMIN INTERFACE (ADMIN PAGE & FEATURES)

    def show_admin_page(self):
        self.clear_window()
        
        # Set background dulu
        self.window.configure(fg_color="#0a0a0a")
        self.window.update()
        
        sidebar = ctk.CTkFrame(self.window, width=200, corner_radius=0, fg_color="#0f0f0f")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="⚡ Groovy", font=("Arial", 20, "bold"), text_color="#6366f1").pack(pady=(30, 50))

        menus = [("📚 Library", self.admin_view_songs), ("➕ Add Song", self.admin_add_song), ("🚪 Logout", self.logout)]
        for text, cmd in menus:
            ctk.CTkButton(sidebar, text=text, width=170, height=38, font=("Arial", 13), corner_radius=8,
                        fg_color="transparent", hover_color="#1e293b", anchor="w", command=cmd).pack(pady=4, padx=15)

        self.content = ctk.CTkFrame(self.window, fg_color="#0a0a0a")
        self.content.pack(side="right", fill="both", expand=True, padx=25, pady=25)
        
        # Update UI dulu sebelum load data
        self.window.update()

        # Load songs di thread terpisah atau gunakan after
        self.window.after(10, self.admin_view_songs)

    def admin_view_songs(self):
        for w in self.content.winfo_children():
            w.destroy()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="Library (Admin)", font=("Arial", 24, "bold"), text_color="#ffffff").pack(side="left", padx=(4,0))

        # Admin-level Prev/Next controls (so admin can navigate)
        admin_controls = ctk.CTkFrame(header, fg_color="transparent")
        admin_controls.pack(side="right")
        ctk.CTkButton(admin_controls, text="⏮ Prev", width=90, height=34, command=self.play_prev).pack(side="left", padx=4)
        ctk.CTkButton(admin_controls, text="⏭ Next", width=90, height=34, command=self.play_next).pack(side="left", padx=4)

        table = ctk.CTkFrame(self.content, fg_color="#0f0f0f", corner_radius=12)
        table.pack(fill="both", expand=True, pady=(5,0))

        thead = ctk.CTkFrame(table, fg_color="transparent", height=45)
        thead.pack(fill="x", padx=15, pady=(15, 5))

        cols = [("#", 0.06), ("Title", 0.25), ("Artist", 0.22), ("Genre", 0.15), ("Album", 0.22)]
        x = 0
        for text, w in cols:
            ctk.CTkLabel(thead, text=text, font=("Arial", 11, "bold"), text_color="#64748b", anchor="w").place(relx=x, rely=0.5, anchor="w")
            x += w

        scroll = ctk.CTkScrollableFrame(table, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for song in self.admin.list_songs():
            row = ctk.CTkFrame(scroll, fg_color="#1a1a1a", height=50, corner_radius=8)
            row.pack(fill="x", pady=2)

            data = [(str(song.id), 0.06), (song.title[:22], 0.25), (song.artist[:18], 0.22), (song.genre, 0.15), (song.album[:18], 0.22)]
            x = 0.02
            for val, w in data:
                ctk.CTkLabel(row, text=val, font=("Arial", 11), text_color="#e2e8f0", anchor="w").place(relx=x, rely=0.5, anchor="w")
                x += w

            play_btn = ctk.CTkButton(
                row,
                text="⏵",
                width=60,
                height=32,
                fg_color="#6366f1",
                hover_color="#4f46e5",
                command=lambda s=song: self.admin_toggle_play(s)
            )
            play_btn.place(relx=0.86, rely=0.5, anchor="center")

            self.admin_play_buttons[song.id] = play_btn

            ctk.CTkButton(row, text="Delete", width=70, height=32, font=("Arial", 10), fg_color="#ef4444",
                         hover_color="#dc2626", command=lambda s=song: self.admin_delete(s.id)).place(relx=0.94, rely=0.5, anchor="center")

    def admin_add_song(self):
        for w in self.content.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.content, text="Add New Song", font=("Arial", 32, "bold"),
                    text_color="#ffffff").pack(pady=(0, 25))

        form = ctk.CTkFrame(self.content, fg_color="#0f0f0f", corner_radius=12)
        form.pack(fill="both", expand=True, padx=50, pady=20)

        # simpan ke self agar bisa dipakai save()
        self.entries = {}
        fields = [
            ("Title", "Song title"),
            ("Artist", "Artist name"),
            ("Genre", "Genre"),
            ("Album", "Album name"),
            ("Year", "2020"),
            ("Duration", "3:30"),
            ("File", "Choose song file")
        ]


        row = 0
        for label, placeholder in fields:
            ctk.CTkLabel(form, text=label).grid(row=row, column=0, sticky="w", padx=20, pady=10)

            if label == "File":
                # Entry menunjukkan nama file
                file_entry = ctk.CTkEntry(form, width=400)
                file_entry.grid(row=row, column=1, sticky="w", padx=20, pady=10)

                # Tombol browse
                def choose_file(entry=file_entry):
                    path = filedialog.askopenfilename(
                        title="Select Song File",
                        filetypes=[
                            ("Audio Files", "*.mp3 *.wav *.flac *.m4a"),
                            ("All Files", "*.*")
                        ]
                    )
                    if path:
                        entry.delete(0, "end")
                        entry.insert(0, path)

                browse_btn = ctk.CTkButton(form, text="Browse", width=80,
                                        command=choose_file)
                browse_btn.grid(row=row, column=2, padx=10)
                self.entries[label.lower()] = file_entry

            else:
                # normal entry
                e = ctk.CTkEntry(form, width=400, placeholder_text=placeholder)
                e.grid(row=row, column=1, sticky="w", padx=20, pady=10)
                self.entries[label.lower()] = e
            row += 1


        ctk.CTkButton(form, text="Save Song", width=180, height=42,
                    font=("Arial", 14), fg_color="#6366f1",
                    hover_color="#4f46e5", command=self.save_song)\
                    .grid(row=row, column=1, sticky="e", pady=30)
        
    def admin_toggle_play(self, song):
        # Jika lagu ini yang sedang dimainkan
        if self.player.current_song == song:

            # Jika sedang bermain → PAUSE
            if self.player.is_playing:
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
                self.player.is_playing = False

                # ubah tombol jadi play (resume)
                if song.id in self.admin_play_buttons:
                    try:
                        self.admin_play_buttons[song.id].configure(text="⏵")
                    except Exception:
                        pass
                return

            # Jika sedang PAUSE → RESUME
            else:
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
                self.player.is_playing = True

                if song.id in self.admin_play_buttons:
                    try:
                        self.admin_play_buttons[song.id].configure(text="⏸")
                    except Exception:
                        pass
                return

        # Jika lagu belum dimainkan sama sekali → PLAY LAGU
        # set player mode and ordering so next/prev behave as admin expects (library asc)
        self.play_song(song, "library")
        self.player.list_order = "asc"

        # set semua tombol admin kembali normal
        for btn in self.admin_play_buttons.values():
            try:
                btn.configure(text="⏵")
            except Exception:
                pass

        # tombol lagu yang dimainkan jadi pause
        if song.id in self.admin_play_buttons:
            try:
                self.admin_play_buttons[song.id].configure(text="⏸")
            except Exception:
                pass


    def save_song(self):
        title = self.entries["title"].get().strip()
        artist = self.entries["artist"].get().strip()
        genre = self.entries["genre"].get().strip()
        album = self.entries["album"].get().strip()
        year = self.entries["year"].get().strip()
        duration = self.entries["duration"].get().strip()
        file_path = self.entries["file"].get().strip()

        
        # FILE TETAP WAJIB
        if not file_path or not os.path.isfile(file_path):
            messagebox.showerror("Error", "File lagu wajib dipilih dan harus valid!")
            return

        # DEFAULT VALUE JIKA KOSONG
        title = title if title else "Unknown Title"
        artist = artist if artist else "Unknown Artist"
        genre = genre if genre else "Unknown Genre"
        album = album if album else "Unknown Album"

        # year & duration boleh kosong
        year = year if year else None
        duration = duration if duration else None

        # TAMBAH LAGU KE LIBRARY
        success, msg = self.admin.add_song(
            title, artist, genre, album, year, duration, file_path
        )

        if success:
            messagebox.showinfo("Success", "Lagu berhasil ditambahkan!")
            self.admin_view_songs()  # refresh library
        else:
            messagebox.showerror("Error", msg)


    def admin_delete(self, song_id):
        if messagebox.askyesno("Confirm", "Delete this song?"):
            self.admin.delete_song(song_id)
            self.admin_view_songs()


    # USER INTERFACE (USER PAGE & FEATURES)
    def show_user_page(self):
        self.clear_window()
        
        # Set background dulu
        self.window.configure(fg_color="#0a0a0a")
        self.window.update()

        #  SIDEBAR 
        sidebar = ctk.CTkFrame(self.window, width=200, corner_radius=0, fg_color="#0f0f0f")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="⚡ Groovy", font=("Arial", 20, "bold"), text_color="#6366f1").pack(pady=(30, 10))
        ctk.CTkLabel(sidebar, text="MENU", font=("Arial", 10, "bold"), text_color="#64748b").pack(pady=(20, 10), padx=20, anchor="w")

        menus = [
            ("🏠 Home", self.user_home),
            ("🔍 Search", self.user_search),
            ("📝 Playlist", self.user_playlist),
            ("⭐ Favorites", self.user_favorites),
            ("📜 History", self.user_history)
        ]
        for text, cmd in menus:
            ctk.CTkButton(sidebar, text=text, width=170, height=38, font=("Arial", 13),
                        corner_radius=8, fg_color="transparent",
                        hover_color="#1e293b", anchor="w", command=cmd).pack(pady=3, padx=15)

        ctk.CTkButton(sidebar, text="🚪 Logout", width=170, height=38, font=("Arial", 13),
                    corner_radius=8, fg_color="transparent",
                    hover_color="#1e293b", anchor="w",
                    command=self.logout).pack(side="bottom", pady=20, padx=15)

        #  MAIN CONTENT 
        self.main_content = ctk.CTkFrame(self.window, fg_color="#0a0a0a")
        self.main_content.pack(side="top", fill="both", expand=True)

        #  TOPBAR HARUS DIBUAT DULU 
        topbar = ctk.CTkFrame(self.main_content, height=60, fg_color="transparent")
        topbar.pack(fill="x", padx=25, pady=(15, 0))

        # Search bar
        self.search_entry = ctk.CTkEntry(
            topbar, width=350, height=38,
            placeholder_text="🔍 Search songs...", font=("Arial", 12),
            corner_radius=20, fg_color="#1a1a1a", border_width=0
        )
        self.search_entry.pack(side="left")

        # Logout button (top-right)
        logout_btn = ctk.CTkButton(
            topbar, text="Logout", width=90, height=32,
            fg_color="#1e293b", hover_color="#334155",
            command=self.logout
        )
        logout_btn.pack(side="right", padx=(10, 0))

        # Username label
        user_btn = ctk.CTkLabel(topbar, text=f"👤 {self.current_user.fullname}", font=("Arial", 12))
        user_btn.pack(side="right", padx=(0, 10))

        #  CONTENT AREA 
        self.content = ctk.CTkScrollableFrame(self.main_content, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=25, pady=(10, 120))

        # = PLAYER BAR =
        self.create_player_bottom()
        
        # Update UI dulu sebelum load data
        self.window.update()

        # = AUTO OPEN HOME dengan delay =
        self.window.after(10, self.user_home)



    def create_player_bottom(self):
        player = ctk.CTkFrame(self.window, height=120, fg_color="#0f0f0f")
        player.place(relx=0, rely=1, anchor="sw", relwidth=1)

        info = ctk.CTkFrame(player, fg_color="transparent")
        info.place(relx=0.02, rely=0.15, anchor="nw")

        self.now_playing = ctk.CTkLabel(info, text="No song playing", font=("Arial", 13, "bold"), text_color="#ffffff")
        self.now_playing.pack(anchor="w")

        self.now_artist = ctk.CTkLabel(info, text="", font=("Arial", 11), text_color="#94a3b8")
        self.now_artist.pack(anchor="w")

        # Progress area
        progress_frame = ctk.CTkFrame(player, fg_color="transparent")
        progress_frame.place(relx=0.22, rely=0.18, anchor="w", relwidth=0.56)

        self.progress_label_elapsed = ctk.CTkLabel(progress_frame, text="00:00", font=("Arial", 10), text_color="#94a3b8")
        self.progress_label_elapsed.pack(side="left", padx=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(side="left", expand=True, fill="x", pady=8)

        self.progress_label_total = ctk.CTkLabel(progress_frame, text="00:00", font=("Arial", 10), text_color="#94a3b8")
        self.progress_label_total.pack(side="left", padx=(8, 0))

        controls = ctk.CTkFrame(player, fg_color="transparent")
        controls.place(relx=0.5, rely=0.73, anchor="center")

        # Buttons: Prev, Play, Pause, Resume, Next
        btn_prev = ctk.CTkButton(controls, text="⏮", width=45, height=45, font=("Arial", 16), corner_radius=25,
                                 fg_color="#1e293b", hover_color="#4f46e5", command=self.play_prev)
        btn_prev.pack(side="left", padx=8)

        btn_pause = ctk.CTkButton(controls, text="⏸", width=45, height=45, font=("Arial", 16), corner_radius=25,
                                  fg_color="#1e293b", hover_color="#4f46e5", command=self.pause_current)
        btn_pause.pack(side="left", padx=8)


        btn_next = ctk.CTkButton(controls, text="⏭", width=45, height=45, font=("Arial", 16), corner_radius=25,
                                 fg_color="#1e293b", hover_color="#4f46e5", command=self.play_next)
        btn_next.pack(side="left", padx=8)

    def create_song_card(self, parent, song):
        card = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=8, height=70)
        card.pack(fill="x", pady=3)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=15, pady=10)

        ctk.CTkLabel(info, text=song.title, font=("Arial", 13, "bold"), text_color="#ffffff", anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=f"{song.artist} • {song.genre}", font=("Arial", 10), text_color="#94a3b8", anchor="w").pack(anchor="w")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(side="right", padx=10)

        fav_text = "⭐" if song.id in self.player.favorites else "☆"
        ctk.CTkButton(btns, text=fav_text, width=35, height=35, font=("Arial", 14), fg_color="transparent", hover_color="#6366f1", command=lambda s=song: self._toggle_fav_and_refresh(s)).pack(side="left", padx=2)

        # Tombol Play (bisa berubah ikon)
        play_btn = ctk.CTkButton(
            btns, text="▶", width=35, height=35, font=("Arial", 12),
            fg_color="#6366f1", hover_color="#4f46e5",
            command=lambda s=song: self.toggle_play(s)
        )
        play_btn.pack(side="left", padx=2)

        # simpan tombol di dict supaya bisa diganti ikon
        self.play_buttons[song.id] = play_btn

        ctk.CTkButton(btns, text="+", width=35, height=35, font=("Arial", 14), fg_color="#1e293b", hover_color="#334155", command=lambda s=song: self.add_playlist_and_notify(s)).pack(side="left", padx=2)

    # --------------------------------------------------
    # USER PAGE SCREENS (HOME, SEARCH, PLAYLIST, FAVORITE, HISTORY)
    # --------------------------------------------------
    def user_home(self):
        # Trending: show newest first (desc). We set player.list_order accordingly.
        for w in self.content.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.content, text="Trending Now", font=("Arial", 28, "bold"), text_color="#ffffff").pack(anchor="w", pady=(10, 20))
        # AMBIL SEMUA LAGU & URUTKAN BERDASARKAN YANG TERBARU
        # set ordering so Next will go to visual "below" item
        self.player.current_mode = "library"
        self.player.list_order = "desc"

        songs = list(reversed(self.player.library.get_all()))  # newest first for display
        for song in songs:
            self.create_song_card(self.content, song)

    def user_search(self):
        for w in self.content.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.content, text="Search", font=("Arial", 28, "bold"), text_color="#ffffff").pack(anchor="w", pady=(10, 15))
        search_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        search_frame.pack(fill="x", pady=10)

        entry = ctk.CTkEntry(search_frame, width=400, height=40, placeholder_text="Search...", font=("Arial", 12), corner_radius=8, fg_color="#1a1a1a")
        entry.pack(side="left", padx=(0, 10))

        result = ctk.CTkFrame(self.content, fg_color="transparent")
        result.pack(fill="both", expand=True, pady=10)

        def do_search():
            for w in result.winfo_children():
                w.destroy()
            keyword = entry.get()
            if keyword:
                songs = self.user.search(keyword)
                # for search results, set ordering to asc (natural)
                self.player.current_mode = "library"
                self.player.list_order = "asc"
                for s in songs:
                    self.create_song_card(result, s)

        ctk.CTkButton(search_frame, text="Search", width=100, height=40, fg_color="#6366f1", hover_color="#4f46e5", command=do_search).pack(side="left")

    def user_playlist(self):
        for w in self.content.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.content, text="My Playlists", font=("Arial", 28, "bold"), text_color="#ffffff").pack(anchor="w", pady=(10, 12))

        # Pastikan ada minimal 1 playlist
        playlists = self.user.get_playlists()
        if not playlists:
            self.player.create_playlist(self.player.current_playlist_name)
            playlists = self.user.get_playlists()

        # Pilih playlist aktif
        default_name = self.player.current_playlist_name if self.player.current_playlist_name in playlists else playlists[0]
        playlist_var = StringVar(value=default_name)

        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(top, text="Select playlist:", font=("Arial", 12), text_color="#94a3b8").pack(side="left", padx=(0, 10))

        # Area lagu dalam playlist
        songs_area = ctk.CTkFrame(self.content, fg_color="transparent")
        songs_area.pack(fill="both", expand=True)

        def render_playlist():
            # set mode agar tombol play mengikuti konteks playlist
            name = playlist_var.get()
            self.player.current_mode = "playlist"
            self.player.current_playlist_name = name
            self.player.list_order = "asc"

            for ww in songs_area.winfo_children():
                ww.destroy()

            songs = self.user.get_playlist_songs(name)
            if not songs:
                ctk.CTkLabel(songs_area, text="Playlist is empty", font=("Arial", 13), text_color="#64748b").pack(pady=30)
            else:
                for song in songs:
                    self.create_song_card(songs_area, song)

        dropdown = ctk.CTkOptionMenu(
            top,
            variable=playlist_var,
            values=playlists,
            width=220,
            command=lambda _=None: render_playlist()
        )
        dropdown.pack(side="left")

        def new_playlist():
            name = simpledialog.askstring("New Playlist", "Enter new playlist name:")
            if not name:
                return
            ok = self.user.create_playlist(name)
            if ok:
                # refresh UI & set as current
                self.player.current_playlist_name = name
                self.user_playlist()

        ctk.CTkButton(top, text="➕ New Playlist", width=140, fg_color="#6366f1", hover_color="#4f46e5",
                     command=new_playlist).pack(side="left", padx=10)

        ctk.CTkButton(top, text="🔄 Refresh", width=110, fg_color="#1e293b", hover_color="#334155",
                     command=render_playlist).pack(side="left")

        render_playlist()

    def user_favorites(self):
        for w in self.content.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.content, text="Favorites", font=("Arial", 28, "bold"), text_color="#ffffff").pack(anchor="w", pady=(10, 20))
        favs = self.user.get_favorites()
        # favorites view -> asc
        self.player.current_mode = "library"
        self.player.list_order = "asc"
        if not favs:
            ctk.CTkLabel(self.content, text="No favorites yet", font=("Arial", 13), text_color="#64748b").pack(pady=30)
        else:
            for s in favs:
                self.create_song_card(self.content, s)

    def user_history(self):
        for w in self.content.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.content, text="Recently Played", font=("Arial", 28, "bold"), text_color="#ffffff").pack(anchor="w", pady=(10, 20))
        history = self.user.get_history()
        # history view -> asc
        self.player.current_mode = "library"
        self.player.list_order = "asc"
        if not history:
            ctk.CTkLabel(self.content, text="No history yet", font=("Arial", 13), text_color="#64748b").pack(pady=30)
        else:
            for s in history:
                self.create_song_card(self.content, s)

    # --- small UI helper wrappers that call controllers ---
    def _toggle_fav_and_refresh(self, song):
        self.user.toggle_favorite(song.id)
        # refresh whichever view is visible by rebuilding home (safe default)
        self.user_home()

    def add_playlist_and_notify(self, song):
        playlists = self.user.get_playlists()

        # Jika belum ada playlist sama sekali
        if not playlists:
            self.player.create_playlist("My Playlist")
            playlists = ["My Playlist"]

        popup = ctk.CTkToplevel(self.window)
        popup.title("Pilih Playlist")
        popup.geometry("300x350")
        popup.transient(self.window)
        popup.grab_set()

        ctk.CTkLabel(
            popup,
            text=f"Tambahkan ke playlist:",
            font=("Arial", 14, "bold")
        ).pack(pady=15)

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="both", expand=True, padx=20)

        # Tombol playlist yang SUDAH ADA
        for name in playlists:
            def make_cmd(pname=name):
                return lambda: (
                    self.user.add_to_playlist(song.id, pname),
                    self.player.save_playlists(),
                    popup.destroy(),
                    messagebox.showinfo("Berhasil", f"Lagu ditambahkan ke '{pname}'")
                )

            ctk.CTkButton(
                btn_frame,
                text=name,
                height=40,
                fg_color="#6366f1",
                hover_color="#4f46e5",
                command=make_cmd()
            ).pack(fill="x", pady=5)

        # Tombol buat playlist baru
        def new_playlist():
            dialog = ctk.CTkInputDialog(
                title="Playlist Baru",
                text="Nama playlist:"
            )
            name = dialog.get_input()
            if name:
                self.player.create_playlist(name)
                popup.destroy()
                self.add_playlist_and_notify(song)

        ctk.CTkButton(
            popup,
            text="➕ Playlist Baru",
            height=40,
            fg_color="#1e293b",
            hover_color="#334155",
            command=new_playlist
        ).pack(pady=10)

    # PLAYBACK CONTROL HANDLERS (PLAY, NEXT, PREV, STOP)
   
    def play_song(self, song, mode):
        # single consolidated play_song method
        self.player.current_song = song
        self.player.is_playing = True

        # Reset semua tombol ke ▶
        for btn in self.play_buttons.values():
            try:
                btn.configure(text="▶")
            except Exception:
                pass
        for btn in self.admin_play_buttons.values():
            try:
                btn.configure(text="⏵")
            except Exception:
                pass

        # Tombol lagu yang sedang diputar berubah jadi ⏸ (if exists)
        if song.id in self.play_buttons:
            try:
                self.play_buttons[song.id].configure(text="⏸")
            except Exception:
                pass
        if song.id in self.admin_play_buttons:
            try:
                self.admin_play_buttons[song.id].configure(text="⏸")
            except Exception:
                pass

        # track mode & history
        self.player.current_mode = mode
        self.player.history.push(song)

        # update UI if present
        if hasattr(self, 'now_playing') and self.now_playing is not None:
            try:
                self.now_playing.configure(text=song.title)
            except Exception:
                pass
        if hasattr(self, 'now_artist') and self.now_artist is not None:
            try:
                self.now_artist.configure(text=song.artist)
            except Exception:
                pass

        
        # ACTUAL MUSIC PLAYBACK
        # compute length
        length = self._get_song_length_seconds(song)
        self.current_song_length = length if length else 0.0
        # set total time label
        self._set_progress_total_label(self.current_song_length)
        # reset progress
        self.progress_value = 0.0
        try:
            if song.file_path:
                if not os.path.isfile(song.file_path):
                    raise FileNotFoundError(f"File not found: {song.file_path}")
                pygame.mixer.music.load(song.file_path)
                pygame.mixer.music.play()
            else:
                messagebox.showwarning("No File", "This song has no audio file.")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot play song:\n{e}")

        # start progress updater
        self._start_progress_updater()

    def play_prev(self):
        # Prev should go to previous item in visual list (which may be above)
        prev = self.player.prev_song()
        if prev:
            self.play_song(prev, self.player.current_mode)

    def play_next(self):
        nxt = self.player.next_song()
        if nxt:
            self.play_song(nxt, self.player.current_mode)

    def play_current(self):
        if self.player.current_song:
            # (re)load & play current
            self.play_song(self.player.current_song, self.player.current_mode)

    def pause_current(self):
        try:
            pygame.mixer.music.pause()
            self.player.is_playing = False
        except Exception as e:
            messagebox.showerror("Error", f"Cannot pause: {e}")

    def resume_current(self):
        try:
            pygame.mixer.music.unpause()
            self.player.is_playing = True
        except Exception as e:
            messagebox.showerror("Error", f"Cannot resume: {e}")

    def stop_current(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        self.player.is_playing = False
        self.player.current_song = None

        # Reset UI
        if hasattr(self, "now_playing") and self.now_playing is not None:
            try:
                self.now_playing.configure(text="No song playing")
            except Exception:
                pass
        if hasattr(self, "now_artist") and self.now_artist is not None:
            try:
                self.now_artist.configure(text="")
            except Exception:
                pass

        # stop progress updater
        if self._progress_update_job:
            try:
                self.window.after_cancel(self._progress_update_job)
            except Exception:
                pass
            self._progress_update_job = None
        # reset progress UI
        self.progress_bar.set(0.0)
        self._set_progress_elapsed_label(0.0)

    # Progress helpers

    def _get_song_length_seconds(self, song: Song):
        # Try pygame Sound if file exists (gives accurate length)
        try:
            if song.file_path and os.path.isfile(song.file_path):
                try:
                    snd = pygame.mixer.Sound(song.file_path)
                    length = snd.get_length()
                    # release Sound object
                    del snd
                    return float(length)
                except Exception:
                    pass
            # fallback: parse song.duration string like "3:45" or "03:45"
            if song.duration:
                parts = song.duration.strip().split(":")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            pass
        return 0.0

    def _format_seconds(self, secs):
        try:
            secs = max(0, int(secs))
            m = secs // 60
            s = secs % 60
            return f"{m:02d}:{s:02d}"
        except Exception:
            return "00:00"

    def _set_progress_total_label(self, total_seconds):
        if self.progress_label_total:
            self.progress_label_total.configure(text=self._format_seconds(total_seconds))

    def _set_progress_elapsed_label(self, elapsed_seconds):
        if self.progress_label_elapsed:
            self.progress_label_elapsed.configure(text=self._format_seconds(elapsed_seconds))

    def _start_progress_updater(self):
        # cancel existing job
        if self._progress_update_job:
            try:
                self.window.after_cancel(self._progress_update_job)
            except Exception:
                pass
            self._progress_update_job = None
        # schedule update
        self._update_progress()

    def _update_progress(self):
        # compute elapsed
        elapsed = 0.0
        try:
            pos_ms = pygame.mixer.music.get_pos()  # milliseconds since play (resets on pause/resume)
            if pos_ms >= 0:
                elapsed = pos_ms / 1000.0
            # There are platform quirks: when music finished, get_pos() may be -1 or 0.
        except Exception:
            elapsed = 0.0

        # If we can get total length from property
        total = self.current_song_length if self.current_song_length else 0.0

        # update UI labels
        self._set_progress_elapsed_label(elapsed)
        if total > 0:
            fraction = min(1.0, elapsed / total)
        else:
            fraction = 0.0
        try:
            self.progress_bar.set(fraction)
        except Exception:
            pass

        # If playback ended (pygame reports not busy) and fraction >= .99 -> auto next
        try:
            busy = pygame.mixer.music.get_busy()
        except Exception:
            busy = False

        # If not busy but elapsed > 0 and fraction near 1 => ended
        if not busy and total > 0 and fraction >= 0.98:
            # move to next
            nxt = self.player.next_song()
            if nxt:
                # small delay to avoid immediate re-entrancy
                self.window.after(200, lambda: self.play_song(nxt, self.player.current_mode))
                return
            else:
                # reset
                self.stop_current()
                return

        # schedule next update
        self._progress_update_job = self.window.after(500, self._update_progress)


    def run(self):
        self.window.mainloop()



if __name__ == "__main__":
    app = MusicPlayerGUI()
    app.run()
