

import tkinter as tk
from tkinter import messagebox
import sys
import os


def _resource_path(relative_path):
    """Mendapatkan path absolut ke resource, kompatibel PyInstaller .exe"""
    if getattr(sys, 'frozen', False):
        # Saat di-bundle, resource ada di sys._MEIPASS (folder temp PyInstaller)
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# Pastikan root folder ada di path
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from styles import COLORS, FONTS, ICONS
import database as db
from views.login import LoginView
from views.dashboard import DashboardView
from views.products import ProductsView
from views.customers import CustomersView
from views.transaction import TransactionView
from views.expenses import ExpensesView
from views.reports import ReportsView
from views.users import UsersView
from views.courier import CourierView
from views.flowmeter import FlowMeterView


class DepoAirApp:
    """Aplikasi utama Kasir Depo Air"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(" Depo Air - Sistem Kasir")
        self.root.geometry("1280x750")
        self.root.minsize(1100, 650)
        self.root.configure(bg=COLORS['bg_light'])

        # Set icon aplikasi dari views/img
        try:
            from PIL import Image, ImageTk
            icon_path = _resource_path(os.path.join('views', 'img', 'Aria_Depo.jpeg'))
            if os.path.exists(icon_path):
                self._app_icon = ImageTk.PhotoImage(Image.open(icon_path))
                self.root.iconphoto(True, self._app_icon)
        except Exception:
            pass

        # State
        self.current_user = None
        self.current_view = None
        self.active_menu = None
        self.sidebar_buttons = {}

        # Init database
        db.init_database()

        # Show login
        self._show_login()

    def _show_login(self):
        """Tampilkan halaman login"""
        self._clear_main()
        self.root.title(" Depo Air - Login")
        LoginView(self.root, self._on_login_success)

    def _on_login_success(self, user):
        """Callback setelah login berhasil"""
        self.current_user = user
        self._clear_main()
        self._build_main_layout()

        # Default view berdasarkan role
        if user['role'] == 'owner':
            self._switch_view('dashboard')
        else:
            self._switch_view('transaction')

    def _clear_main(self):
        """Hapus semua widget"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def _build_main_layout(self):
        """Bangun layout utama dengan sidebar dan content area"""
        self.root.title(f"💧 Depo Air - {self.current_user['full_name']} ({self.current_user['role'].upper()})")

        # ===== SIDEBAR =====
        self.sidebar = tk.Frame(self.root, bg=COLORS['bg_sidebar'], width=240)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)
        self.sidebar.configure(width=240)

        # 1. Logout button - PACK DI BOTTOM LEBIH DULU agar SELALU terlihat & tidak pernah tenggelam
        logout_frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], pady=10)
        logout_frame.pack(side='bottom', fill='x')

        sep2 = tk.Frame(logout_frame, bg=COLORS['primary'], height=1)
        sep2.pack(fill='x', padx=15, pady=(0, 8))

        logout_btn = tk.Button(
            logout_frame, text=f"{ICONS['logout']}   Logout", font=FONTS['sidebar'],
            bg=COLORS['bg_sidebar'], fg=COLORS['text_sidebar'],
            activebackground=COLORS['danger'], activeforeground=COLORS['text_white'],
            relief='flat', cursor='hand2', anchor='w', padx=20, pady=8,
            command=self._logout
        )
        logout_btn.pack(fill='x')
        logout_btn.bind('<Enter>', lambda e: logout_btn.config(bg=COLORS['danger'], fg=COLORS['text_white']))
        logout_btn.bind('<Leave>', lambda e: logout_btn.config(bg=COLORS['bg_sidebar'], fg=COLORS['text_sidebar']))

        # 2. Sidebar header (di bagian atas)
        sidebar_header = tk.Frame(self.sidebar, bg=COLORS['primary_dark'], padx=20, pady=12)
        sidebar_header.pack(fill='x')

        tk.Label(
            sidebar_header, text=f"{ICONS['water']} DEPO AIR", font=('Segoe UI', 16, 'bold'),
            bg=COLORS['primary_dark'], fg=COLORS['text_white']
        ).pack(anchor='w')

        tk.Label(
            sidebar_header, text="Sistem Kasir", font=FONTS['small'],
            bg=COLORS['primary_dark'], fg=COLORS['accent_light']
        ).pack(anchor='w')

        # 3. User info
        user_frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], padx=20, pady=10)
        user_frame.pack(fill='x')

        tk.Label(
            user_frame, text=f"{ICONS['user']}  {self.current_user['full_name']}",
            font=FONTS['body_bold'], bg=COLORS['bg_sidebar'], fg=COLORS['text_white']
        ).pack(anchor='w')

        role_text = "👑 Owner" if self.current_user['role'] == 'owner' else "🏪 Kasir"
        tk.Label(
            user_frame, text=role_text, font=FONTS['small'],
            bg=COLORS['bg_sidebar'], fg=COLORS['accent_light']
        ).pack(anchor='w', pady=(2, 0))

        # Tombol Edit Profil Owner
        if self.current_user['role'] == 'owner':
            profile_btn = tk.Button(
                user_frame, text="⚙️  Edit Profil", font=FONTS['small'],
                bg=COLORS['bg_sidebar_hover'], fg=COLORS['text_white'],
                activebackground=COLORS['primary'], activeforeground=COLORS['text_white'],
                relief='flat', cursor='hand2', padx=10, pady=3,
                command=self._show_owner_profile
            )
            profile_btn.pack(anchor='w', pady=(6, 0))
            profile_btn.bind('<Enter>', lambda e: profile_btn.config(bg=COLORS['primary']))
            profile_btn.bind('<Leave>', lambda e: profile_btn.config(bg=COLORS['bg_sidebar_hover']))

        sep = tk.Frame(self.sidebar, bg=COLORS['primary'], height=1)
        sep.pack(fill='x', padx=15, pady=(0, 4))

        # 4. Menu items
        menu_frame = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'], pady=4)
        menu_frame.pack(fill='x')

        if self.current_user['role'] == 'owner':
            menus = [
                ('dashboard', ICONS['dashboard'], 'Dashboard'),
                ('products', ICONS['product'], 'Data Produk'),
                ('customers', ICONS['customer'], 'Data Pelanggan'),
                ('users', ICONS['user'], 'Kelola Kasir'),
                ('transaction', ICONS['transaction'], 'Transaksi'),
                ('flowmeter', ICONS.get('flowmeter', '⏱️'), 'Meteran Air'),
                ('expenses', ICONS['expense'], 'Pengeluaran'),
                ('courier', '🚚', 'Pendataan Kurir'),
                ('reports', ICONS['report'], 'Laporan'),
            ]
        else:
            menus = [
                ('transaction', ICONS['transaction'], 'Transaksi'),
                ('customers', ICONS['customer'], 'Data Pelanggan'),
                ('flowmeter', ICONS.get('flowmeter', '⏱️'), 'Catat Meteran'),
            ]

        for key, icon, text in menus:
            self._create_sidebar_button(menu_frame, key, icon, text)

        # 5. Spacer pengisi sisa ruang antara menu dan logout
        spacer = tk.Frame(self.sidebar, bg=COLORS['bg_sidebar'])
        spacer.pack(fill='both', expand=True)

        # ===== CONTENT AREA =====
        self.content = tk.Frame(self.root, bg=COLORS['bg_light'])
        self.content.pack(side='left', fill='both', expand=True)

    def _create_sidebar_button(self, parent, key, icon, text):
        """Buat tombol sidebar"""
        btn = tk.Button(
            parent, text=f"{icon}   {text}", font=FONTS['sidebar'],
            bg=COLORS['bg_sidebar'], fg=COLORS['text_sidebar'],
            activebackground=COLORS['bg_sidebar_active'],
            activeforeground=COLORS['text_white'],
            relief='flat', cursor='hand2', anchor='w', padx=20, pady=7,
            command=lambda k=key: self._switch_view(k)
        )
        btn.pack(fill='x')
        btn.bind('<Enter>', lambda e, b=btn, k=key: self._menu_hover(b, k, True))
        btn.bind('<Leave>', lambda e, b=btn, k=key: self._menu_hover(b, k, False))

        self.sidebar_buttons[key] = btn

    def _menu_hover(self, btn, key, entering):
        """Efek hover pada menu sidebar"""
        if key == self.active_menu:
            return  # Jangan ubah style menu aktif
        if entering:
            btn.config(bg=COLORS['bg_sidebar_hover'], fg=COLORS['text_white'])
        else:
            btn.config(bg=COLORS['bg_sidebar'], fg=COLORS['text_sidebar'])

    def _switch_view(self, view_name):
        """Pindah tampilan"""
        # Update menu aktif
        if self.active_menu and self.active_menu in self.sidebar_buttons:
            self.sidebar_buttons[self.active_menu].config(
                bg=COLORS['bg_sidebar'], fg=COLORS['text_sidebar'],
                font=FONTS['sidebar']
            )

        self.active_menu = view_name
        if view_name in self.sidebar_buttons:
            self.sidebar_buttons[view_name].config(
                bg=COLORS['bg_sidebar_active'], fg=COLORS['text_white'],
                font=FONTS['sidebar_bold']
            )

        # Clear content
        for widget in self.content.winfo_children():
            widget.destroy()

        # Load view
        view_map = {
            'dashboard': DashboardView,
            'products': ProductsView,
            'customers': CustomersView,
            'users': UsersView,
            'transaction': TransactionView,
            'flowmeter': FlowMeterView,
            'expenses': ExpensesView,
            'courier': CourierView,
            'reports': ReportsView,
        }

        view_class = view_map.get(view_name)
        if view_class:
            self.current_view = view_class(self.content, self.current_user)
            self.current_view.pack(fill='both', expand=True)

    def _logout(self):
        """Logout dan kembali ke login"""
        if messagebox.askyesno("Logout", "Apakah Anda yakin ingin logout?"):
            self.current_user = None
            self.active_menu = None
            self.sidebar_buttons = {}
            self._show_login()

    def _show_owner_profile(self):
        """Tampilkan dialog edit profil owner"""
        owner_data = db.get_user_by_id(self.current_user['id'])
        if not owner_data:
            messagebox.showerror("Error", "Data owner tidak ditemukan!")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Profil Owner")
        dialog.geometry("480x520")
        dialog.minsize(440, 460)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 240
        y = (dialog.winfo_screenheight() // 2) - 260
        dialog.geometry(f'+{x}+{y}')

        # Header
        tk.Label(dialog, text="👑  Profil Owner",
                 font=FONTS['subtitle'], bg=COLORS['white'],
                 fg=COLORS['primary_dark']).pack(side='top', pady=(15, 10))

        tk.Frame(dialog, bg=COLORS['accent_light'], height=2).pack(side='top', fill='x', padx=30)

        # Buttons packed at BOTTOM first
        btn_frame = tk.Frame(dialog, bg=COLORS['white'])
        btn_frame.pack(side='bottom', fill='x', padx=30, pady=15)

        form = tk.Frame(dialog, bg=COLORS['white'], padx=30)
        form.pack(side='top', fill='both', expand=True, pady=10)

        # Nama Lengkap
        tk.Label(form, text="Nama Lengkap", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(3, 2))
        name_var = tk.StringVar(value=owner_data['full_name'])
        name_entry = tk.Entry(form, textvariable=name_var, font=FONTS['input'],
                               relief='solid', bd=1, bg=COLORS['bg_light'])
        name_entry.pack(fill='x', ipady=6)
        name_entry.focus_set()

        # Username
        tk.Label(form, text="Username", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(8, 2))
        username_var = tk.StringVar(value=owner_data['username'])
        tk.Entry(form, textvariable=username_var, font=FONTS['input'],
                 relief='solid', bd=1, bg=COLORS['bg_light']).pack(fill='x', ipady=6)

        # Separator
        tk.Frame(form, bg=COLORS['border_light'], height=1).pack(fill='x', pady=(12, 8))
        tk.Label(form, text="🔑  Ubah Password (kosongkan jika tidak ingin ubah)", font=FONTS['small_bold'],
                 bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w', pady=(0, 4))

        # Password Baru dengan toggle
        tk.Label(form, text="Password Baru", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(3, 2))
        pf = tk.Frame(form, bg=COLORS['white'])
        pf.pack(fill='x')
        pass_var = tk.StringVar()
        pass_entry = tk.Entry(pf, textvariable=pass_var, font=FONTS['input'],
                               show='●', relief='solid', bd=1, bg=COLORS['bg_light'])
        pass_entry.pack(side='left', fill='x', expand=True, ipady=6)

        ps = [False]
        def tp():
            ps[0] = not ps[0]
            pass_entry.config(show='' if ps[0] else '●')
            pb.config(text='🙈' if ps[0] else '👁️')
        pb = tk.Button(pf, text='👁️', font=('Segoe UI', 12), bg=COLORS['bg_light'],
                       fg=COLORS['text_medium'], relief='flat', cursor='hand2', command=tp, padx=6)
        pb.pack(side='left', padx=(4, 0))

        # Konfirmasi Password dengan toggle
        tk.Label(form, text="Konfirmasi Password Baru", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(6, 2))
        cf = tk.Frame(form, bg=COLORS['white'])
        cf.pack(fill='x')
        confirm_var = tk.StringVar()
        confirm_entry = tk.Entry(cf, textvariable=confirm_var, font=FONTS['input'],
                                  show='●', relief='solid', bd=1, bg=COLORS['bg_light'])
        confirm_entry.pack(side='left', fill='x', expand=True, ipady=6)

        cs = [False]
        def tc():
            cs[0] = not cs[0]
            confirm_entry.config(show='' if cs[0] else '●')
            cb.config(text='🙈' if cs[0] else '👁️')
        cb = tk.Button(cf, text='👁️', font=('Segoe UI', 12), bg=COLORS['bg_light'],
                       fg=COLORS['text_medium'], relief='flat', cursor='hand2', command=tc, padx=6)
        cb.pack(side='left', padx=(4, 0))

        def save_profile():
            full_name = name_var.get().strip()
            username = username_var.get().strip()
            password = pass_var.get()
            confirm = confirm_var.get()

            if not full_name:
                messagebox.showwarning("Peringatan", "Nama lengkap harus diisi!", parent=dialog)
                return

            success, msg = db.update_user(self.current_user['id'], full_name, username)
            if not success:
                messagebox.showerror("Gagal", msg, parent=dialog)
                return

            if password:
                if len(password) < 4:
                    messagebox.showwarning("Peringatan", "Password minimal 4 karakter!", parent=dialog)
                    return
                if password != confirm:
                    messagebox.showwarning("Peringatan", "Password dan konfirmasi tidak cocok!", parent=dialog)
                    return
                db.update_user_password(self.current_user['id'], password)

            self.current_user['full_name'] = full_name
            self.current_user['username'] = username
            self.root.title(f"💧 Depo Air - {full_name} ({self.current_user['role'].upper()})")

            messagebox.showinfo("Berhasil", "Profil owner berhasil diperbarui!", parent=dialog)
            dialog.destroy()

        tk.Button(
            btn_frame, text="  💾  Simpan Profil  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=save_profile, padx=25, pady=8
        ).pack(side='left', padx=(0, 10))

        tk.Button(
            btn_frame, text="Batal", font=FONTS['button'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=dialog.destroy, padx=25, pady=8
        ).pack(side='left')

    def run(self):
        """Jalankan aplikasi"""
        # Center window di layar
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

        self.root.mainloop()


if __name__ == "__main__":
    app = DepoAirApp()
    app.run()
