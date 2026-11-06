"""
Products View - Halaman manajemen produk (CRUD)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from styles import COLORS, FONTS, ICONS, format_currency


class ProductsView(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=COLORS['bg_light'])
        self.user = user
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=COLORS['bg_light'])
        header.pack(fill='x', padx=25, pady=(25, 15))

        tk.Label(
            header, text=f"{ICONS['product']}  Data Produk",
            font=FONTS['title'], bg=COLORS['bg_light'], fg=COLORS['text_dark']
        ).pack(side='left')

        # Tombol Tambah
        add_btn = tk.Button(
            header, text=f"  {ICONS['add']}  Tambah Produk  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._show_add_dialog, pady=8
        )
        add_btn.pack(side='right')
        add_btn.bind('<Enter>', lambda e: add_btn.config(bg=COLORS['primary_hover']))
        add_btn.bind('<Leave>', lambda e: add_btn.config(bg=COLORS['primary']))

        # Search bar
        search_frame = tk.Frame(self, bg=COLORS['white'], padx=15, pady=12,
                                 highlightbackground=COLORS['border_light'], highlightthickness=1)
        search_frame.pack(fill='x', padx=25, pady=(0, 15))

        tk.Label(search_frame, text=ICONS['search'], font=('Segoe UI', 14),
                 bg=COLORS['white']).pack(side='left', padx=(0, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *a: self.refresh_data())
        search_entry = tk.Entry(
            search_frame, textvariable=self.search_var, font=FONTS['input'],
            relief='flat', bg=COLORS['white'], insertbackground=COLORS['primary']
        )
        search_entry.pack(side='left', fill='x', expand=True)

        # ===== PENTING: Buat action_frame dulu, pack di BOTTOM =====
        action_frame = tk.Frame(self, bg=COLORS['bg_light'], pady=5)
        action_frame.pack(side='bottom', fill='x', padx=25, pady=(5, 15))

        edit_btn = tk.Button(
            action_frame, text=f"  {ICONS['edit']}  Edit  ", font=FONTS['body_bold'],
            bg=COLORS['primary_light'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._show_edit_dialog, pady=8, padx=12
        )
        edit_btn.pack(side='left', padx=(0, 8))
        edit_btn.bind('<Enter>', lambda e: edit_btn.config(bg=COLORS['primary']))
        edit_btn.bind('<Leave>', lambda e: edit_btn.config(bg=COLORS['primary_light']))

        del_btn = tk.Button(
            action_frame, text=f"  {ICONS['delete']}  Hapus  ", font=FONTS['body_bold'],
            bg=COLORS['danger'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._delete_product, pady=8, padx=12
        )
        del_btn.pack(side='left')
        del_btn.bind('<Enter>', lambda e: del_btn.config(bg='#B71C1C'))
        del_btn.bind('<Leave>', lambda e: del_btn.config(bg=COLORS['danger']))

        self.count_label = tk.Label(
            action_frame, text="", font=FONTS['small'],
            bg=COLORS['bg_light'], fg=COLORS['text_light']
        )
        self.count_label.pack(side='right')

        # ===== Tabel produk - pack SETELAH action_frame =====
        table_frame = tk.Frame(self, bg=COLORS['white'],
                                highlightbackground=COLORS['border_light'], highlightthickness=1)
        table_frame.pack(fill='both', expand=True, padx=25, pady=(0, 5))

        # Style treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Products.Treeview',
                         background=COLORS['white'],
                         foreground=COLORS['text_dark'],
                         fieldbackground=COLORS['white'],
                         font=FONTS['table'],
                         rowheight=38)
        style.configure('Products.Treeview.Heading',
                         background=COLORS['primary'],
                         foreground=COLORS['text_white'],
                         font=FONTS['table_header'],
                         relief='flat')
        style.map('Products.Treeview.Heading',
                   background=[('active', COLORS['primary_hover'])])
        style.map('Products.Treeview',
                   background=[('selected', COLORS['accent_light'])],
                   foreground=[('selected', COLORS['text_dark'])])

        columns = ('id', 'name', 'category', 'buy_price', 'sell_price', 'courier_fee', 'stock', 'unit')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                  style='Products.Treeview', selectmode='browse')

        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Nama Produk')
        self.tree.heading('category', text='Kategori')
        self.tree.heading('buy_price', text='Harga Beli')
        self.tree.heading('sell_price', text='Harga Jual')
        self.tree.heading('courier_fee', text='Upah Antar (Rp)')
        self.tree.heading('stock', text='Stok')
        self.tree.heading('unit', text='Satuan')

        self.tree.column('id', width=50, anchor='center')
        self.tree.column('name', width=190, anchor='w')
        self.tree.column('category', width=90, anchor='center')
        self.tree.column('buy_price', width=120, anchor='e')
        self.tree.column('sell_price', width=120, anchor='e')
        self.tree.column('courier_fee', width=120, anchor='e')
        self.tree.column('stock', width=70, anchor='center')
        self.tree.column('unit', width=70, anchor='center')

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Tag untuk stok rendah
        self.tree.tag_configure('low_stock', background=COLORS['warning_bg'])
        self.tree.tag_configure('no_stock', background=COLORS['danger_bg'])

        # Context menu
        self.tree.bind('<Double-1>', lambda e: self._show_edit_dialog())
        self.tree.bind('<Button-3>', self._show_context_menu)

    def _show_context_menu(self, event):
        """Tampilkan menu klik kanan"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Edit Produk", command=self._show_edit_dialog)
        menu.add_command(label="Hapus Produk", command=self._delete_product)
        menu.post(event.x_root, event.y_root)

    def refresh_data(self):
        """Refresh data tabel"""
        import database as db
        for item in self.tree.get_children():
            self.tree.delete(item)

        products = db.get_all_products()
        search = self.search_var.get().lower()

        count = 0
        for p in products:
            if search and search not in p['name'].lower() and search not in p['category'].lower():
                continue
            tags = ()
            if p['stock'] == 0:
                tags = ('no_stock',)
            elif p['stock'] < 10:
                tags = ('low_stock',)

            self.tree.insert('', 'end', values=(
                p['id'], p['name'], p['category'],
                format_currency(p['buy_price']),
                format_currency(p['sell_price']),
                format_currency(p.get('courier_fee_per_unit', 0) or 0),
                p['stock'], p['unit']
            ), tags=tags)
            count += 1

        self.count_label.config(text=f"Total: {count} produk")

    def _show_add_dialog(self):
        """Dialog tambah produk"""
        self._show_product_dialog("Tambah Produk Baru")

    def _show_edit_dialog(self):
        """Dialog edit produk"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih produk yang ingin diedit!")
            return

        values = self.tree.item(selected[0])['values']
        self._show_product_dialog("Edit Produk", values)

    def _show_product_dialog(self, title, values=None):
        """Dialog form produk"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("480x620")
        dialog.minsize(440, 520)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 240
        y = (dialog.winfo_screenheight() // 2) - 310
        dialog.geometry(f'+{x}+{y}')

        # Title
        tk.Label(dialog, text=title, font=FONTS['subtitle'],
                 bg=COLORS['white'], fg=COLORS['primary_dark']).pack(side='top', pady=(15, 10))

        sep = tk.Frame(dialog, bg=COLORS['accent_light'], height=2)
        sep.pack(side='top', fill='x', padx=30)

        # Buttons packed at BOTTOM first so they are ALWAYS visible
        btn_frame = tk.Frame(dialog, bg=COLORS['white'])
        btn_frame.pack(side='bottom', fill='x', padx=30, pady=15)

        form = tk.Frame(dialog, bg=COLORS['white'], padx=30)
        form.pack(side='top', fill='both', expand=True, pady=10)

        fields = {}

        def add_field(label_text, key, default=""):
            tk.Label(form, text=label_text, font=FONTS['body_bold'],
                     bg=COLORS['white'], fg=COLORS['text_dark'], anchor='w').pack(fill='x', pady=(6, 2))
            var = tk.StringVar(value=str(default))
            entry = tk.Entry(form, textvariable=var, font=FONTS['input'],
                              relief='solid', bd=1, bg=COLORS['bg_light'])
            entry.pack(fill='x', ipady=5)
            entry.configure(highlightthickness=1, highlightcolor=COLORS['primary'],
                             highlightbackground=COLORS['border'])
            fields[key] = var
            return entry

        # Populate fields
        add_field("Nama Produk", 'name', values[1] if values else "")

        # Kategori dropdown
        tk.Label(form, text="Kategori", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark'], anchor='w').pack(fill='x', pady=(6, 2))
        cat_var = tk.StringVar(value=values[2] if values else "Galon")
        cat_combo = ttk.Combobox(form, textvariable=cat_var, font=FONTS['input'],
                                  values=['Galon', 'Botol', 'Lainnya'], state='readonly')
        cat_combo.pack(fill='x', ipady=4)
        fields['category'] = cat_var

        add_field("Harga Beli (Rp)", 'buy_price',
                  str(values[3]).replace('Rp ', '').replace('.', '') if values else "0")
        add_field("Harga Jual (Rp)", 'sell_price',
                  str(values[4]).replace('Rp ', '').replace('.', '') if values else "0")
        add_field("Upah Antar per Satuan (Rp)", 'courier_fee',
                  str(values[5]).replace('Rp ', '').replace('.', '') if values else "0")
        add_field("Stok", 'stock', values[6] if values else "0")

        # Satuan dropdown
        tk.Label(form, text="Satuan", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark'], anchor='w').pack(fill='x', pady=(6, 2))
        unit_var = tk.StringVar(value=values[7] if values else "galon")
        unit_combo = ttk.Combobox(form, textvariable=unit_var, font=FONTS['input'],
                                  values=['galon', 'botol', 'pcs', 'dus', 'liter'], state='readonly')
        unit_combo.pack(fill='x', ipady=4)
        fields['unit'] = unit_var

        def save():
            try:
                import database as dbase
                name = fields['name'].get().strip()
                category = fields['category'].get()
                buy_price = float(fields['buy_price'].get().replace('.', '').replace(',', ''))
                sell_price = float(fields['sell_price'].get().replace('.', '').replace(',', ''))
                courier_fee = int(fields['courier_fee'].get().replace('.', '').replace(',', '').strip() or 0)
                stock = int(fields['stock'].get())
                unit = fields['unit'].get()

                if not name:
                    messagebox.showwarning("Peringatan", "Nama produk harus diisi!")
                    return
                if courier_fee < 0:
                    messagebox.showwarning("Peringatan", "Upah antar tidak boleh negatif!")
                    return

                if values:
                    dbase.update_product(values[0], name, category, buy_price, sell_price, stock, unit, courier_fee)
                    messagebox.showinfo("Berhasil", "Produk berhasil diupdate!")
                else:
                    dbase.add_product(name, category, buy_price, sell_price, stock, unit, courier_fee)
                    messagebox.showinfo("Berhasil", "Produk berhasil ditambahkan!")

                dialog.destroy()
                self.refresh_data()
            except ValueError:
                messagebox.showerror("Error", "Pastikan harga dan stok berupa angka yang valid!")

        save_btn = tk.Button(
            btn_frame, text="  💾  Simpan  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=save, padx=20, pady=8
        )
        save_btn.pack(side='left', padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg=COLORS['primary_hover']))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg=COLORS['primary']))

        cancel_btn = tk.Button(
            btn_frame, text="  Batal  ", font=FONTS['button'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=dialog.destroy, padx=20, pady=8
        )
        cancel_btn.pack(side='left')

    def _delete_product(self):
        """Hapus produk"""
        import database as dbase
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih produk yang ingin dihapus!")
            return

        values = self.tree.item(selected[0])['values']
        if messagebox.askyesno("Konfirmasi", f"Hapus produk '{values[1]}'?"):
            dbase.delete_product(values[0])
            messagebox.showinfo("Berhasil", "Produk berhasil dihapus!")
            self.refresh_data()
