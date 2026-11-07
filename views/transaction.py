"""
Transaction View - Halaman transaksi / Point of Sale
Digunakan oleh Owner dan Kasir
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from styles import COLORS, FONTS, ICONS, format_currency
import database as db


class TransactionView(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=COLORS['bg_light'])
        self.user = user
        self.cart = []  # list of {'product_id', 'name', 'quantity', 'unit_price', 'subtotal'}
        self.selected_customer = None
        self._build_ui()
        self._load_products()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=COLORS['bg_light'])
        header.pack(fill='x', padx=20, pady=(20, 10))

        tk.Label(
            header, text=f"{ICONS['transaction']}  Transaksi Baru",
            font=FONTS['title'], bg=COLORS['bg_light'], fg=COLORS['text_dark']
        ).pack(side='left')

        # Main content: left = product list, right = cart
        main = tk.Frame(self, bg=COLORS['bg_light'])
        main.pack(fill='both', expand=True, padx=20, pady=(0, 15))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        # ===== LEFT: Daftar Produk =====
        left_frame = tk.Frame(main, bg=COLORS['white'], padx=15, pady=15,
                               highlightbackground=COLORS['border_light'], highlightthickness=1)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

        tk.Label(left_frame, text=f"{ICONS['product']}  Pilih Produk",
                 font=FONTS['heading'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w')

        # Search produk
        search_frame = tk.Frame(left_frame, bg=COLORS['bg_light'], padx=8, pady=6)
        search_frame.pack(fill='x', pady=(8, 10))

        tk.Label(search_frame, text=ICONS['search'], font=('Segoe UI', 12),
                 bg=COLORS['bg_light']).pack(side='left')
        self.product_search = tk.StringVar()
        self.product_search.trace('w', lambda *a: self._load_products())
        tk.Entry(search_frame, textvariable=self.product_search, font=FONTS['input'],
                 relief='flat', bg=COLORS['bg_light'],
                 insertbackground=COLORS['primary']).pack(side='left', fill='x', expand=True, padx=5)

        # Product list dengan scrollbar
        product_list_frame = tk.Frame(left_frame, bg=COLORS['white'])
        product_list_frame.pack(fill='both', expand=True)

        canvas = tk.Canvas(product_list_frame, bg=COLORS['white'], highlightthickness=0)
        scrollbar = tk.Scrollbar(product_list_frame, orient='vertical', command=canvas.yview)
        self.products_container = tk.Frame(canvas, bg=COLORS['white'])

        self.products_container.bind('<Configure>',
                                      lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.products_container, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind mousewheel on canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind('<MouseWheel>', _on_mousewheel)
        self.products_container.bind('<MouseWheel>', _on_mousewheel)

        # ===== RIGHT: Keranjang =====
        right_frame = tk.Frame(main, bg=COLORS['white'],
                                highlightbackground=COLORS['border_light'], highlightthickness=1)
        right_frame.grid(row=0, column=1, sticky='nsew')

        # 1. Bagian Atas: Header, Pelanggan, Antar, Pilih Kurir (Tinggi Tetap)
        top_section = tk.Frame(right_frame, bg=COLORS['white'])
        top_section.pack(side='top', fill='x')

        # Cart header
        cart_header = tk.Frame(top_section, bg=COLORS['primary'], padx=15, pady=12)
        cart_header.pack(fill='x')

        tk.Label(cart_header, text=f"{ICONS['cart']}  Keranjang Belanja",
                 font=FONTS['heading'], bg=COLORS['primary'], fg=COLORS['text_white']).pack(side='left')

        clear_btn = tk.Button(
            cart_header, text="Kosongkan", font=FONTS['small_bold'],
            bg=COLORS['danger'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._clear_cart, padx=10, pady=3
        )
        clear_btn.pack(side='right')

        # Pilih pelanggan
        customer_frame = tk.Frame(top_section, bg=COLORS['bg_light'], padx=15, pady=10)
        customer_frame.pack(fill='x')

        tk.Label(customer_frame, text="Pelanggan:", font=FONTS['body_bold'],
                 bg=COLORS['bg_light'], fg=COLORS['text_dark']).pack(side='left')

        self.customer_var = tk.StringVar(value="Umum (Tanpa Pelanggan)")
        customers = db.get_all_customers()
        customer_names = ["Umum (Tanpa Pelanggan)"] + [f"{c['name']} (ID:{c['id']})" for c in customers]

        self.customer_combo = ttk.Combobox(
            customer_frame, textvariable=self.customer_var,
            values=customer_names, font=FONTS['small'], state='readonly', width=25
        )
        self.customer_combo.pack(side='left', padx=8, fill='x', expand=True)

        # ===== Opsi Pengantaran =====
        delivery_frame = tk.Frame(top_section, bg=COLORS['white'], padx=15, pady=8)
        delivery_frame.pack(fill='x')

        self.is_delivery_var = tk.IntVar(value=0)
        delivery_check = tk.Checkbutton(
            delivery_frame, text="🚚  Antar",
            variable=self.is_delivery_var, font=FONTS['body_bold'],
            bg=COLORS['white'], fg=COLORS['text_dark'],
            activebackground=COLORS['white'], selectcolor=COLORS['bg_light'],
            cursor='hand2', command=self._toggle_delivery
        )
        delivery_check.pack(side='left')

        # Courier name input (hidden by default di dalam top_section)
        self.courier_frame = tk.Frame(top_section, bg=COLORS['accent_light'], padx=15, pady=8)
        # Tidak di-pack dulu, akan muncul saat checkbox dicentang

        courier_top = tk.Frame(self.courier_frame, bg=COLORS['accent_light'])
        courier_top.pack(fill='x')
        tk.Label(courier_top, text="Pilih Kurir:", font=FONTS['body_bold'],
                 bg=COLORS['accent_light'], fg=COLORS['text_dark']).pack(side='left')

        self.courier_var = tk.StringVar()
        self.courier_entry = ttk.Combobox(
            courier_top, textvariable=self.courier_var,
            font=FONTS['small'], width=22, state='readonly'
        )
        self.courier_entry.pack(side='left', padx=8, fill='x', expand=True)

        self.courier_wage_label = tk.Label(
            self.courier_frame, text="Upah Kurir: Rp 0", font=FONTS['small_bold'],
            bg=COLORS['accent_light'], fg=COLORS['primary_dark']
        )
        self.courier_wage_label.pack(anchor='w', pady=(4, 0))

        # 2. Bagian Bawah: Subtotal, Diskon, TOTAL, Bayar Cash & Hutang
        # PENTING: Di-pack dengan side="bottom" LEBIH DULU agar SELALU terlihat di dasar panel!
        bottom_section = tk.Frame(right_frame, bg=COLORS['white'])
        bottom_section.pack(side='bottom', fill='x')

        # ===== Payment buttons (di bagian paling dasar dari bottom_section) =====
        pay_frame = tk.Frame(bottom_section, bg=COLORS['white'], padx=15, pady=12)
        pay_frame.pack(side='bottom', fill='x')

        cash_btn = tk.Button(
            pay_frame, text=f"  {ICONS['money']}  Bayar Cash  ", font=FONTS['button'],
            bg=COLORS['success'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=lambda: self._process_payment('cash'),
            pady=12
        )
        cash_btn.pack(fill='x', pady=(0, 8))
        cash_btn.bind('<Enter>', lambda e: cash_btn.config(bg='#1B5E20'))
        cash_btn.bind('<Leave>', lambda e: cash_btn.config(bg=COLORS['success']))

        debt_btn = tk.Button(
            pay_frame, text=f"  {ICONS['debt']}  Hutang  ", font=FONTS['button'],
            bg=COLORS['warning'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=lambda: self._process_payment('hutang'),
            pady=12
        )
        debt_btn.pack(fill='x')
        debt_btn.bind('<Enter>', lambda e: debt_btn.config(bg='#E65100'))
        debt_btn.bind('<Leave>', lambda e: debt_btn.config(bg=COLORS['warning']))

        # ===== Summary (Subtotal, Diskon, TOTAL) =====
        summary_frame = tk.Frame(bottom_section, bg=COLORS['bg_light'], padx=15, pady=12)
        summary_frame.pack(side='bottom', fill='x')

        # Subtotal
        sub_row = tk.Frame(summary_frame, bg=COLORS['bg_light'])
        sub_row.pack(fill='x', pady=2)
        tk.Label(sub_row, text="Subtotal:", font=FONTS['body'],
                 bg=COLORS['bg_light'], fg=COLORS['text_medium']).pack(side='left')
        self.subtotal_label = tk.Label(sub_row, text="Rp 0", font=FONTS['body_bold'],
                                        bg=COLORS['bg_light'], fg=COLORS['text_dark'])
        self.subtotal_label.pack(side='right')

        # Diskon
        disc_row = tk.Frame(summary_frame, bg=COLORS['bg_light'])
        disc_row.pack(fill='x', pady=2)
        tk.Label(disc_row, text="Diskon:", font=FONTS['body'],
                 bg=COLORS['bg_light'], fg=COLORS['text_medium']).pack(side='left')
        self.discount_var = tk.StringVar(value="0")
        disc_entry = tk.Entry(disc_row, textvariable=self.discount_var, font=FONTS['body'],
                               width=12, relief='solid', bd=1, justify='right')
        disc_entry.pack(side='right')
        self.discount_var.trace('w', lambda *a: self._update_total())

        # Ongkos kirim (hidden by default, shown when delivery checked)
        self.delivery_row = tk.Frame(summary_frame, bg=COLORS['bg_light'])
        # Tidak di-pack dulu
        tk.Label(self.delivery_row, text="🚚 Ongkir:", font=FONTS['body'],
                 bg=COLORS['bg_light'], fg=COLORS['info']).pack(side='left')
        self.delivery_fee_label = tk.Label(self.delivery_row, text="Rp 2.000", font=FONTS['body_bold'],
                                            bg=COLORS['bg_light'], fg=COLORS['info'])
        self.delivery_fee_label.pack(side='right')

        sep = tk.Frame(summary_frame, bg=COLORS['primary'], height=2)
        sep.pack(fill='x', pady=8)

        # Total
        total_row = tk.Frame(summary_frame, bg=COLORS['bg_light'])
        total_row.pack(fill='x', pady=2)
        tk.Label(total_row, text="TOTAL:", font=FONTS['subtitle'],
                 bg=COLORS['bg_light'], fg=COLORS['text_dark']).pack(side='left')
        self.total_label = tk.Label(total_row, text="Rp 0", font=FONTS['subtitle'],
                                     bg=COLORS['bg_light'], fg=COLORS['primary'])
        self.total_label.pack(side='right')

        # 3. Bagian Tengah: Cart items list - Mengisi sisa ruang di tengah
        self.cart_frame = tk.Frame(right_frame, bg=COLORS['white'], padx=10, pady=5)
        self.cart_frame.pack(side='top', fill='both', expand=True)

        self.cart_empty_label = tk.Label(
            self.cart_frame, text="Keranjang masih kosong\n\nKlik produk untuk menambahkan",
            font=FONTS['body'], bg=COLORS['white'], fg=COLORS['text_light'], justify='center'
        )
        self.cart_empty_label.pack(expand=True)

    def _toggle_delivery(self):
        """Toggle tampilan input kurir saat checkbox diantar dicentang"""
        if self.is_delivery_var.get():
            # Muat kurir aktif
            try:
                self.active_couriers = db.get_all_couriers(active_only=True)
                self.courier_map = {c['name']: c for c in self.active_couriers}
                courier_names = [c['name'] for c in self.active_couriers]
                self.courier_entry['values'] = courier_names
                if courier_names and not self.courier_var.get():
                    self.courier_var.set(courier_names[0])
            except Exception:
                self.active_couriers = []
                self.courier_map = {}

            # Tampilkan courier input di dalam top_section
            self.courier_frame.pack(fill='x')
        else:
            self.courier_frame.pack_forget()
            self.delivery_row.pack_forget()
            self.courier_var.set('')
        self._update_total()

    def _load_products(self):
        """Load daftar produk"""
        for widget in self.products_container.winfo_children():
            widget.destroy()

        products = db.get_all_products()
        search = self.product_search.get().lower()

        row = 0
        col = 0
        for p in products:
            if search and search not in p['name'].lower():
                continue
            # Produk isi ulang selalu tampil (stok tak terbatas)
            is_refill = db.is_water_refill_product(p['name'], p.get('category', ''))
            if not is_refill and p['stock'] <= 0:
                continue

            card = tk.Frame(self.products_container, bg=COLORS['bg_light'], padx=12, pady=10,
                             cursor='hand2')
            card.grid(row=row, column=col, sticky='nsew', padx=4, pady=4)
            self.products_container.columnconfigure(col, weight=1)

            name_label = tk.Label(card, text=p['name'], font=FONTS['body_bold'],
                                   bg=COLORS['bg_light'], fg=COLORS['text_dark'], anchor='w',
                                   cursor='hand2')
            name_label.pack(fill='x')

            price_label = tk.Label(card, text=format_currency(p['sell_price']),
                                    font=FONTS['body_bold'], bg=COLORS['bg_light'],
                                    fg=COLORS['primary'], anchor='w', cursor='hand2')
            price_label.pack(fill='x')

            if is_refill:
                stock_color = COLORS['info']
                stock_text = f"Stok: ∞ (Tak Terbatas)"
            else:
                stock_color = COLORS['success'] if p['stock'] >= 10 else COLORS['warning']
                stock_text = f"Stok: {p['stock']} {p['unit']}"
            stock_label = tk.Label(card, text=stock_text,
                                    font=FONTS['small'], bg=COLORS['bg_light'],
                                    fg=stock_color, anchor='w', cursor='hand2')
            stock_label.pack(fill='x')

            # Bind click event
            product_data = p.copy()
            for widget in [card, name_label, price_label, stock_label]:
                widget.bind('<Button-1>', lambda e, pd=product_data: self._add_to_cart(pd))
                widget.bind('<Enter>', lambda e, c=card: c.config(bg=COLORS['accent_light']))
                widget.bind('<Leave>', lambda e, c=card: c.config(bg=COLORS['bg_light']))
                # Also update children bg
                widget.bind('<Enter>', lambda e, c=card: [
                    c.config(bg=COLORS['accent_light']),
                    *[w.config(bg=COLORS['accent_light']) for w in c.winfo_children()]
                ], add='+')
                widget.bind('<Leave>', lambda e, c=card: [
                    c.config(bg=COLORS['bg_light']),
                    *[w.config(bg=COLORS['bg_light']) for w in c.winfo_children()]
                ], add='+')

            col += 1
            if col >= 2:
                col = 0
                row += 1

    def _add_to_cart(self, product):
        """Tambah produk ke keranjang"""
        is_refill = db.is_water_refill_product(product['name'], product.get('category', ''))
        # Cek apakah sudah ada di keranjang
        for item in self.cart:
            if item['product_id'] == product['id']:
                # Cek stok (skip untuk produk isi ulang)
                if not is_refill and item['quantity'] >= product['stock']:
                    messagebox.showwarning("Peringatan", f"Stok {product['name']} tidak mencukupi!")
                    return
                item['quantity'] += 1
                item['subtotal'] = item['quantity'] * item['unit_price']
                self._refresh_cart()
                return

        # Produk baru di keranjang
        self.cart.append({
            'product_id': product['id'],
            'name': product['name'],
            'quantity': 1,
            'unit_price': product['sell_price'],
            'subtotal': product['sell_price'],
            'max_stock': 999999 if is_refill else product['stock'],
            'courier_fee_per_unit': int(product.get('courier_fee_per_unit', 0) or 0)
        })
        self._refresh_cart()

    def _refresh_cart(self):
        """Refresh tampilan keranjang"""
        for widget in self.cart_frame.winfo_children():
            widget.destroy()

        if not self.cart:
            self.cart_empty_label = tk.Label(
                self.cart_frame, text="Keranjang masih kosong\n\nKlik produk untuk menambahkan",
                font=FONTS['body'], bg=COLORS['white'], fg=COLORS['text_light'], justify='center'
            )
            self.cart_empty_label.pack(expand=True)
            self._update_total()
            return

        # Cart items with scroll
        canvas = tk.Canvas(self.cart_frame, bg=COLORS['white'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.cart_frame, orient='vertical', command=canvas.yview)
        items_frame = tk.Frame(canvas, bg=COLORS['white'])

        items_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas_win = canvas.create_window((0, 0), window=items_frame, anchor='nw')
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_win, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_cart_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind('<MouseWheel>', _on_cart_mousewheel)
        items_frame.bind('<MouseWheel>', _on_cart_mousewheel)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        for i, item in enumerate(self.cart):
            item_frame = tk.Frame(items_frame, bg=COLORS['white'], pady=6)
            item_frame.pack(fill='x', padx=5)

            # Nama & harga
            info_frame = tk.Frame(item_frame, bg=COLORS['white'])
            info_frame.pack(fill='x')

            tk.Label(info_frame, text=item['name'], font=FONTS['body_bold'],
                     bg=COLORS['white'], fg=COLORS['text_dark'], anchor='w').pack(side='left')

            # Tombol hapus
            del_btn = tk.Button(
                info_frame, text="✕", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['white'], fg=COLORS['danger'], relief='flat',
                cursor='hand2', command=lambda idx=i: self._remove_from_cart(idx)
            )
            del_btn.pack(side='right')

            # Quantity controls & subtotal
            qty_frame = tk.Frame(item_frame, bg=COLORS['white'])
            qty_frame.pack(fill='x', pady=(3, 0))

            tk.Label(qty_frame, text=f"@ {format_currency(item['unit_price'])}",
                     font=FONTS['small'], bg=COLORS['white'], fg=COLORS['text_light']).pack(side='left')

            # Subtotal
            tk.Label(qty_frame, text=format_currency(item['subtotal']),
                     font=FONTS['body_bold'], bg=COLORS['white'],
                     fg=COLORS['primary']).pack(side='right')

            # Qty buttons
            qty_ctrl = tk.Frame(qty_frame, bg=COLORS['white'])
            qty_ctrl.pack(side='right', padx=10)

            minus_btn = tk.Button(
                qty_ctrl, text="−", font=('Segoe UI', 10, 'bold'), width=3,
                bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
                cursor='hand2', command=lambda idx=i: self._change_qty(idx, -1)
            )
            minus_btn.pack(side='left')

            tk.Label(qty_ctrl, text=str(item['quantity']), font=FONTS['body_bold'],
                     bg=COLORS['white'], fg=COLORS['text_dark'], width=4).pack(side='left')

            plus_btn = tk.Button(
                qty_ctrl, text="+", font=('Segoe UI', 10, 'bold'), width=3,
                bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
                cursor='hand2', command=lambda idx=i: self._change_qty(idx, 1)
            )
            plus_btn.pack(side='left')

            # Separator
            sep = tk.Frame(items_frame, bg=COLORS['border_light'], height=1)
            sep.pack(fill='x', padx=5)

        def _bind_mousewheel(w):
            w.bind('<MouseWheel>', _on_cart_mousewheel)
            for child in w.winfo_children():
                _bind_mousewheel(child)
        _bind_mousewheel(items_frame)

        self._update_total()

    def _change_qty(self, index, change):
        """Ubah jumlah item di keranjang"""
        item = self.cart[index]
        new_qty = item['quantity'] + change
        if new_qty <= 0:
            self._remove_from_cart(index)
            return
        if new_qty > item['max_stock']:
            messagebox.showwarning("Peringatan", "Stok tidak mencukupi!")
            return
        item['quantity'] = new_qty
        item['subtotal'] = new_qty * item['unit_price']
        self._refresh_cart()

    def _remove_from_cart(self, index):
        """Hapus item dari keranjang"""
        self.cart.pop(index)
        self._refresh_cart()

    def _clear_cart(self):
        """Kosongkan keranjang"""
        if self.cart and messagebox.askyesno("Konfirmasi", "Kosongkan keranjang?"):
            self.cart = []
            self._refresh_cart()

    def _update_total(self):
        """Update total belanja termasuk delivery fee"""
        subtotal = sum(item['subtotal'] for item in self.cart)
        try:
            discount = float(self.discount_var.get().replace('.', '').replace(',', '') or 0)
        except ValueError:
            discount = 0

        delivery_fee = 0
        total = max(0, subtotal - discount)

        self.subtotal_label.config(text=format_currency(subtotal))

        # Update delivery fee label text
        if hasattr(self, 'delivery_fee_label'):
            self.delivery_fee_label.config(text=format_currency(delivery_fee))

        # Update upah kurir label text
        courier_wage = sum(item['quantity'] * item.get('courier_fee_per_unit', 0) for item in self.cart)
        if hasattr(self, 'courier_wage_label'):
            self.courier_wage_label.config(text=f"Upah Kurir: {format_currency(courier_wage)}")

        self.total_label.config(text=format_currency(total))

    def _get_customer_id(self):
        """Dapatkan customer ID dari pilihan"""
        selected = self.customer_var.get()
        if "ID:" in selected:
            try:
                return int(selected.split("ID:")[1].rstrip(")"))
            except (ValueError, IndexError):
                return None
        return None

    def _process_payment(self, method):
        """Proses pembayaran"""
        if not self.cart:
            messagebox.showwarning("Peringatan", "Keranjang masih kosong!")
            return

        subtotal = sum(item['subtotal'] for item in self.cart)
        try:
            discount = float(self.discount_var.get().replace('.', '').replace(',', '') or 0)
        except ValueError:
            discount = 0

        is_delivery = bool(self.is_delivery_var.get())
        courier_name = self.courier_var.get().strip()
        delivery_fee = 0
        total = max(0, subtotal - discount)

        courier_id = None
        if is_delivery:
            if not courier_name:
                messagebox.showwarning("Peringatan", "Pilihan 'Antar' dipilih. Anda wajib memilih kurir pengantar!")
                return
            if hasattr(self, 'courier_map') and courier_name in self.courier_map:
                courier_id = self.courier_map[courier_name]['id']
            else:
                c = db.get_courier_by_name(courier_name)
                if not c:
                    messagebox.showwarning("Peringatan", f"Kurir '{courier_name}' tidak valid!")
                    return
                courier_id = c['id']

        customer_id = self._get_customer_id()

        if method == 'hutang':
            if not customer_id:
                messagebox.showwarning("Peringatan",
                                       "Pilih pelanggan untuk pembayaran hutang!")
                return
            if messagebox.askyesno("Konfirmasi Hutang",
                                    f"Catat hutang {format_currency(total)} untuk pelanggan?"):
                items = [{'product_id': i['product_id'], 'quantity': i['quantity'],
                          'unit_price': i['unit_price']} for i in self.cart]
                cart_copy = list(self.cart)
                trx_id, invoice = db.create_transaction(
                    customer_id, self.user['id'], items, 'hutang', 0, discount,
                    is_delivery=is_delivery, courier_name=courier_name, delivery_fee=0,
                    courier_id=courier_id
                )
                self.cart = []
                self.is_delivery_var.set(0)
                self._toggle_delivery()
                self._refresh_cart()
                self._load_products()  # Refresh stok
                self._show_receipt(invoice, total, 0, 0, 'hutang', is_delivery, courier_name, delivery_fee=0, cart_items=cart_copy)

        elif method == 'cash':
            self._show_cash_dialog(total, customer_id, discount, is_delivery, courier_name, courier_id)

    def _show_cash_dialog(self, total, customer_id, discount, is_delivery=False, courier_name="", courier_id=None):
        """Dialog pembayaran cash"""
        dialog = tk.Toplevel(self)
        dialog.title("Pembayaran Cash")
        dialog.geometry("420x420")
        dialog.minsize(380, 360)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 210
        y = (dialog.winfo_screenheight() // 2) - 210
        dialog.geometry(f'+{x}+{y}')

        tk.Label(dialog, text="Pembayaran Cash", font=FONTS['subtitle'],
                 bg=COLORS['white'], fg=COLORS['primary_dark']).pack(side='top', pady=(15, 8))

        # Tombol aksi di-pack di BOTTOM terlebih dahulu agar selalu terlihat
        btn_frame = tk.Frame(dialog, bg=COLORS['white'])
        btn_frame.pack(side='bottom', fill='x', padx=30, pady=15)

        total_frame = tk.Frame(dialog, bg=COLORS['primary'], padx=20, pady=12)
        total_frame.pack(side='top', fill='x', padx=30)
        tk.Label(total_frame, text="Total Bayar", font=FONTS['body'],
                 bg=COLORS['primary'], fg=COLORS['accent_light']).pack(anchor='w')
        tk.Label(total_frame, text=format_currency(total), font=FONTS['big_number'],
                 bg=COLORS['primary'], fg=COLORS['text_white']).pack(anchor='w')

        form = tk.Frame(dialog, bg=COLORS['white'], padx=30)
        form.pack(side='top', fill='both', expand=True, pady=10)

        tk.Label(form, text="Jumlah Uang Diterima (Rp)", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(0, 5))

        paid_var = tk.StringVar()
        paid_entry = tk.Entry(form, textvariable=paid_var, font=('Segoe UI', 16, 'bold'),
                               relief='solid', bd=1, bg=COLORS['bg_light'], justify='right')
        paid_entry.pack(fill='x', ipady=8)
        paid_entry.configure(highlightthickness=2, highlightcolor=COLORS['primary'],
                              highlightbackground=COLORS['border'])
        paid_entry.focus_set()

        change_label = tk.Label(form, text="Kembalian: Rp 0", font=FONTS['heading'],
                                 bg=COLORS['white'], fg=COLORS['success'])
        change_label.pack(anchor='w', pady=(8, 0))

        def update_change(*args):
            try:
                paid = float(paid_var.get().replace('.', '').replace(',', '') or 0)
                change = paid - total
                if change >= 0:
                    change_label.config(text=f"Kembalian: {format_currency(change)}", fg=COLORS['success'])
                else:
                    change_label.config(text=f"Kurang: {format_currency(abs(change))}", fg=COLORS['danger'])
            except ValueError:
                change_label.config(text="Kembalian: -", fg=COLORS['text_light'])

        paid_var.trace('w', update_change)

        # Tombol uang pas
        exact_btn = tk.Button(
            form, text=f"Uang Pas ({format_currency(total)})", font=FONTS['small_bold'],
            bg=COLORS['info_bg'], fg=COLORS['info'], relief='flat', cursor='hand2',
            command=lambda: paid_var.set(str(int(total))), pady=4
        )
        exact_btn.pack(fill='x', pady=(8, 0))

        def process():
            try:
                paid = float(paid_var.get().replace('.', '').replace(',', '') or 0)
                if paid < total:
                    messagebox.showwarning("Peringatan", "Jumlah uang kurang!", parent=dialog)
                    return
                change = paid - total

                items = [{'product_id': i['product_id'], 'quantity': i['quantity'],
                          'unit_price': i['unit_price']} for i in self.cart]
                cart_copy = list(self.cart)
                trx_id, invoice = db.create_transaction(
                    customer_id, self.user['id'], items, 'cash', paid, discount,
                    is_delivery=is_delivery, courier_name=courier_name, delivery_fee=0,
                    courier_id=courier_id
                )

                delivery_fee = 0
                dialog.destroy()
                self.cart = []
                self.is_delivery_var.set(0)
                self._toggle_delivery()
                self._refresh_cart()
                self._load_products()
                self._show_receipt(invoice, total, paid, change, 'cash', is_delivery, courier_name, delivery_fee=0, cart_items=cart_copy)

            except ValueError:
                messagebox.showerror("Error", "Masukkan jumlah yang valid!", parent=dialog)

        paid_entry.bind('<Return>', lambda e: process())

        save_btn = tk.Button(
            btn_frame, text=f"  {ICONS['check']}  Proses & Simpan  ", font=FONTS['button'],
            bg=COLORS['success'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=process, padx=20, pady=8
        )
        save_btn.pack(side='left', padx=(0, 10))

        cancel_btn = tk.Button(
            btn_frame, text="Batal", font=FONTS['button'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=dialog.destroy, padx=20, pady=8
        )
        cancel_btn.pack(side='left')

    def _show_receipt(self, invoice, total, paid, change, method, is_delivery=False, courier_name="", delivery_fee=0, cart_items=None):
        """Tampilkan struk transaksi dengan tombol simpan struk"""
        receipt_items = cart_items if cart_items is not None else list(self.cart)

        dialog = tk.Toplevel(self)
        dialog.title(f"Transaksi Berhasil - {invoice}")
        dialog.geometry("440x620")
        dialog.minsize(400, 500)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 220
        y = (dialog.winfo_screenheight() // 2) - 310
        dialog.geometry(f'+{x}+{y}')

        # Header
        tk.Label(dialog, text="✅", font=('Segoe UI', 36),
                 bg=COLORS['white']).pack(side='top', pady=(15, 2))
        tk.Label(dialog, text="Transaksi Berhasil!", font=FONTS['subtitle'],
                 bg=COLORS['white'], fg=COLORS['success']).pack(side='top')

        sep = tk.Frame(dialog, bg=COLORS['border_light'], height=1)
        sep.pack(side='top', fill='x', padx=25, pady=10)

        # Buttons packed at BOTTOM first so they are ALWAYS visible
        btn_frame = tk.Frame(dialog, bg=COLORS['white'])
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=(10, 15))

        # Receipt info
        info_frame = tk.Frame(dialog, bg=COLORS['white'], padx=25)
        info_frame.pack(side='top', fill='x')

        def add_row(label, value, bold=False):
            row = tk.Frame(info_frame, bg=COLORS['white'])
            row.pack(fill='x', pady=2)
            tk.Label(row, text=label, font=FONTS['body'], bg=COLORS['white'],
                     fg=COLORS['text_medium']).pack(side='left')
            font = FONTS['body_bold'] if bold else FONTS['body']
            tk.Label(row, text=value, font=font, bg=COLORS['white'],
                     fg=COLORS['text_dark']).pack(side='right')

        add_row("No. Invoice:", invoice)
        add_row("Metode:", method.upper())
        add_row("Total:", format_currency(total), True)
        if is_delivery:
            add_row("Ongkir (Kurir):", format_currency(delivery_fee))
            add_row("Kurir:", courier_name)
        if method == 'cash':
            add_row("Dibayar:", format_currency(paid))
            add_row("Kembalian:", format_currency(change), True)

        sep2 = tk.Frame(dialog, bg=COLORS['border_light'], height=1)
        sep2.pack(side='top', fill='x', padx=25, pady=8)

        # Items list in a scrollable frame
        tk.Label(dialog, text="Daftar Pembelian:", font=FONTS['small_bold'],
                 bg=COLORS['white'], fg=COLORS['text_light']).pack(side='top', anchor='w', padx=25)

        items_container = tk.Frame(dialog, bg=COLORS['bg_light'], padx=10, pady=8,
                                   highlightbackground=COLORS['border_light'], highlightthickness=1)
        items_container.pack(side='top', fill='both', expand=True, padx=25, pady=(5, 5))

        canvas = tk.Canvas(items_container, bg=COLORS['bg_light'], highlightthickness=0)
        scrollbar = tk.Scrollbar(items_container, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_light'])

        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        for item in receipt_items:
            item_row = tk.Frame(scrollable_frame, bg=COLORS['bg_light'])
            item_row.pack(fill='x', pady=2)
            name = item.get('name') or item.get('product_name', 'Produk')
            qty = item.get('quantity', 1)
            sub = item.get('subtotal', 0)
            tk.Label(item_row, text=f"• {name} x{qty}",
                     font=FONTS['body'], bg=COLORS['bg_light'],
                     fg=COLORS['text_dark']).pack(side='left')
            tk.Label(item_row, text=format_currency(sub),
                     font=FONTS['body_bold'], bg=COLORS['bg_light'],
                     fg=COLORS['primary']).pack(side='right')

        def save_receipt_to_file():
            file_path = filedialog.asksaveasfilename(
                parent=dialog,
                title="Simpan Struk Transaksi",
                defaultextension=".txt",
                initialfile=f"Struk_{invoice}.txt",
                filetypes=[("Text File (*.txt)", "*.txt"), ("All Files (*.*)", "*.*")]
            )
            if not file_path:
                return
            try:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                kasir_name = self.user.get('full_name', 'Kasir')
                lines = [
                    "=" * 42,
                    "              DEPO AIR MINUM              ",
                    "=" * 42,
                    f"No. Invoice : {invoice}",
                    f"Tanggal     : {now_str}",
                    f"Kasir       : {kasir_name}",
                    f"Metode      : {method.upper()}",
                ]
                if is_delivery:
                    lines.append(f"Kurir       : {courier_name}")
                    lines.append(f"Ongkir      : {format_currency(delivery_fee)}")
                lines.append("-" * 42)
                lines.append(f"{'Produk':<24}{'Qty':>4}{'Subtotal':>14}")
                lines.append("-" * 42)
                for itm in receipt_items:
                    p_name = itm.get('name') or itm.get('product_name', 'Produk')
                    p_qty = itm.get('quantity', 1)
                    p_sub = itm.get('subtotal', 0)
                    lines.append(f"{p_name[:22]:<24}{p_qty:>4}{format_currency(p_sub):>14}")
                lines.append("-" * 42)
                lines.append(f"{'TOTAL':<24}{format_currency(total):>18}")
                if method == 'cash':
                    lines.append(f"{'DIBAYAR':<24}{format_currency(paid):>18}")
                    lines.append(f"{'KEMBALIAN':<24}{format_currency(change):>18}")
                lines.append("=" * 42)
                lines.append("       Terima Kasih Atas Kunjungan Anda!   ")
                lines.append("=" * 42)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(lines) + "\n")

                messagebox.showinfo("Berhasil", f"Struk berhasil disimpan di:\n{file_path}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan struk:\n{e}", parent=dialog)

        save_btn = tk.Button(
            btn_frame, text="  💾  Simpan Struk  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=save_receipt_to_file, pady=9
        )
        save_btn.pack(side='left', fill='x', expand=True, padx=(0, 10))

        close_btn = tk.Button(
            btn_frame, text="Tutup", font=FONTS['button'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=dialog.destroy, pady=9
        )
        close_btn.pack(side='right', fill='x', expand=True)
