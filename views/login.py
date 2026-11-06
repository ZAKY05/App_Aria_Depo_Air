"""
Login View - Halaman login aplikasi
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
try:
    from PIL import Image, ImageTk, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from styles import COLORS, FONTS, ICONS
import database as db


def _resource_path(relative_path):
    """Mendapatkan path absolut ke resource, kompatibel PyInstaller .exe"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class LoginView(tk.Frame):
    def __init__(self, parent, on_login_success):
        super().__init__(parent, bg=COLORS['primary_dark'])
        self.parent = parent
        self.on_login_success = on_login_success
        self.pack(fill='both', expand=True)
        self._build_ui()

    def _load_logo(self, target_size=(130, 130)):
        """Muat dan olah logo dari folder views/img"""
        if not HAS_PIL:
            return None
        try:
            img_dir = _resource_path('img')
            if not os.path.exists(img_dir):
                return None

            valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
            image_files = [f for f in os.listdir(img_dir) if f.lower().endswith(valid_exts)]
            if not image_files:
                return None

            # Prioritaskan Aria_Depo.jpeg jika ada, atau file gambar pertama
            selected_file = 'Aria_Depo.jpeg' if 'Aria_Depo.jpeg' in image_files else image_files[0]
            img_path = os.path.join(img_dir, selected_file)

            img = Image.open(img_path).convert('RGB')

            # Auto-crop margin putih di sekeliling logo
            bg = Image.new('RGB', img.size, (255, 255, 255))
            diff = ImageChops.difference(img, bg).convert('L')
            mask = diff.point(lambda p: 255 if p > 15 else 0)
            bbox = mask.getbbox()
            if bbox:
                margin = 15
                crop_box = (
                    max(0, bbox[0] - margin),
                    max(0, bbox[1] - margin),
                    min(img.width, bbox[2] + margin),
                    min(img.height, bbox[3] + margin)
                )
                img = img.crop(crop_box)

            # Resize proporsional dengan kualitas tinggi
            resample_filter = getattr(getattr(Image, 'Resampling', Image), 'LANCZOS', Image.BICUBIC)
            img.thumbnail(target_size, resample_filter)

            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Gagal memuat logo: {e}")
            return None

    def _build_ui(self):
        # Background gradient effect dengan canvas
        self.canvas = tk.Canvas(self, bg=COLORS['primary_dark'], highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # Dekorasi lingkaran di background
        self.canvas.create_oval(-100, -100, 300, 300, fill=COLORS['primary'], outline='')
        self.canvas.create_oval(900, 400, 1300, 800, fill=COLORS['primary'], outline='')
        self.canvas.create_oval(600, -200, 900, 100, fill=COLORS['primary_light'], outline='')

        # Container utama login - posisi tengah
        self.login_frame = tk.Frame(self.canvas, bg=COLORS['white'], padx=50, pady=40)

        # Header
        header_frame = tk.Frame(self.login_frame, bg=COLORS['white'])
        header_frame.pack(fill='x', pady=(0, 10))

        # Tampilkan logo dari views/img atau fallback ke icon
        self.logo_img = self._load_logo((130, 130))
        if self.logo_img:
            logo_label = tk.Label(header_frame, image=self.logo_img, bg=COLORS['white'])
            logo_label.image = self.logo_img
            logo_label.pack(pady=(0, 10))
        else:
            icon_label = tk.Label(
                header_frame, text=ICONS['water'], font=('Segoe UI', 40),
                bg=COLORS['white'], fg=COLORS['primary']
            )
            icon_label.pack()

        title_label = tk.Label(
            header_frame, text="DEPO ARIA", font=FONTS['login_title'],
            bg=COLORS['white'], fg=COLORS['primary_dark']
        )
        title_label.pack()

        subtitle_label = tk.Label(
            header_frame, text="Sistem Kasir & Manajemen", font=FONTS['login_subtitle'],
            bg=COLORS['white'], fg=COLORS['text_light']
        )
        subtitle_label.pack(pady=(0, 5))

        # Separator
        sep = tk.Frame(self.login_frame, bg=COLORS['accent_light'], height=2)
        sep.pack(fill='x', pady=(0, 25))

        # Form login
        form_frame = tk.Frame(self.login_frame, bg=COLORS['white'])
        form_frame.pack(fill='x')

        # Username
        usr_label = tk.Label(
            form_frame, text=f"{ICONS['user']}  Username", font=FONTS['body_bold'],
            bg=COLORS['white'], fg=COLORS['text_dark'], anchor='w'
        )
        usr_label.pack(fill='x', pady=(0, 5))

        self.username_var = tk.StringVar()
        self.username_entry = tk.Entry(
            form_frame, textvariable=self.username_var, font=FONTS['input'],
            relief='solid', bd=1, bg=COLORS['bg_light'],
            insertbackground=COLORS['primary']
        )
        self.username_entry.pack(fill='x', ipady=10, pady=(0, 15))
        self.username_entry.configure(highlightthickness=2, highlightcolor=COLORS['primary'],
                                       highlightbackground=COLORS['border'])

        # Password
        pwd_label = tk.Label(
            form_frame, text=f"{ICONS['lock']}  Password", font=FONTS['body_bold'],
            bg=COLORS['white'], fg=COLORS['text_dark'], anchor='w'
        )
        pwd_label.pack(fill='x', pady=(0, 5))

        self.pwd_frame = tk.Frame(
            form_frame, bg=COLORS['bg_light'], relief='solid', bd=1,
            highlightthickness=2, highlightcolor=COLORS['primary'], highlightbackground=COLORS['border']
        )
        self.pwd_frame.pack(fill='x', pady=(0, 25))

        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(
            self.pwd_frame, textvariable=self.password_var, font=FONTS['input'],
            show='●', relief='flat', bd=0, bg=COLORS['bg_light'],
            insertbackground=COLORS['primary']
        )
        self.password_entry.pack(side='left', fill='x', expand=True, ipady=10, padx=(8, 0))

        self.show_password = False
        self.eye_btn = tk.Button(
            self.pwd_frame, text='👁️', font=('Segoe UI', 11),
            bg=COLORS['bg_light'], fg=COLORS['text_medium'],
            activebackground=COLORS['bg_light'], activeforeground=COLORS['primary'],
            relief='flat', bd=0, cursor='hand2', command=self._toggle_password,
            padx=8
        )
        self.eye_btn.pack(side='right', fill='y', padx=(0, 4))

        self.password_entry.bind('<FocusIn>', lambda e: self.pwd_frame.configure(highlightbackground=COLORS['primary']))
        self.password_entry.bind('<FocusOut>', lambda e: self.pwd_frame.configure(highlightbackground=COLORS['border']))

        # Login button
        self.login_btn = tk.Button(
            form_frame, text="MASUK", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'],
            activebackground=COLORS['primary_dark'], activeforeground=COLORS['text_white'],
            relief='flat', cursor='hand2', command=self._login,
            bd=0
        )
        self.login_btn.pack(fill='x', ipady=12, pady=(0, 15))
        self.login_btn.bind('<Enter>', lambda e: self.login_btn.config(bg=COLORS['primary_hover']))
        self.login_btn.bind('<Leave>', lambda e: self.login_btn.config(bg=COLORS['primary']))


        # Bind Enter key
        self.username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        self.password_entry.bind('<Return>', lambda e: self._login())

        # Center login frame
        self.canvas.bind('<Configure>', self._center_login)
        self.username_entry.focus_set()

    def _toggle_password(self):
        """Toggle visibilitas password"""
        self.show_password = not self.show_password
        if self.show_password:
            self.password_entry.configure(show='')
            self.eye_btn.configure(text='🙈')
        else:
            self.password_entry.configure(show='●')
            self.eye_btn.configure(text='👁️')

    def _center_login(self, event=None):
        """Posisikan login card di tengah"""
        self.canvas.delete('login_window')
        self.update_idletasks()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.create_window(w // 2, h // 2, window=self.login_frame, tags='login_window')

    def _login(self):
        """Proses login"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showwarning("Peringatan", "Username dan password harus diisi!")
            return

        user = db.authenticate_user(username, password)
        if user:
            self.on_login_success(user)
        else:
            messagebox.showerror("Login Gagal", "Username atau password salah!")
            self.password_var.set("")
            self.password_entry.focus_set()
