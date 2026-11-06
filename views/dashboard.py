
import tkinter as tk
from datetime import datetime
from styles import COLORS, FONTS, ICONS, format_currency, format_number
import database as db


class DashboardView(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=COLORS['bg_light'])
        self.user = user
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # Scrollable area
        canvas = tk.Canvas(self, bg=COLORS['bg_light'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient='vertical', command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=COLORS['bg_light'])

        self.scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind mousewheel
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))

        # Header
        header = tk.Frame(self.scroll_frame, bg=COLORS['bg_light'])
        header.pack(fill='x', padx=25, pady=(25, 5))

        tk.Label(
            header, text=f"{ICONS['dashboard']}  Dashboard",
            font=FONTS['title'], bg=COLORS['bg_light'], fg=COLORS['text_dark']
        ).pack(side='left')

        self.date_label = tk.Label(
            header, text=datetime.now().strftime("%A, %d %B %Y"),
            font=FONTS['body'], bg=COLORS['bg_light'], fg=COLORS['text_light']
        )
        self.date_label.pack(side='right')

        # Welcome message
        welcome_frame = tk.Frame(self.scroll_frame, bg=COLORS['primary'], padx=25, pady=18)
        welcome_frame.pack(fill='x', padx=25, pady=(10, 20))

        tk.Label(
            welcome_frame,
            text=f"Selamat Datang, {self.user['full_name']}! 👋",
            font=FONTS['subtitle'], bg=COLORS['primary'], fg=COLORS['text_white']
        ).pack(side='left')

        refresh_btn = tk.Button(
            welcome_frame, text=f"{ICONS['refresh']}  Refresh", font=FONTS['small_bold'],
            bg=COLORS['white'], fg=COLORS['primary'], relief='flat', cursor='hand2',
            command=self.refresh_data, padx=15, pady=5
        )
        refresh_btn.pack(side='right')

        # Stats cards container
        self.stats_frame = tk.Frame(self.scroll_frame, bg=COLORS['bg_light'])
        self.stats_frame.pack(fill='x', padx=25, pady=(0, 10))

        # Second row stats
        self.stats_frame2 = tk.Frame(self.scroll_frame, bg=COLORS['bg_light'])
        self.stats_frame2.pack(fill='x', padx=25, pady=(0, 20))

        # Bottom section: recent transactions & low stock
        bottom_frame = tk.Frame(self.scroll_frame, bg=COLORS['bg_light'])
        bottom_frame.pack(fill='x', padx=25, pady=(0, 25))
        bottom_frame.columnconfigure(0, weight=3)
        bottom_frame.columnconfigure(1, weight=2)

        # Transaksi terakhir
        self.recent_frame = tk.LabelFrame(
            bottom_frame, text=f"  {ICONS['transaction']}  Transaksi Terakhir  ",
            font=FONTS['heading'], bg=COLORS['white'], fg=COLORS['text_dark'],
            relief='solid', bd=1, padx=15, pady=15
        )
        self.recent_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

        # Stok rendah
        self.lowstock_frame = tk.LabelFrame(
            bottom_frame, text=f"  {ICONS['warning']}  Stok Rendah  ",
            font=FONTS['heading'], bg=COLORS['white'], fg=COLORS['danger'],
            relief='solid', bd=1, padx=15, pady=15
        )
        self.lowstock_frame.grid(row=0, column=1, sticky='nsew')

    def _create_stat_card(self, parent, title, value, icon, color, row=0, col=0):
        """Buat kartu statistik"""
        card = tk.Frame(parent, bg=COLORS['white'], padx=20, pady=18,
                        highlightbackground=COLORS['border_light'], highlightthickness=1)
        card.grid(row=row, column=col, sticky='nsew', padx=5, pady=5)

        # Icon and title row
        top = tk.Frame(card, bg=COLORS['white'])
        top.pack(fill='x')

        tk.Label(top, text=icon, font=('Segoe UI', 20), bg=COLORS['white']).pack(side='left')
        tk.Label(top, text=title, font=FONTS['small_bold'], bg=COLORS['white'],
                 fg=COLORS['text_light']).pack(side='right')

        # Value
        tk.Label(card, text=value, font=FONTS['big_number'], bg=COLORS['white'],
                 fg=color, anchor='w').pack(fill='x', pady=(8, 0))

        return card

    def refresh_data(self):
        """Refresh semua data dashboard"""
        stats = db.get_dashboard_stats()

        # Clear existing cards
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        for widget in self.stats_frame2.winfo_children():
            widget.destroy()

        self.stats_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.stats_frame2.columnconfigure((0, 1, 2, 3), weight=1)

        # Row 1 stats
        self._create_stat_card(
            self.stats_frame, "Penjualan Hari Ini",
            format_currency(stats['today_sales']),
            ICONS['money'], COLORS['primary'], 0, 0
        )
        self._create_stat_card(
            self.stats_frame, "Transaksi Hari Ini",
            format_number(stats['today_transactions']),
            ICONS['cart'], COLORS['success'], 0, 1
        )
        self._create_stat_card(
            self.stats_frame, "Total Hutang",
            format_currency(stats['total_debt']),
            ICONS['debt'], COLORS['danger'], 0, 2
        )
        self._create_stat_card(
            self.stats_frame, "Pengeluaran Hari Ini",
            format_currency(stats['today_expenses']),
            ICONS['expense'], COLORS['warning'], 0, 3
        )

        # Row 2 stats
        self._create_stat_card(
            self.stats_frame2, "Penjualan Bulan Ini",
            format_currency(stats['month_sales']),
            ICONS['report'], COLORS['primary_dark'], 0, 0
        )
        self._create_stat_card(
            self.stats_frame2, "Pengeluaran Bulan Ini",
            format_currency(stats['month_expenses']),
            ICONS['expense'], COLORS['warning'], 0, 1
        )
        self._create_stat_card(
            self.stats_frame2, "Total Produk",
            format_number(stats['total_products']),
            ICONS['product'], COLORS['info'], 0, 2
        )
        self._create_stat_card(
            self.stats_frame2, "Total Pelanggan",
            format_number(stats['total_customers']),
            ICONS['customer'], COLORS['accent'], 0, 3
        )

        # Recent transactions
        for widget in self.recent_frame.winfo_children():
            widget.destroy()

        recent = db.get_recent_transactions(8)
        if recent:
            # Header
            header = tk.Frame(self.recent_frame, bg=COLORS['white'])
            header.pack(fill='x', pady=(0, 8))
            for i, text in enumerate(["Invoice", "Pelanggan", "Total", "Metode", "Waktu"]):
                tk.Label(header, text=text, font=FONTS['small_bold'], bg=COLORS['white'],
                         fg=COLORS['text_light'], width=15 if i < 2 else 12, anchor='w').pack(side='left')

            sep = tk.Frame(self.recent_frame, bg=COLORS['border_light'], height=1)
            sep.pack(fill='x', pady=(0, 5))

            for trx in recent:
                row = tk.Frame(self.recent_frame, bg=COLORS['white'])
                row.pack(fill='x', pady=3)

                tk.Label(row, text=trx['invoice_number'], font=FONTS['small'],
                         bg=COLORS['white'], fg=COLORS['primary'], width=15, anchor='w').pack(side='left')
                tk.Label(row, text=trx['customer_name'], font=FONTS['small'],
                         bg=COLORS['white'], fg=COLORS['text_dark'], width=15, anchor='w').pack(side='left')
                tk.Label(row, text=format_currency(trx['total']), font=FONTS['small_bold'],
                         bg=COLORS['white'], fg=COLORS['success'], width=12, anchor='w').pack(side='left')

                method_color = COLORS['primary'] if trx['payment_method'] == 'cash' else COLORS['warning']
                tk.Label(row, text=trx['payment_method'].upper(), font=FONTS['small_bold'],
                         bg=COLORS['white'], fg=method_color, width=12, anchor='w').pack(side='left')

                time_str = trx['created_at'][:16] if trx['created_at'] else ''
                tk.Label(row, text=time_str, font=FONTS['small'],
                         bg=COLORS['white'], fg=COLORS['text_light'], width=12, anchor='w').pack(side='left')
        else:
            tk.Label(self.recent_frame, text="Belum ada transaksi", font=FONTS['body'],
                     bg=COLORS['white'], fg=COLORS['text_light']).pack(pady=20)

        # Low stock products
        for widget in self.lowstock_frame.winfo_children():
            widget.destroy()

        low_stock = db.get_low_stock_products()
        if low_stock:
            for product in low_stock:
                row = tk.Frame(self.lowstock_frame, bg=COLORS['white'])
                row.pack(fill='x', pady=3)

                tk.Label(row, text=f"  {product['name']}", font=FONTS['small'],
                         bg=COLORS['white'], fg=COLORS['text_dark'], anchor='w').pack(side='left', fill='x',
                                                                                        expand=True)
                stock_color = COLORS['danger'] if product['stock'] < 5 else COLORS['warning']
                tk.Label(row, text=f"{product['stock']} {product['unit']}", font=FONTS['small_bold'],
                         bg=COLORS['white'], fg=stock_color).pack(side='right')
        else:
            tk.Label(self.lowstock_frame, text="Semua stok aman ✅", font=FONTS['body'],
                     bg=COLORS['white'], fg=COLORS['success']).pack(pady=20)
