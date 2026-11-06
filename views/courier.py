"""
Courier View - Halaman Pendataan Kurir & Upah Antar
Digunakan oleh Owner & Kasir untuk memantau upah kurir, pembayaran upah, dan status antaran.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from styles import COLORS, FONTS, ICONS, format_currency
import database as db


class CourierView(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=COLORS['bg_light'])
        self.user = user
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=COLORS['bg_light'])
        header.pack(fill='x', padx=20, pady=(20, 10))

        tk.Label(
            header, text="🚚  Pendataan Upah Kurir",
            font=FONTS['title'], bg=COLORS['bg_light'], fg=COLORS['text_dark']
        ).pack(side='left')

        # Header action buttons
        btn_box = tk.Frame(header, bg=COLORS['bg_light'])
        btn_box.pack(side='right')

        if self.user.get('role') == 'owner':
            add_courier_btn = tk.Button(
                btn_box, text=f"  {ICONS['add']}  Tambah Kurir  ", font=FONTS['button'],
                bg=COLORS['success'], fg=COLORS['text_white'], relief='flat',
                cursor='hand2', command=self._show_add_courier_dialog, padx=12, pady=6
            )
            add_courier_btn.pack(side='left', padx=(0, 8))
            add_courier_btn.bind('<Enter>', lambda e: add_courier_btn.config(bg='#1B5E20'))
            add_courier_btn.bind('<Leave>', lambda e: add_courier_btn.config(bg=COLORS['success']))

        refresh_btn = tk.Button(
            btn_box, text=f"  {ICONS['refresh']}  Refresh  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self.refresh_data, padx=12, pady=6
        )
        refresh_btn.pack(side='left')
        refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(bg=COLORS['primary_hover']))
        refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(bg=COLORS['primary']))

        # Main content with tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        # Tab 1: Ringkasan Kurir & Bayar Upah
        self.summary_tab = tk.Frame(self.notebook, bg=COLORS['white'])
        self.notebook.add(self.summary_tab, text="  📊 Ringkasan Kurir & Bayar Upah  ")

        # Tab 2: Rincian Upah Antaran
        self.detail_tab = tk.Frame(self.notebook, bg=COLORS['white'])
        self.notebook.add(self.detail_tab, text="  📋 Rincian Upah Antaran  ")

        # Tab 3: Riwayat Pembayaran Upah (Syarat 1)
        self.history_tab = tk.Frame(self.notebook, bg=COLORS['white'])
        self.notebook.add(self.history_tab, text="  📜 Riwayat Pembayaran Upah  ")

        self._build_summary_tab()
        self._build_detail_tab()
        self._build_history_tab()

    def _build_summary_tab(self):
        """Tab 1: Ringkasan per kurir dan tombol Bayar Upah Kurir"""
        # Stats cards
        self.stats_frame = tk.Frame(self.summary_tab, bg=COLORS['white'], padx=15, pady=15)
        self.stats_frame.pack(fill='x')

        # Action buttons frame (pack di BOTTOM lebih dulu agar selalu terlihat)
        action_frame = tk.Frame(self.summary_tab, bg=COLORS['white'], padx=15, pady=10)
        action_frame.pack(fill='x', side='bottom')

        is_owner = (self.user.get('role') == 'owner')

        if is_owner:
            pay_btn = tk.Button(
                action_frame, text="  💵  Bayar Upah Kurir  ", font=FONTS['button'],
                bg=COLORS['success'], fg=COLORS['text_white'], relief='flat',
                cursor='hand2', command=self._pay_courier_wage, padx=15, pady=8
            )
            pay_btn.pack(side='left', padx=(0, 10))
            pay_btn.bind('<Enter>', lambda e: pay_btn.config(bg='#1B5E20'))
            pay_btn.bind('<Leave>', lambda e: pay_btn.config(bg=COLORS['success']))

            edit_btn = tk.Button(
                action_frame, text=f"  {ICONS['edit']}  Edit Kurir  ", font=FONTS['body_bold'],
                bg=COLORS['primary_light'], fg=COLORS['text_white'], relief='flat',
                cursor='hand2', command=self._show_edit_courier_dialog, padx=12, pady=8
            )
            edit_btn.pack(side='left', padx=(0, 10))
            edit_btn.bind('<Enter>', lambda e: edit_btn.config(bg=COLORS['primary']))
            edit_btn.bind('<Leave>', lambda e: edit_btn.config(bg=COLORS['primary_light']))

            toggle_btn = tk.Button(
                action_frame, text="  🔄  Aktifkan / Nonaktifkan  ", font=FONTS['body_bold'],
                bg=COLORS['info'], fg=COLORS['text_white'], relief='flat',
                cursor='hand2', command=self._toggle_courier_status, padx=12, pady=8
            )
            toggle_btn.pack(side='left', padx=(0, 10))
            toggle_btn.bind('<Enter>', lambda e: toggle_btn.config(bg=COLORS['primary_hover']))
            toggle_btn.bind('<Leave>', lambda e: toggle_btn.config(bg=COLORS['info']))

            del_icon = ICONS.get('delete', '🗑️')
            del_btn = tk.Button(
                action_frame, text=f"  {del_icon}  Hapus Kurir  ", font=FONTS['body_bold'],
                bg=COLORS['danger'], fg=COLORS['text_white'], relief='flat',
                cursor='hand2', command=self._delete_courier, padx=12, pady=8
            )
            del_btn.pack(side='left')
            del_btn.bind('<Enter>', lambda e: del_btn.config(bg='#B71C1C'))
            del_btn.bind('<Leave>', lambda e: del_btn.config(bg=COLORS['danger']))

        # Table area
        table_frame = tk.Frame(self.summary_tab, bg=COLORS['white'], padx=15, pady=5)
        table_frame.pack(fill='both', expand=True, pady=(0, 5))

        tk.Label(table_frame, text="Ringkasan Saldo & Cara Bayar Kurir", font=FONTS['heading'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(0, 8))

        columns = ('id', 'name', 'phone', 'payment_type', 'total_deliveries', 'total_wage', 'paid_wage', 'balance', 'status')
        self.summary_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=8, selectmode='browse')

        self.summary_tree.heading('id', text='ID')
        self.summary_tree.heading('name', text='Nama Kurir')
        self.summary_tree.heading('phone', text='No. Telepon')
        self.summary_tree.heading('payment_type', text='Cara Bayar')
        self.summary_tree.heading('total_deliveries', text='Jml Antaran')
        self.summary_tree.heading('total_wage', text='Total Upah')
        self.summary_tree.heading('paid_wage', text='Sudah Dibayar')
        self.summary_tree.heading('balance', text='Saldo Belum Dibayar')
        self.summary_tree.heading('status', text='Status Kurir')

        self.summary_tree.column('id', width=45, anchor='center')
        self.summary_tree.column('name', width=150, anchor='w')
        self.summary_tree.column('phone', width=120, anchor='w')
        self.summary_tree.column('payment_type', width=110, anchor='center')
        self.summary_tree.column('total_deliveries', width=90, anchor='center')
        self.summary_tree.column('total_wage', width=120, anchor='e')
        self.summary_tree.column('paid_wage', width=120, anchor='e')
        self.summary_tree.column('balance', width=150, anchor='e')
        self.summary_tree.column('status', width=90, anchor='center')

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=scrollbar.set)
        self.summary_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _build_detail_tab(self):
        """Tab 2: Rincian Upah Antaran per transaksi dengan filter kurir, status, & rentang tanggal"""
        # Filters (Syarat 9)
        filter_frame = tk.Frame(self.detail_tab, bg=COLORS['bg_light'], padx=15, pady=10)
        filter_frame.pack(fill='x')

        tk.Label(filter_frame, text="Kurir:", font=FONTS['body_bold'],
                 bg=COLORS['bg_light'], fg=COLORS['text_dark']).pack(side='left')

        self.filter_courier_var = tk.StringVar(value="Semua Kurir")
        self.filter_courier_combo = ttk.Combobox(
            filter_frame, textvariable=self.filter_courier_var,
            font=FONTS['small'], state='readonly', width=16
        )
        self.filter_courier_combo.pack(side='left', padx=6)
        self.filter_courier_combo.bind('<<ComboboxSelected>>', lambda e: self._load_detail_data())

        tk.Label(filter_frame, text="Status:", font=FONTS['body_bold'],
                 bg=COLORS['bg_light'], fg=COLORS['text_dark']).pack(side='left', padx=(10, 0))

        self.filter_status_var = tk.StringVar(value="Semua")
        status_combo = ttk.Combobox(
            filter_frame, textvariable=self.filter_status_var,
            values=["Semua", "belum_dibayar", "sudah_dibayar"],
            font=FONTS['small'], state='readonly', width=14
        )
        status_combo.pack(side='left', padx=6)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self._load_detail_data())

        # Filter Rentang Tanggal (Syarat 9)
        tk.Label(filter_frame, text="Dari:", font=FONTS['body_bold'],
                 bg=COLORS['bg_light'], fg=COLORS['text_dark']).pack(side='left', padx=(10, 0))
        self.filter_date_from = tk.StringVar()
        tk.Entry(filter_frame, textvariable=self.filter_date_from, font=FONTS['small'],
                 width=11, relief='solid', bd=1).pack(side='left', padx=4)

        tk.Label(filter_frame, text="s/d:", font=FONTS['body_bold'],
                 bg=COLORS['bg_light'], fg=COLORS['text_dark']).pack(side='left', padx=(4, 0))
        self.filter_date_to = tk.StringVar()
        tk.Entry(filter_frame, textvariable=self.filter_date_to, font=FONTS['small'],
                 width=11, relief='solid', bd=1).pack(side='left', padx=4)

        filter_btn = tk.Button(
            filter_frame, text=" Filter ", font=FONTS['small_bold'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._load_detail_data, padx=8, pady=3
        )
        filter_btn.pack(side='left', padx=8)

        reset_btn = tk.Button(
            filter_frame, text=" Reset ", font=FONTS['small'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=self._reset_detail_filter, padx=6, pady=3
        )
        reset_btn.pack(side='left')

        # Table
        table_frame = tk.Frame(self.detail_tab, bg=COLORS['white'], padx=15, pady=5)
        table_frame.pack(fill='both', expand=True, pady=(5, 10))

        detail_cols = ('id', 'date', 'invoice', 'customer', 'courier', 'payment_type', 'amount', 'status', 'paid_at')
        self.detail_tree = ttk.Treeview(table_frame, columns=detail_cols, show='headings', height=12)

        self.detail_tree.heading('id', text='ID')
        self.detail_tree.heading('date', text='Tanggal')
        self.detail_tree.heading('invoice', text='No. Invoice')
        self.detail_tree.heading('customer', text='Pelanggan')
        self.detail_tree.heading('courier', text='Kurir')
        self.detail_tree.heading('payment_type', text='Cara Bayar')
        self.detail_tree.heading('amount', text='Upah Antar (Rp)')
        self.detail_tree.heading('status', text='Status Upah')
        self.detail_tree.heading('paid_at', text='Tanggal Bayar')

        self.detail_tree.column('id', width=45, anchor='center')
        self.detail_tree.column('date', width=100, anchor='center')
        self.detail_tree.column('invoice', width=130, anchor='w')
        self.detail_tree.column('customer', width=140, anchor='w')
        self.detail_tree.column('courier', width=120, anchor='w')
        self.detail_tree.column('payment_type', width=90, anchor='center')
        self.detail_tree.column('amount', width=110, anchor='e')
        self.detail_tree.column('status', width=110, anchor='center')
        self.detail_tree.column('paid_at', width=130, anchor='center')

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.detail_tree.yview)
        self.detail_tree.configure(yscrollcommand=scrollbar.set)
        self.detail_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _reset_detail_filter(self):
        self.filter_courier_var.set("Semua Kurir")
        self.filter_status_var.set("Semua")
        self.filter_date_from.set("")
        self.filter_date_to.set("")
        self._load_detail_data()

    def _build_history_tab(self):
        """Tab 3: Riwayat Pembayaran Upah Kurir (Syarat 1)"""
        table_frame = tk.Frame(self.history_tab, bg=COLORS['white'], padx=15, pady=15)
        table_frame.pack(fill='both', expand=True)

        tk.Label(table_frame, text="Riwayat Pembayaran Upah Kurir (Tabel courier_payments)", font=FONTS['heading'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(0, 10))

        history_cols = ('id', 'date', 'courier', 'total', 'paid_by', 'expense_id', 'notes')
        self.history_tree = ttk.Treeview(table_frame, columns=history_cols, show='headings', height=12)

        self.history_tree.heading('id', text='ID Bayar')
        self.history_tree.heading('date', text='Tanggal & Waktu Bayar')
        self.history_tree.heading('courier', text='Kurir')
        self.history_tree.heading('total', text='Total Dibayar (Rp)')
        self.history_tree.heading('paid_by', text='Dibayar Oleh')
        self.history_tree.heading('expense_id', text='Ref Pengeluaran')
        self.history_tree.heading('notes', text='Catatan')

        self.history_tree.column('id', width=60, anchor='center')
        self.history_tree.column('date', width=140, anchor='center')
        self.history_tree.column('courier', width=130, anchor='w')
        self.history_tree.column('total', width=130, anchor='e')
        self.history_tree.column('paid_by', width=120, anchor='w')
        self.history_tree.column('expense_id', width=110, anchor='center')
        self.history_tree.column('notes', width=200, anchor='w')

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def refresh_data(self):
        """Refresh semua data view"""
        self._load_stats()
        self._load_summary_data()
        self._load_detail_data()
        self._load_history_data()
        self._load_courier_filter()

    def _load_stats(self):
        """Muat kartu statistik upah kurir"""
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        try:
            stats = db.get_courier_stats()
        except Exception:
            stats = {'unpaid_total': 0, 'unpaid_count': 0,
                     'paid_total': 0, 'paid_count': 0,
                     'today_total': 0, 'today_count': 0}

        cards_data = [
            ("Antaran Hari Ini", f"{stats['today_count']} kali", format_currency(stats['today_total']),
             COLORS['primary'], COLORS['accent_light']),
            ("Saldo Belum Dibayar (Hutang Upah)", f"{stats['unpaid_count']} antaran", format_currency(stats['unpaid_total']),
             COLORS['warning'], COLORS['warning_bg']),
            ("Upah Sudah Dibayar", f"{stats['paid_count']} antaran", format_currency(stats['paid_total']),
             COLORS['success'], '#E8F5E9'),
        ]

        for i, (title, count_text, amount_text, color, bg) in enumerate(cards_data):
            card = tk.Frame(self.stats_frame, bg=bg, padx=18, pady=12,
                            highlightbackground=color, highlightthickness=2)
            card.pack(side='left', fill='x', expand=True, padx=(0, 10) if i < 2 else (0, 0))

            tk.Label(card, text=title, font=FONTS['body_bold'], bg=bg, fg=COLORS['text_dark']).pack(anchor='w')
            tk.Label(card, text=amount_text, font=FONTS['medium_number'], bg=bg, fg=color).pack(anchor='w', pady=(2, 0))
            tk.Label(card, text=count_text, font=FONTS['small'], bg=bg, fg=COLORS['text_medium']).pack(anchor='w')

    def _load_summary_data(self):
        """Muat ringkasan per kurir"""
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)

        try:
            summary = db.get_courier_wage_summary()
        except Exception:
            summary = []

        for s in summary:
            status_text = "Aktif" if s['is_active'] == 1 else "Nonaktif"
            pay_type_display = "Langsung" if s['payment_type'] == 'langsung' else "Dikumpulkan"
            self.summary_tree.insert('', 'end', iid=str(s['courier_id']), values=(
                s['courier_id'],
                s['courier_name'],
                s.get('phone') or '-',
                pay_type_display,
                f"{s['total_deliveries']} kali",
                format_currency(s['total_wage']),
                format_currency(s['paid_wage']),
                format_currency(s['balance']),
                status_text,
            ))

    def _load_detail_data(self):
        """Muat rincian antaran dengan filter"""
        for item in self.detail_tree.get_children():
            self.detail_tree.delete(item)

        courier_filter = self.filter_courier_var.get()
        status_filter = self.filter_status_var.get()

        courier_id = None
        if courier_filter != "Semua Kurir":
            c = db.get_courier_by_name(courier_filter)
            if c:
                courier_id = c['id']

        status = None if status_filter == "Semua" else status_filter
        start_date = self.filter_date_from.get().strip() or None
        end_date = self.filter_date_to.get().strip() or None

        try:
            wages = db.get_courier_wages(courier_id=courier_id, status=status,
                                         start_date=start_date, end_date=end_date)
        except Exception:
            wages = []

        status_display = {
            'belum_dibayar': '⏳ Belum Dibayar',
            'sudah_dibayar': '✅ Sudah Dibayar',
        }

        for w in wages:
            date_str = w.get('wage_date', '')
            paid_str = w.get('paid_at') or '-'
            if paid_str and paid_str != '-':
                try:
                    dt = datetime.strptime(paid_str[:19], "%Y-%m-%d %H:%M:%S")
                    paid_str = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

            pay_type = "Langsung" if w.get('payment_type') == 'langsung' else "Dikumpulkan"

            self.detail_tree.insert('', 'end', values=(
                w['id'],
                date_str,
                w.get('invoice_number', '-'),
                w.get('customer_name', 'Umum'),
                w['courier_name'],
                pay_type,
                format_currency(w['amount']),
                status_display.get(w['status'], w['status']),
                paid_str,
            ))

    def _load_history_data(self):
        """Muat riwayat dari courier_payments (Syarat 1)"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        try:
            payments = db.get_courier_payments()
        except Exception:
            payments = []

        for p in payments:
            paid_time = p.get('paid_at', '')
            try:
                dt = datetime.strptime(paid_time[:19], "%Y-%m-%d %H:%M:%S")
                paid_time = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

            exp_ref = f"EXP #{p['expense_id']}" if p.get('expense_id') else '-'

            self.history_tree.insert('', 'end', values=(
                p['id'],
                paid_time,
                p['courier_name'],
                format_currency(p['total']),
                p.get('paid_by_name') or '-',
                exp_ref,
                p.get('notes') or '-',
            ))

    def _load_courier_filter(self):
        """Muat nama-nama kurir ke dropdown filter"""
        try:
            names = db.get_all_courier_names(active_only=False)
        except Exception:
            names = []
        self.filter_courier_combo['values'] = ["Semua Kurir"] + names

    def _pay_courier_wage(self):
        """Tombol Bayar Upah Kurir (Khusus Owner) - Fleksibel / Cicilan"""
        # Validasi role Owner di logika program
        if self.user.get('role') != 'owner':
            messagebox.showerror("Akses Ditolak", "Hanya Owner yang dapat melakukan pembayaran upah kurir!")
            return

        selected = self.summary_tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih kurir dari tabel ringkasan terlebih dahulu!")
            return

        values = self.summary_tree.item(selected[0], 'values')
        courier_id = int(values[0])
        courier_name = values[1]

        # Ambil data kurir & saldo belum dibayar
        summary = db.get_courier_wage_summary(courier_id=courier_id)
        if not summary:
            messagebox.showerror("Error", "Data kurir tidak ditemukan!")
            return

        c_data = summary[0]
        balance = c_data['balance']
        if balance <= 0:
            messagebox.showinfo("Info", f"Kurir '{courier_name}' tidak memiliki saldo upah yang belum dibayar.")
            return

        # Modal dialog konfirmasi pembayaran
        dialog = tk.Toplevel(self)
        dialog.title("Bayar Upah Kurir")
        dialog.geometry("480x520")
        dialog.minsize(440, 480)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 240
        y = (dialog.winfo_screenheight() // 2) - 260
        dialog.geometry(f'+{x}+{y}')

        tk.Label(dialog, text="💵 Pembayaran Upah Kurir", font=FONTS['subtitle'],
                 bg=COLORS['white'], fg=COLORS['primary_dark']).pack(side='top', pady=(18, 4))

        tk.Label(dialog, text=f"Kurir: {courier_name}", font=FONTS['heading'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(side='top', pady=(0, 12))

        # Bottom buttons
        btn_frame = tk.Frame(dialog, bg=COLORS['white'])
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=(10, 18))

        # Info Box
        info_frame = tk.Frame(dialog, bg=COLORS['info_bg'], padx=15, pady=10,
                              highlightbackground=COLORS['border_light'], highlightthickness=1)
        info_frame.pack(side='top', fill='x', padx=25)

        tk.Label(info_frame, text=f"Cara Bayar: {c_data['payment_type'].upper()}",
                 font=FONTS['body'], bg=COLORS['info_bg'], fg=COLORS['text_dark']).pack(anchor='w')
        tk.Label(info_frame, text=f"Total Saldo Belum Dibayar: {format_currency(balance)}",
                 font=FONTS['body_bold'], bg=COLORS['info_bg'], fg=COLORS['primary']).pack(anchor='w', pady=(3, 0))

        # Form
        form = tk.Frame(dialog, bg=COLORS['white'], padx=25)
        form.pack(side='top', fill='both', expand=True, pady=12)

        # Nominal Pembayaran
        tk.Label(form, text="Nominal Pembayaran (Rp) *:", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(4, 2))

        amount_var = tk.StringVar(value=str(balance))
        amount_entry = tk.Entry(form, textvariable=amount_var, font=FONTS['input'],
                                relief='solid', bd=1, bg=COLORS['bg_light'])
        amount_entry.pack(fill='x', ipady=6)

        # Quick action buttons
        quick_frame = tk.Frame(form, bg=COLORS['white'])
        quick_frame.pack(fill='x', pady=(6, 4))

        tk.Label(quick_frame, text="Pilihan Cepat:", font=FONTS['small'],
                 bg=COLORS['white'], fg=COLORS['text_medium']).pack(side='left', padx=(0, 8))

        def set_full():
            amount_var.set(str(balance))

        def set_half():
            half = max(1, balance // 2)
            amount_var.set(str(half))

        full_btn = tk.Button(quick_frame, text="Bayar Semua (100%)", font=FONTS['small'],
                             bg=COLORS['primary_light'], fg=COLORS['text_white'], relief='flat',
                             cursor='hand2', command=set_full, padx=8, pady=3)
        full_btn.pack(side='left', padx=(0, 6))

        half_btn = tk.Button(quick_frame, text="Bayar Setengah (50%)", font=FONTS['small'],
                             bg='#FF9800', fg=COLORS['text_white'], relief='flat',
                             cursor='hand2', command=set_half, padx=8, pady=3)
        half_btn.pack(side='left')

        # Live calculation label
        calc_label = tk.Label(form, text="Sisa saldo setelah dibayar: Rp 0 (LUNAS)",
                              font=FONTS['body_bold'], bg=COLORS['white'], fg=COLORS['success'])
        calc_label.pack(anchor='w', pady=(6, 10))

        def update_calc(*args):
            raw = amount_var.get().strip().replace('.', '').replace(',', '').replace(' ', '')
            if not raw:
                calc_label.config(text="Masukkan nominal pembayaran", fg=COLORS['text_medium'])
                return
            try:
                val = int(raw)
                if val <= 0:
                    calc_label.config(text="Nominal harus lebih dari Rp 0", fg=COLORS['danger'])
                elif val > balance:
                    calc_label.config(text=f"Melebihi saldo! Maksimal: {format_currency(balance)}", fg=COLORS['danger'])
                else:
                    remaining = balance - val
                    if remaining == 0:
                        calc_label.config(text="Sisa saldo setelah dibayar: Rp 0 (LUNAS)", fg=COLORS['success'])
                    else:
                        calc_label.config(text=f"Sisa saldo setelah dibayar: {format_currency(remaining)} (Cicilan)", fg='#E65100')
            except ValueError:
                calc_label.config(text="Nominal tidak valid (hanya angka)", fg=COLORS['danger'])

        amount_var.trace_add('write', update_calc)

        # Input catatan
        tk.Label(form, text="Catatan Pembayaran (opsional):", font=FONTS['body'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(4, 2))
        notes_var = tk.StringVar(value=f"Pelunasan upah kurir {courier_name}")
        notes_entry = tk.Entry(form, textvariable=notes_var, font=FONTS['input'],
                               relief='solid', bd=1, bg=COLORS['bg_light'])
        notes_entry.pack(fill='x', ipady=6)

        def process_payment():
            raw = amount_var.get().strip().replace('.', '').replace(',', '').replace(' ', '')
            try:
                pay_val = int(raw)
            except ValueError:
                messagebox.showerror("Input Tidak Valid", "Nominal pembayaran harus berupa angka bulat!")
                amount_entry.focus_set()
                return

            if pay_val <= 0:
                messagebox.showerror("Input Tidak Valid", "Nominal pembayaran harus lebih dari 0!")
                amount_entry.focus_set()
                return

            if pay_val > balance:
                messagebox.showerror("Melebihi Saldo", f"Nominal pembayaran ({format_currency(pay_val)}) melebihi total saldo belum dibayar ({format_currency(balance)})!")
                amount_entry.focus_set()
                return

            note_text = notes_var.get().strip()
            if not note_text:
                if pay_val == balance:
                    note_text = f"Pelunasan upah kurir {courier_name}"
                else:
                    note_text = f"Cicilan upah kurir {courier_name}"

            try:
                count_done, total_done, payment_id = db.pay_courier_wages(
                    courier_id=courier_id,
                    user_id=self.user['id'],
                    notes=note_text,
                    amount=pay_val
                )
                dialog.destroy()
                self.refresh_data()
                if count_done > 0:
                    remaining_after = balance - total_done
                    if remaining_after <= 0:
                        messagebox.showinfo(
                            "Pembayaran Lunas Berhasil",
                            f"Berhasil melunasi upah kurir '{courier_name}'!\n\n"
                            f"• Jumlah Antaran : {count_done} antaran\n"
                            f"• Total Dibayar  : {format_currency(total_done)}\n"
                            f"• Sisa Saldo     : Rp 0 (LUNAS)\n"
                            f"• Tercatat di Pengeluaran kategori 'Upah Kurir'"
                        )
                    else:
                        messagebox.showinfo(
                            "Pembayaran Cicilan Berhasil",
                            f"Berhasil membayar cicilan upah kurir '{courier_name}'!\n\n"
                            f"• Jumlah Antaran : {count_done} antaran tercakup\n"
                            f"• Total Dibayar  : {format_currency(total_done)}\n"
                            f"• Sisa Saldo     : {format_currency(remaining_after)}\n"
                            f"• Tercatat di Pengeluaran kategori 'Upah Kurir'"
                        )
                else:
                    messagebox.showinfo("Info", "Tidak ada upah yang perlu dibayar.")
            except Exception as e:
                messagebox.showerror("Gagal", f"Terjadi kesalahan saat memproses pembayaran:\n{e}")

        tk.Button(
            btn_frame, text=f"  {ICONS['check']}  Proses Pembayaran  ", font=FONTS['button'],
            bg=COLORS['success'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=process_payment, padx=15, pady=8
        ).pack(side='left', padx=(0, 10))

        tk.Button(
            btn_frame, text="Batal", font=FONTS['button'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=dialog.destroy, padx=20, pady=8
        ).pack(side='left')

    def _show_add_courier_dialog(self):
        """Dialog tambah master kurir"""
        self._show_courier_form_dialog("Tambah Kurir Baru")

    def _show_edit_courier_dialog(self):
        """Dialog edit master kurir"""
        selected = self.summary_tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih kurir dari tabel ringkasan!")
            return

        values = self.summary_tree.item(selected[0], 'values')
        courier_id = int(values[0])
        courier = db.get_courier_by_id(courier_id)
        if not courier:
            messagebox.showerror("Error", "Data kurir tidak ditemukan!")
            return

        self._show_courier_form_dialog("Edit Data Kurir", courier)

    def _show_courier_form_dialog(self, title, courier=None):
        """Form dialog tambah / edit kurir (Syarat 8)"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("460x480")
        dialog.minsize(420, 450)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 230
        y = (dialog.winfo_screenheight() // 2) - 240
        dialog.geometry(f'+{x}+{y}')

        tk.Label(dialog, text=title, font=FONTS['subtitle'],
                 bg=COLORS['white'], fg=COLORS['primary_dark']).pack(side='top', pady=(20, 10))

        # Bottom buttons (Pack terlebih dahulu di bottom agar selalu terlihat)
        btn_frame = tk.Frame(dialog, bg=COLORS['white'])
        btn_frame.pack(side='bottom', fill='x', padx=30, pady=(10, 20))

        form = tk.Frame(dialog, bg=COLORS['white'], padx=30)
        form.pack(side='top', fill='both', expand=True, pady=10)

        # Nama
        tk.Label(form, text="Nama Kurir *", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(5, 2))
        name_var = tk.StringVar(value=courier['name'] if courier else "")
        name_entry = tk.Entry(form, textvariable=name_var, font=FONTS['input'],
                              relief='solid', bd=1, bg=COLORS['bg_light'])
        name_entry.pack(fill='x', ipady=5)
        name_entry.focus_set()

        # No Telepon
        tk.Label(form, text="Nomor Telepon (opsional)", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(10, 2))
        phone_var = tk.StringVar(value=courier.get('phone', '') if courier else "")
        phone_entry = tk.Entry(form, textvariable=phone_var, font=FONTS['input'],
                               relief='solid', bd=1, bg=COLORS['bg_light'])
        phone_entry.pack(fill='x', ipady=5)

        # Pengaturan Cara Bayar (Syarat 4 & 8)
        tk.Label(form, text="Pengaturan Cara Bayar Upah *", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(10, 2))
        tk.Label(form, text="(Catatan: perubahan cara bayar hanya berlaku untuk transaksi berikutnya)",
                 font=FONTS['small'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')

        payment_type_var = tk.StringVar(value=courier['payment_type'] if courier else "dikumpulkan")
        radio_frame = tk.Frame(form, bg=COLORS['white'])
        radio_frame.pack(anchor='w', pady=(4, 5))

        tk.Radiobutton(
            radio_frame, text="Dikumpulkan (Akumulasi / Dibayar Owner Nanti)",
            variable=payment_type_var, value="dikumpulkan",
            font=FONTS['body'], bg=COLORS['white'], activebackground=COLORS['white']
        ).pack(anchor='w', pady=2)

        tk.Radiobutton(
            radio_frame, text="Langsung (Otomatis Sudah Dibayar Tiap Transaksi)",
            variable=payment_type_var, value="langsung",
            font=FONTS['body'], bg=COLORS['white'], activebackground=COLORS['white']
        ).pack(anchor='w', pady=2)

        def save_courier():
            name = name_var.get().strip()
            phone = phone_var.get().strip()
            pay_type = payment_type_var.get()

            if not name:
                messagebox.showwarning("Peringatan", "Nama kurir harus diisi!", parent=dialog)
                return

            try:
                if courier:
                    db.update_courier(
                        courier_id=courier['id'],
                        name=name,
                        phone=phone,
                        payment_type=pay_type,
                        is_active=courier['is_active']
                    )
                    messagebox.showinfo("Berhasil", f"Data kurir '{name}' berhasil diperbarui!", parent=dialog)
                else:
                    db.add_courier(name=name, phone=phone, payment_type=pay_type)
                    messagebox.showinfo("Berhasil", f"Kurir baru '{name}' berhasil ditambahkan!", parent=dialog)

                dialog.destroy()
                self.refresh_data()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan data kurir:\n{e}", parent=dialog)

        # Tombol Simpan
        save_icon = ICONS.get('save', '💾')
        save_btn = tk.Button(
            btn_frame, text=f"  {save_icon}  Simpan  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=save_courier, padx=24, pady=8
        )
        save_btn.pack(side='left', padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg=COLORS['primary_hover']))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg=COLORS['primary']))

        # Tombol Batal
        cancel_btn = tk.Button(
            btn_frame, text="  Batal  ", font=FONTS['button'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=dialog.destroy, padx=20, pady=8
        )
        cancel_btn.pack(side='left')

        # Keyboard shortcuts
        name_entry.bind('<Return>', lambda e: save_courier())
        phone_entry.bind('<Return>', lambda e: save_courier())
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def _toggle_courier_status(self):
        """Aktifkan atau nonaktifkan kurir (Syarat 8: tidak dihapus)"""
        selected = self.summary_tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih kurir dari tabel ringkasan!")
            return

        values = self.summary_tree.item(selected[0], 'values')
        courier_id = int(values[0])
        courier_name = values[1]
        current_status = values[8]

        new_action = "menonaktifkan" if current_status == "Aktif" else "mengaktifkan"
        if messagebox.askyesno("Konfirmasi", f"Apakah Anda yakin ingin {new_action} kurir '{courier_name}'?"):
            db.toggle_courier_active(courier_id)
            self.refresh_data()
            messagebox.showinfo("Berhasil", f"Status kurir '{courier_name}' berhasil diubah!")

    def _delete_courier(self):
        """Hapus kurir (Khusus Owner)"""
        if self.user.get('role') != 'owner':
            messagebox.showerror("Akses Ditolak", "Hanya Owner yang dapat menghapus kurir!")
            return

        selected = self.summary_tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih kurir dari tabel ringkasan yang ingin dihapus!")
            return

        values = self.summary_tree.item(selected[0], 'values')
        courier_id = int(values[0])
        courier_name = values[1]

        # Ambil data terkini kurir untuk cek saldo belum dibayar
        summary = db.get_courier_wage_summary(courier_id=courier_id)
        if summary:
            balance = summary[0]['balance']
            if balance > 0:
                messagebox.showwarning(
                    "Tidak Dapat Dihapus",
                    f"Kurir '{courier_name}' masih memiliki saldo upah belum dibayar sebesar {format_currency(balance)}.\n\n"
                    "Silakan bayar atau lunasi saldo upah kurir terlebih dahulu sebelum menghapus kurir ini."
                )
                return

        if not messagebox.askyesno(
            "Konfirmasi Hapus",
            f"Apakah Anda yakin ingin menghapus kurir '{courier_name}'?\n\n"
            "Catatan: Jika kurir pernah memiliki riwayat transaksi atau upah, data kurir akan dinonaktifkan dan disembunyikan agar pembukuan dan laporan keuangan tetap aman & akurat."
        ):
            return

        try:
            db.delete_courier(courier_id)
            self.refresh_data()
            messagebox.showinfo("Berhasil", f"Kurir '{courier_name}' berhasil dihapus.")
        except Exception as e:
            messagebox.showerror("Gagal", f"Terjadi kesalahan saat menghapus kurir:\n{e}")

