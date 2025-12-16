# Groovy Music Player

## Deskripsi Aplikasi

Groovy Music Player adalah aplikasi pemutar musik berbasis GUI (Graphical User Interface) yang dibuat menggunakan bahasa pemrograman Python. Aplikasi ini dirancang sebagai implementasi mata kuliah **Struktur Data**, dengan menerapkan berbagai struktur data seperti **Doubly Linked List, Queue, Stack**, dan **Multi-Playlist**.

Aplikasi memiliki dua peran pengguna, yaitu **Admin** dan **User**. Admin bertugas mengelola data lagu dalam library, sedangkan User dapat memutar lagu, mengelola playlist, menandai lagu favorit, serta melihat riwayat pemutaran lagu.

---

## Fitur-Fitur

### 🔑 Login

* Login sebagai **Admin** (dengan username dan password)
* Login sebagai **User** (tanpa validasi password)

### 👨‍💼 Fitur Admin

* Menambahkan lagu baru ke dalam library
* Melihat seluruh lagu yang tersedia
* Menghapus lagu dari library
* Memutar, pause, dan navigasi lagu (next / prev)

### 👤 Fitur User

* Melihat daftar lagu (library)
* Mencari lagu berdasarkan judul, artis, atau genre
* Memutar dan menghentikan lagu
* Navigasi lagu (next / previous)
* Membuat dan mengelola **multiple playlist**
* Menambahkan lagu ke playlist
* Menandai lagu sebagai **favorite**
* Melihat **riwayat lagu** yang telah diputar

### Struktur Data yang Digunakan

* **Doubly Linked List**: penyimpanan lagu di library dan playlist
* **Queue**: antrian lagu
* **Stack**: riwayat lagu yang diputar
* **Set**: penyimpanan lagu favorit

---

## Cara Menjalankan Program

### 1. Persyaratan

Pastikan Python sudah terinstall (versi 3.8 atau lebih baru).

Install library yang dibutuhkan dengan perintah:

```bash
pip install customtkinter pygame
```

### 2. Menjalankan Program

Buka terminal / command prompt pada folder project, lalu jalankan ketiga program ini:

1. Jalankan file backend_groovy_player.py
```bash
python backend_groovy_player.py
```

2. Jalankan file controller_groovy_player.py
```bash
python controller_groovy_player.py
```

3. Jalankan frontend_groovy_player.py
```bash
python frontend_groovy_player.py
```

Kami sudah menyediakan file yang bisa langsung di jalankan untuk mempermudah dalam menjalankan program:
```bash
python Kelompok_4_Source_Kode_Struktur_Data_multi_playlist.py
```

Pastikan file audio (mp3/wav) tersedia di perangkat Anda saat menambahkan lagu.

---

## Daftar Anggota Kelompok

**Kelompok 4**

1. Muhammad Ilham Maulana
2. Muhammad Al Fayyad Nezati Al-Qasim
3. Muhammad Ade Sulistiansyah

---

## Catatan

* Data lagu disimpan dalam file `songs.json`
* Data playlist disimpan dalam file `playlists.json`
* Aplikasi berjalan secara lokal (offline)

---

Dikembangkan untuk memenuhi Tugas Besar Mata Kuliah **Struktur Data Semester Ganjil 2025/2026**
