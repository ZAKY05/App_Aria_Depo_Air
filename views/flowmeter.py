"""
View Pencatatan Flow Meter Air (Kilometer Air Awal & Akhir Shift)
Depo Air - Digitalisasi Catatan Meteran Air
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta
import os

from styles import COLORS, FONTS, ICONS, format_currency, format_decimal, parse_locale_number
import database as db

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class FlowMeterView(tk.Frame):
    """Tampilan pencatatan flow meter (kilometer air) awal dan akhir shift"""

    def __init__(self, parent, user):
        super().__init__(parent, bg=COLORS['bg_light'])
        self.user = user

        # Filter states
        self.date_from_var = tk.StringVar(value=datetime.now().replace(day=1).strftime("%Y-%m-%d"))
        self.date_to_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.search_var = tk.StringVar()

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        is_owner = self.user.get('role', '') == 'owner'
        if is_owner:
            self._build_owner_ui()
        else:
            self._build_kasir_ui()

    def _build_owner_ui(self):
        # ===== HEADER =====
        header = tk.Frame(self, bg=COLORS['white'], padx=25, pady=18,
                          highlightbackground=COLORS['border_light'], highlightthickness=1)
        header.pack(fill='x')

        title_frame = tk.Frame(header, bg=COLORS['white'])
        title_frame.pack(side='left')

        tk.Label(
            title_frame, text=f"{ICONS.get('flowmeter', '⏱️')}  Pencatatan Flow Meter Air",
            font=FONTS['title'], bg=COLORS['white'], fg=COLORS['primary_dark']
        ).pack(anchor='w')

        is_owner = self.user.get('role', '') == 'owner'

        sub_text = (
            "Catat kilometer awal & akhir shift • Hitung otomatis liter, galon (Bio 21,5L / RO 20,5L), dan omzet air"
            if is_owner else
            "Catat kilometer awal & akhir shift • Hitung otomatis liter dan galon (Bio 21,5L / RO 20,5L)"
        )
        tk.Label(
            title_frame, text=sub_text,
            font=FONTS['small'], bg=COLORS['white'], fg=COLORS['text_medium']
        ).pack(anchor='w', pady=(3, 0))

        # Header Action Buttons
        btn_box = tk.Frame(header, bg=COLORS['white'])
        btn_box.pack(side='right')

        # Tombol Unduh Excel
        excel_btn = tk.Button(
            btn_box, text=f"  💾 Unduh Excel  ", font=FONTS['button'],
            bg=COLORS['success'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._export_to_excel, pady=8, padx=12
        )
        excel_btn.pack(side='left', padx=(0, 8))
        excel_btn.bind('<Enter>', lambda e: excel_btn.config(bg='#256029'))
        excel_btn.bind('<Leave>', lambda e: excel_btn.config(bg=COLORS['success']))

        # Tombol Catat Meteran Baru
        add_btn = tk.Button(
            btn_box, text=f"  {ICONS['add']} Catat Meteran  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._show_add_dialog, pady=8, padx=14
        )
        add_btn.pack(side='left')
        add_btn.bind('<Enter>', lambda e: add_btn.config(bg=COLORS['primary_hover']))
        add_btn.bind('<Leave>', lambda e: add_btn.config(bg=COLORS['primary']))

        # ===== SUMMARY CARDS =====
        summary = tk.Frame(self, bg=COLORS['bg_light'], padx=25, pady=12)
        summary.pack(fill='x')
        summary.columnconfigure((0, 1, 2), weight=1)

        # Card 1: Air Bio Energi
        self.bio_card = tk.Frame(summary, bg=COLORS['white'], padx=18, pady=12,
                                 highlightbackground=COLORS['border_light'], highlightthickness=1)
        self.bio_card.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        self.bio_card_title = tk.Label(self.bio_card, text="🚰 Air Bio Energi", font=FONTS['small_bold'],
                                       bg=COLORS['white'], fg=COLORS['primary'])
        self.bio_card_title.pack(anchor='w')
        self.bio_liters_label = tk.Label(self.bio_card, text="0 Liter", font=FONTS['medium_number'],
                                         bg=COLORS['white'], fg=COLORS['text_dark'])
        self.bio_liters_label.pack(anchor='w', pady=(2, 0))
        self.bio_detail_label = tk.Label(self.bio_card, text="0 Galon • Rp 0" if is_owner else "0 Galon",
                                         font=FONTS['small'], bg=COLORS['white'], fg=COLORS['text_medium'])
        self.bio_detail_label.pack(anchor='w')

        # Card 2: Air RO (Reverse Osmosis)
        self.ro_card = tk.Frame(summary, bg=COLORS['white'], padx=18, pady=12,
                                highlightbackground=COLORS['border_light'], highlightthickness=1)
        self.ro_card.grid(row=0, column=1, sticky='nsew', padx=3)
        self.ro_card_title = tk.Label(self.ro_card, text="💧 Air RO", font=FONTS['small_bold'],
                                      bg=COLORS['white'], fg=COLORS['info'])
        self.ro_card_title.pack(anchor='w')
        self.ro_liters_label = tk.Label(self.ro_card, text="0 Liter", font=FONTS['medium_number'],
                                        bg=COLORS['white'], fg=COLORS['text_dark'])
        self.ro_liters_label.pack(anchor='w', pady=(2, 0))
        self.ro_detail_label = tk.Label(self.ro_card, text="0 Galon • Rp 0" if is_owner else "0 Galon",
                                        font=FONTS['small'], bg=COLORS['white'], fg=COLORS['text_medium'])
        self.ro_detail_label.pack(anchor='w')

        # Card 3: Total
        self.total_card = tk.Frame(summary, bg=COLORS['white'], padx=18, pady=12,
                                   highlightbackground=COLORS['border_light'], highlightthickness=1)
        self.total_card.grid(row=0, column=2, sticky='nsew', padx=(6, 0))
        tot_title = "💰 Total Omzet Fisik Air" if is_owner else "📊 Total Air Keluar"
        tk.Label(self.total_card, text=tot_title, font=FONTS['small_bold'],
                 bg=COLORS['white'], fg=COLORS['success']).pack(anchor='w')
        self.total_rev_label = tk.Label(self.total_card, text="Rp 0" if is_owner else "0 Galon", font=FONTS['medium_number'],
                                        bg=COLORS['white'], fg=COLORS['success'])
        self.total_rev_label.pack(anchor='w', pady=(2, 0))
        self.total_gal_label = tk.Label(self.total_card, text="0 Galon (0 Liter)" if is_owner else "0 Liter", font=FONTS['small'],
                                        bg=COLORS['white'], fg=COLORS['text_medium'])
        self.total_gal_label.pack(anchor='w')

        # ===== FILTER BAR =====
        filter_frame = tk.Frame(self, bg=COLORS['white'], padx=15, pady=8,
                                highlightbackground=COLORS['border_light'], highlightthickness=1)
        filter_frame.pack(fill='x', padx=25, pady=(0, 10))

        tk.Label(filter_frame, text="Filter:", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(side='left', padx=(0, 8))

        # Quick date buttons
        today_str = datetime.now().strftime("%Y-%m-%d")
        month_start_str = datetime.now().replace(day=1).strftime("%Y-%m-%d")

        def set_filter(f_from, f_to):
            self.date_from_var.set(f_from)
            self.date_to_var.set(f_to)
            self.refresh_data()

        tk.Button(
            filter_frame, text="Hari Ini", font=FONTS['small'], bg=COLORS['bg_light'],
            fg=COLORS['text_dark'], relief='flat', cursor='hand2',
            command=lambda: set_filter(today_str, today_str), padx=8, pady=3
        ).pack(side='left', padx=3)

        tk.Button(
            filter_frame, text="Bulan Ini", font=FONTS['small'], bg=COLORS['bg_light'],
            fg=COLORS['text_dark'], relief='flat', cursor='hand2',
            command=lambda: set_filter(month_start_str, today_str), padx=8, pady=3
        ).pack(side='left', padx=3)

        tk.Button(
            filter_frame, text="Semua", font=FONTS['small'], bg=COLORS['bg_light'],
            fg=COLORS['text_dark'], relief='flat', cursor='hand2',
            command=lambda: set_filter("", ""), padx=8, pady=3
        ).pack(side='left', padx=3)

        tk.Label(filter_frame, text="   Dari:", font=FONTS['body'],
                 bg=COLORS['white'], fg=COLORS['text_medium']).pack(side='left', padx=(10, 5))

        tk.Entry(filter_frame, textvariable=self.date_from_var, font=FONTS['small'],
                 width=11, relief='solid', bd=1).pack(side='left')

        tk.Label(filter_frame, text=" s/d:", font=FONTS['body'],
                 bg=COLORS['white'], fg=COLORS['text_medium']).pack(side='left', padx=5)

        tk.Entry(filter_frame, textvariable=self.date_to_var, font=FONTS['small'],
                 width=11, relief='solid', bd=1).pack(side='left')

        tk.Label(filter_frame, text="  Cari:", font=FONTS['body'],
                 bg=COLORS['white'], fg=COLORS['text_medium']).pack(side='left', padx=(15, 5))

        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, font=FONTS['small'],
                                width=16, relief='solid', bd=1)
        search_entry.pack(side='left')
        search_entry.bind('<Return>', lambda e: self.refresh_data())

        filter_btn = tk.Button(
            filter_frame, text=f"  {ICONS['search']} Terapkan  ", font=FONTS['small_bold'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self.refresh_data, padx=10, pady=3
        )
        filter_btn.pack(side='left', padx=8)

        reset_btn = tk.Button(
            filter_frame, text="Reset", font=FONTS['small'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=self._reset_filter, padx=8, pady=3
        )
        reset_btn.pack(side='left')

        # ===== ACTION FRAME BOTTOM (Pack FIRST at bottom to prevent clipping) =====
        action_frame = tk.Frame(self, bg=COLORS['bg_light'], pady=5)
        action_frame.pack(side='bottom', fill='x', padx=25, pady=(5, 12))

        # Edit button
        edit_btn = tk.Button(
            action_frame, text=f"  {ICONS['edit']} Edit Catatan  ", font=FONTS['body_bold'],
            bg=COLORS['primary_light'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._show_edit_dialog, pady=8, padx=12
        )
        edit_btn.pack(side='left', padx=(0, 8))

        # Delete button
        del_btn = tk.Button(
            action_frame, text=f"  {ICONS['delete']} Hapus  ", font=FONTS['body_bold'],
            bg=COLORS['danger'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._delete_record, pady=8, padx=12
        )
        del_btn.pack(side='left', padx=(0, 8))

        self.count_label = tk.Label(
            action_frame, text="", font=FONTS['small'],
            bg=COLORS['bg_light'], fg=COLORS['text_medium']
        )
        self.count_label.pack(side='right')

        # ===== TABLE FRAME =====
        table_frame = tk.Frame(self, bg=COLORS['white'],
                               highlightbackground=COLORS['border_light'], highlightthickness=1)
        table_frame.pack(fill='both', expand=True, padx=25, pady=(0, 5))

        if is_owner:
            columns = (
                'id', 'date', 'shift', 'user',
                'bio_start', 'bio_end', 'bio_liters', 'bio_gallons', 'bio_revenue',
                'ro_start', 'ro_end', 'ro_liters', 'ro_gallons', 'ro_revenue',
                'total_revenue', 'status', 'notes'
            )
        else:
            columns = (
                'id', 'date', 'shift', 'user',
                'bio_start', 'bio_end', 'bio_liters', 'bio_gallons',
                'ro_start', 'ro_end', 'ro_liters', 'ro_gallons',
                'status', 'notes'
            )

        # Style Treeview
        style = ttk.Style()
        style.configure('FlowMeter.Treeview',
                        background=COLORS['white'],
                        foreground=COLORS['text_dark'],
                        fieldbackground=COLORS['white'],
                        font=FONTS['table'],
                        rowheight=30)
        style.configure('FlowMeter.Treeview.Heading',
                        font=FONTS['table_header'])
        style.map('FlowMeter.Treeview',
                  background=[('selected', COLORS['accent_light'])],
                  foreground=[('selected', COLORS['text_dark'])])

        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                style='FlowMeter.Treeview', selectmode='browse')

        # Headings & Column config
        self.tree.heading('id', text='ID')
        self.tree.heading('date', text='Tanggal')
        self.tree.heading('shift', text='Kasir')
        self.tree.heading('user', text='Petugas')
        self.tree.heading('bio_start', text='Bio Awal')
        self.tree.heading('bio_end', text='Bio Akhir')
        self.tree.heading('bio_liters', text='Bio (L)')
        self.tree.heading('bio_gallons', text='Bio (Galon)')
        if is_owner:
            self.tree.heading('bio_revenue', text='Bio (Rp)')
        self.tree.heading('ro_start', text='RO Awal')
        self.tree.heading('ro_end', text='RO Akhir')
        self.tree.heading('ro_liters', text='RO (L)')
        self.tree.heading('ro_gallons', text='RO (Galon)')
        if is_owner:
            self.tree.heading('ro_revenue', text='RO (Rp)')
            self.tree.heading('total_revenue', text='Total Omzet')
        self.tree.heading('status', text='Status')
        self.tree.heading('notes', text='Catatan')

        self.tree.column('id', width=45, minwidth=35, anchor='center')
        self.tree.column('date', width=85, minwidth=75, anchor='center')
        self.tree.column('shift', width=75, minwidth=65, anchor='center')
        self.tree.column('user', width=95, minwidth=80, anchor='w')
        self.tree.column('bio_start', width=75, minwidth=65, anchor='e')
        self.tree.column('bio_end', width=75, minwidth=65, anchor='e')
        self.tree.column('bio_liters', width=70, minwidth=60, anchor='e')
        self.tree.column('bio_gallons', width=75, minwidth=65, anchor='e')
        if is_owner:
            self.tree.column('bio_revenue', width=90, minwidth=80, anchor='e')
        self.tree.column('ro_start', width=75, minwidth=65, anchor='e')
        self.tree.column('ro_end', width=75, minwidth=65, anchor='e')
        self.tree.column('ro_liters', width=70, minwidth=60, anchor='e')
        self.tree.column('ro_gallons', width=75, minwidth=65, anchor='e')
        if is_owner:
            self.tree.column('ro_revenue', width=90, minwidth=80, anchor='e')
            self.tree.column('total_revenue', width=105, minwidth=90, anchor='e')
        self.tree.column('status', width=65, minwidth=55, anchor='center')
        self.tree.column('notes', width=120, minwidth=80, anchor='w')

        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Layout dengan Grid agar Treeview dan kedua Scrollbar tampil sempurna dan tidak tertimpa
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        # Bind mouse wheel untuk scroll horizontal (Shift + Wheel) & trackpad
        self.tree.bind('<Shift-MouseWheel>', lambda e: self.tree.xview_scroll(int(-1 * (e.delta / 120)), 'units'))
        self.tree.bind('<Shift-Button-4>', lambda e: self.tree.xview_scroll(-1, 'units'))
        self.tree.bind('<Shift-Button-5>', lambda e: self.tree.xview_scroll(1, 'units'))

        self.tree.bind('<Double-1>', lambda e: self._show_edit_dialog())

        # Tag styles
        self.tree.tag_configure('open_shift', background='#FFF9C4')  # Kuning lembut untuk shift terbuka

    def _build_kasir_ui(self):
        """Tampilan khusus kasir: formulir pencatatan meteran air tanpa data sensitif / tanpa tabel"""
        # ===== HEADER KASIR =====
        header = tk.Frame(self, bg=COLORS['white'], padx=25, pady=18,
                          highlightbackground=COLORS['border_light'], highlightthickness=1)
        header.pack(fill='x')

        title_frame = tk.Frame(header, bg=COLORS['white'])
        title_frame.pack(side='left')

        tk.Label(
            title_frame, text=f"{ICONS.get('flowmeter', '⏱️')}  Catat Meteran Air",
            font=FONTS['title'], bg=COLORS['white'], fg=COLORS['primary_dark']
        ).pack(anchor='w')

        tk.Label(
            title_frame, text="Pencatatan angka meteran fisik (kilometer air) awal & akhir shift",
            font=FONTS['small'], bg=COLORS['white'], fg=COLORS['text_medium']
        ).pack(anchor='w', pady=(3, 0))

        # Kontainer scrollable untuk formulir agar responsif di segala ukuran layar
        canvas = tk.Canvas(self, bg=COLORS['bg_light'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_light'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind('<Configure>', _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind scroll mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)

        # Kartu Formulir di tengah
        center_container = tk.Frame(scrollable_frame, bg=COLORS['bg_light'], pady=20)
        center_container.pack(fill='both', expand=True)

        card = tk.Frame(center_container, bg=COLORS['white'], padx=32, pady=24,
                        highlightbackground=COLORS['border_light'], highlightthickness=1)
        card.pack(anchor='center', pady=10)

        # --- Row 1: Tanggal, Nama Kasir, Petugas ---
        top_row = tk.Frame(card, bg=COLORS['white'])
        top_row.pack(fill='x', pady=(0, 16))

        # Tanggal
        t_col1 = tk.Frame(top_row, bg=COLORS['white'])
        t_col1.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Label(t_col1, text="Tanggal", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w')
        self.kasir_date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        tk.Entry(t_col1, textvariable=self.kasir_date_var, font=FONTS['input'], relief='solid', bd=1, bg=COLORS['bg_light']).pack(fill='x', ipady=4)

        # Nama Kasir (otomatis mengikuti login dan tidak dapat diubah)
        t_col2 = tk.Frame(top_row, bg=COLORS['white'])
        t_col2.pack(side='left', fill='x', expand=True, padx=3)
        tk.Label(t_col2, text="Nama Kasir", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w')
        self.kasir_shift_var = tk.StringVar(value=self.user.get('full_name', 'Kasir'))
        shift_entry = tk.Entry(t_col2, textvariable=self.kasir_shift_var, font=FONTS['input'],
                               relief='solid', bd=1, bg='#F0F0F0', state='readonly')
        shift_entry.pack(fill='x', ipady=4)

        # Petugas
        t_col3 = tk.Frame(top_row, bg=COLORS['white'])
        t_col3.pack(side='left', fill='x', expand=True, padx=(6, 0))
        tk.Label(t_col3, text="Petugas", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w')
        self.kasir_petugas_var = tk.StringVar(value=self.user.get('full_name', 'Kasir'))
        tk.Entry(t_col3, textvariable=self.kasir_petugas_var, font=FONTS['input'], relief='solid', bd=1, bg=COLORS['bg_light']).pack(fill='x', ipady=4)

        # --- Card 1: Air Bio Energi ---
        bio_box = tk.LabelFrame(card, text="  🚰 Air Bio Energi  ",
                                font=FONTS['body_bold'], fg=COLORS['primary_dark'], bg=COLORS['white'],
                                padx=16, pady=12, bd=1, relief='solid')
        bio_box.pack(fill='x', pady=(0, 16))

        b_row = tk.Frame(bio_box, bg=COLORS['white'])
        b_row.pack(fill='x')

        # Bio Meter Awal
        b_col1 = tk.Frame(b_row, bg=COLORS['white'])
        b_col1.pack(side='left', fill='x', expand=True, padx=(0, 8))
        tk.Label(b_col1, text="Meter Awal (L):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')
        self.kasir_bio_start_var = tk.StringVar(value="0")
        self.kasir_bio_start_entry = tk.Entry(b_col1, textvariable=self.kasir_bio_start_var, font=('Segoe UI', 12, 'bold'),
                                              relief='solid', bd=1, bg='#F0F0F0', state='readonly', justify='right')
        self.kasir_bio_start_entry.pack(fill='x', ipady=4)

        # Bio Meter Akhir
        b_col2 = tk.Frame(b_row, bg=COLORS['white'])
        b_col2.pack(side='left', fill='x', expand=True, padx=(8, 0))
        tk.Label(b_col2, text="Meter Akhir (L):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w')
        self.kasir_bio_end_var = tk.StringVar(value="")
        self.kasir_bio_end_entry = tk.Entry(b_col2, textvariable=self.kasir_bio_end_var, font=('Segoe UI', 12, 'bold'),
                                            relief='solid', bd=1, bg='#E8F5E9', justify='right')
        self.kasir_bio_end_entry.pack(fill='x', ipady=4)

        # --- Card 2: Air RO (Reverse Osmosis) ---
        ro_box = tk.LabelFrame(card, text="  💧 Air RO (Reverse Osmosis)  ",
                               font=FONTS['body_bold'], fg=COLORS['info'], bg=COLORS['white'],
                               padx=16, pady=12, bd=1, relief='solid')
        ro_box.pack(fill='x', pady=(0, 16))

        r_row = tk.Frame(ro_box, bg=COLORS['white'])
        r_row.pack(fill='x')

        # RO Meter Awal
        r_col1 = tk.Frame(r_row, bg=COLORS['white'])
        r_col1.pack(side='left', fill='x', expand=True, padx=(0, 8))
        tk.Label(r_col1, text="Meter Awal (L):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')
        self.kasir_ro_start_var = tk.StringVar(value="0")
        self.kasir_ro_start_entry = tk.Entry(r_col1, textvariable=self.kasir_ro_start_var, font=('Segoe UI', 12, 'bold'),
                                             relief='solid', bd=1, bg='#F0F0F0', state='readonly', justify='right')
        self.kasir_ro_start_entry.pack(fill='x', ipady=4)

        # RO Meter Akhir
        r_col2 = tk.Frame(r_row, bg=COLORS['white'])
        r_col2.pack(side='left', fill='x', expand=True, padx=(8, 0))
        tk.Label(r_col2, text="Meter Akhir (L):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['info']).pack(anchor='w')
        self.kasir_ro_end_var = tk.StringVar(value="")
        self.kasir_ro_end_entry = tk.Entry(r_col2, textvariable=self.kasir_ro_end_var, font=('Segoe UI', 12, 'bold'),
                                           relief='solid', bd=1, bg='#E8F5E9', justify='right')
        self.kasir_ro_end_entry.pack(fill='x', ipady=4)

        # --- Catatan ---
        tk.Label(card, text="Catatan (opsional, misal: cuci filter, bilas galon, dll):",
                 font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(0, 4))
        self.kasir_notes_var = tk.StringVar(value="")
        notes_entry = tk.Entry(card, textvariable=self.kasir_notes_var, font=FONTS['input'],
                               relief='solid', bd=1, bg=COLORS['bg_light'])
        notes_entry.pack(fill='x', ipady=4, pady=(0, 18))

        # Navigasi tombol Enter antar kolom
        self.kasir_bio_end_entry.bind('<Return>', lambda e: self.kasir_ro_end_entry.focus_set())
        self.kasir_ro_end_entry.bind('<Return>', lambda e: notes_entry.focus_set())
        notes_entry.bind('<Return>', lambda e: self._save_kasir_meter())

        # --- Tombol Aksi ---
        btn_frame = tk.Frame(card, bg=COLORS['white'])
        btn_frame.pack(fill='x', pady=(4, 6))

        save_btn = tk.Button(
            btn_frame, text="  💾  Simpan Catatan Meteran  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._save_kasir_meter, padx=22, pady=10
        )
        save_btn.pack(side='left', padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg=COLORS['primary_hover']))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg=COLORS['primary']))

        reset_btn = tk.Button(
            btn_frame, text="  🔄  Reset / Muat Ulang  ", font=FONTS['button'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=self._refresh_kasir_form, padx=16, pady=10
        )
        reset_btn.pack(side='left')

        # Info footer
        footer_frame = tk.Frame(card, bg='#F8F9FA', padx=12, pady=8, highlightbackground=COLORS['border_light'], highlightthickness=1)
        footer_frame.pack(fill='x', pady=(16, 0))
        tk.Label(
            footer_frame,
            text="💡 Tips: Masukkan angka meter akhir dari mesin flow meter sebelum pergantian shift atau saat tutup depo.",
            font=FONTS['small'], bg='#F8F9FA', fg=COLORS['text_medium']
        ).pack(anchor='w')

    def _refresh_kasir_form(self):
        """Segarkan form input kasir dengan pembacaan terbaru"""
        if not hasattr(self, 'kasir_date_var'):
            return

        latest = db.get_latest_water_meter()

        self.kasir_date_var.set(date.today().strftime("%Y-%m-%d"))
        self.kasir_shift_var.set(self.user.get('full_name', 'Kasir'))
        self.kasir_petugas_var.set(self.user.get('full_name', 'Kasir'))

        def_bio = f"{latest['bio_meter_end']:g}" if latest else "0"
        def_ro = f"{latest['ro_meter_end']:g}" if latest else "0"

        self.kasir_bio_start_var.set(def_bio)
        self.kasir_bio_end_var.set("")
        self.kasir_ro_start_var.set(def_ro)
        self.kasir_ro_end_var.set("")
        self.kasir_notes_var.set("")

        # Kunci meter awal jika sudah ada nilainya (> 0 atau catatan sebelumnya ada)
        bio_has_val = (latest is not None and latest.get('bio_meter_end', 0) > 0) or parse_locale_number(def_bio) > 0
        ro_has_val = (latest is not None and latest.get('ro_meter_end', 0) > 0) or parse_locale_number(def_ro) > 0
        self.kasir_bio_start_entry.config(
            state='readonly' if bio_has_val else 'normal',
            bg='#F0F0F0' if bio_has_val else COLORS['bg_light']
        )
        self.kasir_ro_start_entry.config(
            state='readonly' if ro_has_val else 'normal',
            bg='#F0F0F0' if ro_has_val else COLORS['bg_light']
        )
        self.kasir_bio_end_entry.focus_set()

    def _save_kasir_meter(self):
        """Simpan catatan flow meter dari form kasir (tutup shift / akhir shift)"""
        try:
            rec_date = self.kasir_date_var.get().strip()
            # 1. Nama kasir otomatis mengikuti user login dan tidak dapat diubah
            s_name = self.user.get('full_name', 'Kasir')
            u_name = self.kasir_petugas_var.get().strip() or s_name
            notes_text = self.kasir_notes_var.get().strip()

            if not rec_date:
                messagebox.showwarning("Peringatan", "Tanggal harus diisi!")
                return

            b_start_str = self.kasir_bio_start_var.get().strip()
            r_start_str = self.kasir_ro_start_var.get().strip()
            b_end_str = self.kasir_bio_end_var.get().strip()
            r_end_str = self.kasir_ro_end_var.get().strip()

            if not b_start_str or not r_start_str:
                messagebox.showwarning("Peringatan", "Meter awal Bio dan RO harus diisi!")
                return

            if not b_end_str or not r_end_str:
                messagebox.showwarning("Peringatan", "Meter akhir Bio dan RO harus diisi!")
                return

            b_start = parse_locale_number(b_start_str)
            r_start = parse_locale_number(r_start_str)
            b_end = parse_locale_number(b_end_str)
            r_end = parse_locale_number(r_end_str)

            if b_end < b_start:
                if not messagebox.askyesno(
                    "Konfirmasi Angka Meteran",
                    f"Meter akhir Bio ({b_end}) lebih kecil dari meter awal ({b_start}).\nApakah meteran sempat reset/rollover?"
                ):
                    return
            if r_end < r_start:
                if not messagebox.askyesno(
                    "Konfirmasi Angka Meteran",
                    f"Meter akhir RO ({r_end}) lebih kecil dari meter awal ({r_start}).\nApakah meteran sempat reset/rollover?"
                ):
                    return

            # Mengambil harga otomatis tersinkronisasi dari master produk
            synced = db.get_water_prices_from_products()
            cur_bio_price = synced['bio_price']
            cur_ro_price = synced['ro_price']

            latest = db.get_latest_water_meter()
            cur_bio_lpg = latest.get('bio_liters_per_gallon', 21.5) or 21.5 if latest else 21.5
            cur_ro_lpg = latest.get('ro_liters_per_gallon', 20.5) or 20.5 if latest else 20.5

            db.add_water_meter(
                rec_date, s_name, self.user.get('id', 1), u_name,
                b_start, b_end, r_start, r_end,
                bio_lpg=cur_bio_lpg, bio_price=cur_bio_price,
                ro_lpg=cur_ro_lpg, ro_price=cur_ro_price,
                status='closed', notes=notes_text
            )
            messagebox.showinfo("Berhasil", "Catatan flow meter berhasil disimpan!")
            self._refresh_kasir_form()

        except ValueError:
            messagebox.showerror("Error", "Pastikan angka kilometer air berupa angka valid (contoh: 12975.8)!")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan catatan meteran:\n{e}")

            self._refresh_kasir_form()

        except ValueError:
            messagebox.showerror("Error", "Pastikan angka kilometer air berupa angka valid (contoh: 12975.8)!")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan catatan meteran:\n{e}")

    def _reset_filter(self):
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.search_var.set("")
        self.refresh_data()

    def refresh_data(self):
        """Memuat ulang data dari database ke tampilan tabel & kartu ringkasan"""
        is_owner = self.user.get('role', '') == 'owner'
        if not is_owner:
            self._refresh_kasir_form()
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        d_from = self.date_from_var.get().strip() or None
        d_to = self.date_to_var.get().strip() or None
        search = self.search_var.get().strip() or None

        records = db.get_water_meters(d_from, d_to, search)
        summary = db.get_water_meter_summary(d_from, d_to)
        is_owner = self.user.get('role', '') == 'owner'

        # Sinkronisasi label judul harga di kartu KPI
        synced_prices = db.get_water_prices_from_products()
        if hasattr(self, 'bio_card_title'):
            bio_p_text = format_currency(synced_prices['bio_price'])
            self.bio_card_title.config(text=f"🚰 Air Bio Energi ({bio_p_text})" if is_owner else "🚰 Air Bio Energi")
        if hasattr(self, 'ro_card_title'):
            ro_p_text = format_currency(synced_prices['ro_price'])
            self.ro_card_title.config(text=f"💧 Air RO ({ro_p_text})" if is_owner else "💧 Air RO")

        # Update KPI cards
        self.bio_liters_label.config(text=f"{format_decimal(summary['total_bio_liters'], 1)} L")
        if is_owner:
            self.bio_detail_label.config(text=f"{format_decimal(summary['total_bio_gallons'], 1)} Galon • {format_currency(summary['total_bio_revenue'])}")
        else:
            self.bio_detail_label.config(text=f"{format_decimal(summary['total_bio_gallons'], 1)} Galon")

        self.ro_liters_label.config(text=f"{format_decimal(summary['total_ro_liters'], 1)} L")
        if is_owner:
            self.ro_detail_label.config(text=f"{format_decimal(summary['total_ro_gallons'], 1)} Galon • {format_currency(summary['total_ro_revenue'])}")
        else:
            self.ro_detail_label.config(text=f"{format_decimal(summary['total_ro_gallons'], 1)} Galon")

        if is_owner:
            self.total_rev_label.config(text=format_currency(summary['total_revenue']))
            self.total_gal_label.config(text=f"{format_decimal(summary['total_gallons'], 1)} Galon ({format_decimal(summary['total_liters'], 1)} Liter)")
        else:
            self.total_rev_label.config(text=f"{format_decimal(summary['total_gallons'], 1)} Galon")
            self.total_gal_label.config(text=f"{format_decimal(summary['total_liters'], 1)} Liter")

        self.count_label.config(text=f"Menampilkan: {len(records)} catatan flow meter")

        for r in records:
            status_text = "Buka" if r['status'] == 'open' else "Selesai"
            tag = 'open_shift' if r['status'] == 'open' else ''

            if is_owner:
                vals = (
                    r['id'],
                    r['record_date'],
                    r['shift_name'],
                    r['user_name'] or '-',
                    format_decimal(r['bio_meter_start'], 1),
                    format_decimal(r['bio_meter_end'], 1) if r['status'] == 'closed' else '-',
                    format_decimal(r['bio_liters'], 1) if r['status'] == 'closed' else '-',
                    format_decimal(r['bio_gallons'], 2) if r['status'] == 'closed' else '-',
                    format_currency(r['bio_revenue']) if r['status'] == 'closed' else '-',
                    format_decimal(r['ro_meter_start'], 1),
                    format_decimal(r['ro_meter_end'], 1) if r['status'] == 'closed' else '-',
                    format_decimal(r['ro_liters'], 1) if r['status'] == 'closed' else '-',
                    format_decimal(r['ro_gallons'], 2) if r['status'] == 'closed' else '-',
                    format_currency(r['ro_revenue']) if r['status'] == 'closed' else '-',
                    format_currency(r['total_revenue']) if r['status'] == 'closed' else '-',
                    status_text,
                    r['notes'] or '-'
                )
            else:
                vals = (
                    r['id'],
                    r['record_date'],
                    r['shift_name'],
                    r['user_name'] or '-',
                    format_decimal(r['bio_meter_start'], 1),
                    format_decimal(r['bio_meter_end'], 1) if r['status'] == 'closed' else '-',
                    format_decimal(r['bio_liters'], 1) if r['status'] == 'closed' else '-',
                    format_decimal(r['bio_gallons'], 2) if r['status'] == 'closed' else '-',
                    format_decimal(r['ro_meter_start'], 1),
                    format_decimal(r['ro_meter_end'], 1) if r['status'] == 'closed' else '-',
                    format_decimal(r['ro_liters'], 1) if r['status'] == 'closed' else '-',
                    format_decimal(r['ro_gallons'], 2) if r['status'] == 'closed' else '-',
                    status_text,
                    r['notes'] or '-'
                )

            self.tree.insert('', 'end', values=vals, tags=(tag,) if tag else ())

    # ==================== DIALOG INPUT & EDIT ====================

    def _show_add_dialog(self):
        """Dialog untuk mencatat meteran baru"""
        self._open_meter_form_dialog("Catat Flow Meter Air Baru")

    def _show_edit_dialog(self):
        """Dialog untuk mengedit catatan meteran yang dipilih"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih baris meteran yang ingin diedit!")
            return
        meter_id = self.tree.item(selected[0])['values'][0]
        rec = db.get_water_meter_by_id(meter_id)
        if not rec:
            messagebox.showerror("Error", "Data tidak ditemukan!")
            return
        self._open_meter_form_dialog(f"Edit Flow Meter (ID: {meter_id})", existing_data=rec)

    def _open_meter_form_dialog(self, title, existing_data=None):
        """Dialog formulir pengisian flow meter dengan kalkulasi live"""
        is_owner = self.user.get('role', '') == 'owner'

        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog_h = 680 if is_owner else 490
        dialog.geometry(f"540x{dialog_h}")
        dialog.minsize(480, 420)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 270
        y = (dialog.winfo_screenheight() // 2) - (dialog_h // 2)
        dialog.geometry(f'+{x}+{y}')

        # Header
        tk.Label(dialog, text=title, font=FONTS['subtitle'],
                 bg=COLORS['white'], fg=COLORS['primary_dark']).pack(side='top', pady=(15, 6))

        sep = tk.Frame(dialog, bg=COLORS['accent_light'], height=2)
        sep.pack(side='top', fill='x', padx=25)

        # Tombol aksi di-pack di BOTTOM terlebih dahulu agar selalu terlihat
        btn_frame = tk.Frame(dialog, bg=COLORS['white'])
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=15)

        # Body form dalam scrollable / pack container
        form = tk.Frame(dialog, bg=COLORS['white'], padx=25)
        form.pack(side='top', fill='both', expand=True, pady=10)

        # Nilai awal / default
        latest = db.get_latest_water_meter()

        # Ambil daftar nama kasir dari database
        all_users = db.get_all_users()
        kasir_names = [u['full_name'] for u in all_users if u['role'] == 'kasir' and u['is_active']]

        def_date = existing_data['record_date'] if existing_data else date.today().strftime("%Y-%m-%d")
        def_shift = existing_data['shift_name'] if existing_data else (kasir_names[0] if (kasir_names and is_owner) else self.user.get('full_name', 'Kasir'))
        if not is_owner:
            def_shift = self.user.get('full_name', 'Kasir')
        def_user = existing_data['user_name'] if existing_data else self.user.get('full_name', 'Kasir')

        def_bio_start = f"{existing_data['bio_meter_start']:g}" if existing_data else (f"{latest['bio_meter_end']:g}" if latest else "0")
        def_bio_end = f"{existing_data['bio_meter_end']:g}" if existing_data and existing_data['bio_meter_end'] > 0 else ""

        def_ro_start = f"{existing_data['ro_meter_start']:g}" if existing_data else (f"{latest['ro_meter_end']:g}" if latest else "0")
        def_ro_end = f"{existing_data['ro_meter_end']:g}" if existing_data and existing_data['ro_meter_end'] > 0 else ""

        def_notes = existing_data['notes'] if existing_data else ""
        def_status = existing_data['status'] if existing_data else "closed"

        # --- Row 1: Tanggal, Shift, Petugas ---
        top_row = tk.Frame(form, bg=COLORS['white'])
        top_row.pack(fill='x', pady=(0, 10))

        # Tanggal
        t_col1 = tk.Frame(top_row, bg=COLORS['white'])
        t_col1.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Label(t_col1, text="Tanggal", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w')
        date_var = tk.StringVar(value=def_date)
        tk.Entry(t_col1, textvariable=date_var, font=FONTS['input'], relief='solid', bd=1, bg=COLORS['bg_light']).pack(fill='x', ipady=4)

        # Nama Kasir (menggantikan Shift)
        t_col2 = tk.Frame(top_row, bg=COLORS['white'])
        t_col2.pack(side='left', fill='x', expand=True, padx=3)
        tk.Label(t_col2, text="Nama Kasir", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w')
        shift_var = tk.StringVar(value=def_shift)
        if is_owner:
            shift_combo = ttk.Combobox(t_col2, textvariable=shift_var, font=FONTS['input'],
                                       values=kasir_names)
            shift_combo.pack(fill='x', ipady=3)
        else:
            shift_entry = tk.Entry(t_col2, textvariable=shift_var, font=FONTS['input'],
                                   relief='solid', bd=1, bg='#F0F0F0', state='readonly')
            shift_entry.pack(fill='x', ipady=4)

        # Petugas
        t_col3 = tk.Frame(top_row, bg=COLORS['white'])
        t_col3.pack(side='left', fill='x', expand=True, padx=(6, 0))
        tk.Label(t_col3, text="Petugas", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w')
        user_var = tk.StringVar(value=def_user)
        tk.Entry(t_col3, textvariable=user_var, font=FONTS['input'], relief='solid', bd=1, bg=COLORS['bg_light']).pack(fill='x', ipady=4)

        # --- Card 1: Air Bio Energi ---
        bio_box = tk.LabelFrame(form, text="  🚰 Air Bio Energi  ",
                                font=FONTS['body_bold'], fg=COLORS['primary_dark'], bg=COLORS['white'],
                                padx=12, pady=8, bd=1, relief='solid')
        bio_box.pack(fill='x', pady=(0, 10))

        # Ambil harga air tersinkronisasi dari produk
        synced_prices = db.get_water_prices_from_products()

        # Row harga & liter per galon Bio (Hanya untuk Owner)
        if is_owner:
            bio_config_row = tk.Frame(bio_box, bg=COLORS['white'])
            bio_config_row.pack(fill='x', pady=(0, 6))

            bc_col1 = tk.Frame(bio_config_row, bg=COLORS['white'])
            bc_col1.pack(side='left', fill='x', expand=True, padx=(0, 6))
            tk.Label(bc_col1, text="Liter per Galon:", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')
            def_bio_lpg = f"{existing_data['bio_liters_per_gallon']:g}" if existing_data and existing_data.get('bio_liters_per_gallon') else "21.5"
            bio_lpg_var = tk.StringVar(value=def_bio_lpg)
            bio_lpg_entry = tk.Entry(bc_col1, textvariable=bio_lpg_var, font=FONTS['input'],
                                     relief='solid', bd=1, bg=COLORS['bg_light'], justify='right')
            bio_lpg_entry.pack(fill='x', ipady=3)

            bc_col2 = tk.Frame(bio_config_row, bg=COLORS['white'])
            bc_col2.pack(side='left', fill='x', expand=True, padx=(6, 0))
            tk.Label(bc_col2, text="Harga per Galon (Rp):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')
            def_bio_price = f"{existing_data['bio_price_per_gallon']:g}" if existing_data and existing_data.get('bio_price_per_gallon') else f"{synced_prices['bio_price']:g}"
            bio_price_var = tk.StringVar(value=def_bio_price)
            bio_price_entry = tk.Entry(bc_col2, textvariable=bio_price_var, font=FONTS['input'],
                                       relief='solid', bd=1, bg=COLORS['bg_light'], justify='right')
            bio_price_entry.pack(fill='x', ipady=3)
            tk.Label(bc_col2, text=f"⚡ Sinkron Produk: {format_currency(synced_prices['bio_price'])}", font=FONTS['small'], bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w')
        else:
            def_bio_lpg = f"{existing_data['bio_liters_per_gallon']:g}" if existing_data and existing_data.get('bio_liters_per_gallon') else "21.5"
            bio_lpg_var = tk.StringVar(value=def_bio_lpg)
            def_bio_price = f"{existing_data['bio_price_per_gallon']:g}" if existing_data and existing_data.get('bio_price_per_gallon') else f"{synced_prices['bio_price']:g}"
            bio_price_var = tk.StringVar(value=def_bio_price)

        b_row = tk.Frame(bio_box, bg=COLORS['white'])
        b_row.pack(fill='x')

        # Bio Meter Awal
        b_col1 = tk.Frame(b_row, bg=COLORS['white'])
        b_col1.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Label(b_col1, text="Meter Awal (L):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')
        bio_start_var = tk.StringVar(value=def_bio_start)
        bio_has_val = parse_locale_number(def_bio_start) > 0 or (latest is not None and latest.get('bio_meter_end', 0) > 0)
        bio_start_entry = tk.Entry(b_col1, textvariable=bio_start_var, font=('Segoe UI', 12, 'bold'),
                                   relief='solid', bd=1,
                                   bg='#F0F0F0' if bio_has_val else COLORS['bg_light'],
                                   state='readonly' if bio_has_val else 'normal',
                                   justify='right')
        bio_start_entry.pack(fill='x', ipady=4)
        if is_owner and bio_has_val:
            bio_start_entry.bind('<Double-Button-1>', lambda e: bio_start_entry.config(state='normal', bg=COLORS['bg_light']))

        # Bio Meter Akhir
        b_col2 = tk.Frame(b_row, bg=COLORS['white'])
        b_col2.pack(side='left', fill='x', expand=True, padx=(6, 0))
        tk.Label(b_col2, text="Meter Akhir (L):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['primary']).pack(anchor='w')
        bio_end_var = tk.StringVar(value=def_bio_end)
        bio_end_entry = tk.Entry(b_col2, textvariable=bio_end_var, font=('Segoe UI', 12, 'bold'),
                                 relief='solid', bd=1, bg='#E8F5E9', justify='right')
        bio_end_entry.pack(fill='x', ipady=4)

        # Bio Live Feedback (Hanya untuk Owner)
        if is_owner:
            bio_calc_label = tk.Label(bio_box, text="Liter Keluar: 0 L  •  Galon: 0 galon  •  Omzet: Rp 0",
                                      font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['primary'])
            bio_calc_label.pack(anchor='w', pady=(6, 0))

        # --- Card 2: Air RO (Reverse Osmosis) ---
        ro_box = tk.LabelFrame(form, text="  💧 Air RO (Reverse Osmosis)  ",
                               font=FONTS['body_bold'], fg=COLORS['info'], bg=COLORS['white'],
                               padx=12, pady=8, bd=1, relief='solid')
        ro_box.pack(fill='x', pady=(0, 10))

        # Row harga & liter per galon RO (Hanya untuk Owner)
        if is_owner:
            ro_config_row = tk.Frame(ro_box, bg=COLORS['white'])
            ro_config_row.pack(fill='x', pady=(0, 6))

            rc_col1 = tk.Frame(ro_config_row, bg=COLORS['white'])
            rc_col1.pack(side='left', fill='x', expand=True, padx=(0, 6))
            tk.Label(rc_col1, text="Liter per Galon:", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')
            def_ro_lpg = f"{existing_data['ro_liters_per_gallon']:g}" if existing_data and existing_data.get('ro_liters_per_gallon') else "20.5"
            ro_lpg_var = tk.StringVar(value=def_ro_lpg)
            ro_lpg_entry = tk.Entry(rc_col1, textvariable=ro_lpg_var, font=FONTS['input'],
                                    relief='solid', bd=1, bg=COLORS['bg_light'], justify='right')
            ro_lpg_entry.pack(fill='x', ipady=3)

            rc_col2 = tk.Frame(ro_config_row, bg=COLORS['white'])
            rc_col2.pack(side='left', fill='x', expand=True, padx=(6, 0))
            tk.Label(rc_col2, text="Harga per Galon (Rp):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')
            def_ro_price = f"{existing_data['ro_price_per_gallon']:g}" if existing_data and existing_data.get('ro_price_per_gallon') else f"{synced_prices['ro_price']:g}"
            ro_price_var = tk.StringVar(value=def_ro_price)
            ro_price_entry = tk.Entry(rc_col2, textvariable=ro_price_var, font=FONTS['input'],
                                      relief='solid', bd=1, bg=COLORS['bg_light'], justify='right')
            ro_price_entry.pack(fill='x', ipady=3)
            tk.Label(rc_col2, text=f"⚡ Sinkron Produk: {format_currency(synced_prices['ro_price'])}", font=FONTS['small'], bg=COLORS['white'], fg=COLORS['info']).pack(anchor='w')
        else:
            def_ro_lpg = f"{existing_data['ro_liters_per_gallon']:g}" if existing_data and existing_data.get('ro_liters_per_gallon') else "20.5"
            ro_lpg_var = tk.StringVar(value=def_ro_lpg)
            def_ro_price = f"{existing_data['ro_price_per_gallon']:g}" if existing_data and existing_data.get('ro_price_per_gallon') else f"{synced_prices['ro_price']:g}"
            ro_price_var = tk.StringVar(value=def_ro_price)

        r_row = tk.Frame(ro_box, bg=COLORS['white'])
        r_row.pack(fill='x')

        # RO Meter Awal
        r_col1 = tk.Frame(r_row, bg=COLORS['white'])
        r_col1.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Label(r_col1, text="Meter Awal (L):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_medium']).pack(anchor='w')
        ro_start_var = tk.StringVar(value=def_ro_start)
        ro_has_val = parse_locale_number(def_ro_start) > 0 or (latest is not None and latest.get('ro_meter_end', 0) > 0)
        ro_start_entry = tk.Entry(r_col1, textvariable=ro_start_var, font=('Segoe UI', 12, 'bold'),
                                  relief='solid', bd=1,
                                  bg='#F0F0F0' if ro_has_val else COLORS['bg_light'],
                                  state='readonly' if ro_has_val else 'normal',
                                  justify='right')
        ro_start_entry.pack(fill='x', ipady=4)
        if is_owner and ro_has_val:
            ro_start_entry.bind('<Double-Button-1>', lambda e: ro_start_entry.config(state='normal', bg=COLORS['bg_light']))

        # RO Meter Akhir
        r_col2 = tk.Frame(r_row, bg=COLORS['white'])
        r_col2.pack(side='left', fill='x', expand=True, padx=(6, 0))
        tk.Label(r_col2, text="Meter Akhir (L):", font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['info']).pack(anchor='w')
        ro_end_var = tk.StringVar(value=def_ro_end)
        ro_end_entry = tk.Entry(r_col2, textvariable=ro_end_var, font=('Segoe UI', 12, 'bold'),
                                relief='solid', bd=1, bg='#E8F5E9', justify='right')
        ro_end_entry.pack(fill='x', ipady=4)

        # RO Live Feedback (Hanya untuk Owner)
        if is_owner:
            ro_calc_label = tk.Label(ro_box, text="Liter Keluar: 0 L  •  Galon: 0 galon  •  Omzet: Rp 0",
                                     font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['info'])
            ro_calc_label.pack(anchor='w', pady=(6, 0))

        # --- Card 3: Ringkasan Total Real-Time (Hanya untuk Owner) ---
        if is_owner:
            sum_box = tk.Frame(form, bg=COLORS['info_bg'], padx=12, pady=8,
                               highlightbackground=COLORS['border_light'], highlightthickness=1)
            sum_box.pack(fill='x', pady=(0, 10))

            tk.Label(sum_box, text="📊 Total Gabungan Real-Time:", font=FONTS['small_bold'],
                     bg=COLORS['info_bg'], fg=COLORS['primary_dark']).pack(anchor='w')
            total_live_label = tk.Label(sum_box, text="Total: 0 Liter  •  0 Galon  •  Omzet: Rp 0",
                                        font=FONTS['body_bold'], bg=COLORS['info_bg'], fg=COLORS['success'])
            total_live_label.pack(anchor='w', pady=(2, 0))

        # --- Catatan ---
        tk.Label(form, text="Catatan (opsional, misal: cuci filter, bilas galon, dll):",
                 font=FONTS['small_bold'], bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(0, 2))
        notes_var = tk.StringVar(value=def_notes)
        notes_entry = tk.Entry(form, textvariable=notes_var, font=FONTS['input'],
                               relief='solid', bd=1, bg=COLORS['bg_light'])
        notes_entry.pack(fill='x', ipady=4)

        # Live calculation callback (hanya aktif untuk owner)
        def recalculate(*args):
            if not is_owner:
                return
            try:
                b_start = parse_locale_number(bio_start_var.get())
                b_end = parse_locale_number(bio_end_var.get()) if bio_end_var.get().strip() else b_start
                r_start = parse_locale_number(ro_start_var.get())
                r_end = parse_locale_number(ro_end_var.get()) if ro_end_var.get().strip() else r_start

                cur_bio_lpg = parse_locale_number(bio_lpg_var.get()) if bio_lpg_var.get().strip() else 21.5
                cur_bio_price = parse_locale_number(bio_price_var.get()) if bio_price_var.get().strip() else synced_prices['bio_price']
                cur_ro_lpg = parse_locale_number(ro_lpg_var.get()) if ro_lpg_var.get().strip() else 20.5
                cur_ro_price = parse_locale_number(ro_price_var.get()) if ro_price_var.get().strip() else synced_prices['ro_price']

                b_liters = max(0.0, round(b_end - b_start, 2)) if bio_end_var.get().strip() else 0.0
                b_gal = round(b_liters / cur_bio_lpg, 2) if cur_bio_lpg > 0 else 0.0
                b_rev = round(b_gal * cur_bio_price)

                r_liters = max(0.0, round(r_end - r_start, 2)) if ro_end_var.get().strip() else 0.0
                r_gal = round(r_liters / cur_ro_lpg, 2) if cur_ro_lpg > 0 else 0.0
                r_rev = round(r_gal * cur_ro_price)

                tot_liters = round(b_liters + r_liters, 2)
                tot_gal = round(b_gal + r_gal, 2)
                tot_rev = b_rev + r_rev

                bio_calc_label.config(
                    text=f"Liter Keluar: {format_decimal(b_liters, 1)} L  •  {format_decimal(b_gal, 2)} Galon  •  {format_currency(b_rev)}"
                )
                ro_calc_label.config(
                    text=f"Liter Keluar: {format_decimal(r_liters, 1)} L  •  {format_decimal(r_gal, 2)} Galon  •  {format_currency(r_rev)}"
                )
                total_live_label.config(
                    text=f"Total: {format_decimal(tot_liters, 1)} Liter  •  {format_decimal(tot_gal, 2)} Galon  •  {format_currency(tot_rev)}"
                )
            except (ValueError, Exception):
                pass

        if is_owner:
            bio_start_var.trace_add('write', recalculate)
            bio_end_var.trace_add('write', recalculate)
            ro_start_var.trace_add('write', recalculate)
            ro_end_var.trace_add('write', recalculate)
            bio_lpg_var.trace_add('write', recalculate)
            bio_price_var.trace_add('write', recalculate)
            ro_lpg_var.trace_add('write', recalculate)
            ro_price_var.trace_add('write', recalculate)
            recalculate()

        # Fokus input
        if (existing_data and existing_data['status'] == 'open') or bio_has_val:
            bio_end_entry.focus_set()
        else:
            bio_start_entry.focus_set()

        # Save Handler
        def save():
            try:
                rec_date = date_var.get().strip()
                s_name = self.user.get('full_name', 'Kasir') if not is_owner else (shift_var.get().strip() or self.user.get('full_name', 'Kasir'))
                u_name = user_var.get().strip() or s_name
                notes_text = notes_var.get().strip()

                if not rec_date:
                    messagebox.showwarning("Peringatan", "Tanggal harus diisi!", parent=dialog)
                    return

                b_start = parse_locale_number(bio_start_var.get())
                r_start = parse_locale_number(ro_start_var.get())

                # Parse editable lpg & price values
                cur_bio_lpg = parse_locale_number(bio_lpg_var.get()) if bio_lpg_var.get().strip() else 21.5
                cur_bio_price = parse_locale_number(bio_price_var.get()) if bio_price_var.get().strip() else synced_prices['bio_price']
                cur_ro_lpg = parse_locale_number(ro_lpg_var.get()) if ro_lpg_var.get().strip() else 20.5
                cur_ro_price = parse_locale_number(ro_price_var.get()) if ro_price_var.get().strip() else synced_prices['ro_price']

                has_end = bool(bio_end_var.get().strip() and ro_end_var.get().strip())
                status = 'closed' if has_end else 'open'

                b_end = parse_locale_number(bio_end_var.get()) if bio_end_var.get().strip() else b_start
                r_end = parse_locale_number(ro_end_var.get()) if ro_end_var.get().strip() else r_start

                if has_end:
                    if b_end < b_start:
                        if not messagebox.askyesno(
                            "Konfirmasi Angka Meteran",
                            f"Meter akhir Bio ({b_end}) lebih kecil dari meter awal ({b_start}).\nApakah meteran sempat reset/rollover?",
                            parent=dialog
                        ):
                            return
                    if r_end < r_start:
                        if not messagebox.askyesno(
                            "Konfirmasi Angka Meteran",
                            f"Meter akhir RO ({r_end}) lebih kecil dari meter awal ({r_start}).\nApakah meteran sempat reset/rollover?",
                            parent=dialog
                        ):
                            return

                if existing_data:
                    db.update_water_meter(
                        existing_data['id'], rec_date, s_name, u_name,
                        b_start, b_end, r_start, r_end,
                        bio_lpg=cur_bio_lpg, bio_price=cur_bio_price, ro_lpg=cur_ro_lpg, ro_price=cur_ro_price,
                        status=status, notes=notes_text
                    )
                    messagebox.showinfo("Berhasil", "Data flow meter berhasil diperbarui!", parent=dialog)
                else:
                    db.add_water_meter(
                        rec_date, s_name, self.user.get('id', 1), u_name,
                        b_start, b_end, r_start, r_end,
                        bio_lpg=cur_bio_lpg, bio_price=cur_bio_price, ro_lpg=cur_ro_lpg, ro_price=cur_ro_price,
                        status=status, notes=notes_text
                    )
                    messagebox.showinfo("Berhasil", "Catatan flow meter berhasil disimpan!", parent=dialog)

                dialog.destroy()
                self.refresh_data()

            except ValueError:
                messagebox.showerror("Error", "Pastikan angka kilometer air berupa angka valid (contoh: 12975.8)!", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan:\n{e}", parent=dialog)

        # Action buttons
        save_btn = tk.Button(
            btn_frame, text="  💾  Simpan Catatan  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=save, padx=22, pady=9
        )
        save_btn.pack(side='left', padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg=COLORS['primary_hover']))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg=COLORS['primary']))

        cancel_btn = tk.Button(
            btn_frame, text="  Batal  ", font=FONTS['button'],
            bg=COLORS['border'], fg=COLORS['text_dark'], relief='flat',
            cursor='hand2', command=dialog.destroy, padx=20, pady=9
        )
        cancel_btn.pack(side='left')

    def _delete_record(self):
        """Hapus catatan meteran yang dipilih"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih baris meteran yang ingin dihapus!")
            return

        values = self.tree.item(selected[0])['values']
        meter_id = values[0]
        rec_date = values[1]
        shift = values[2]

        if messagebox.askyesno("Konfirmasi Hapus", f"Apakah Anda yakin ingin menghapus catatan meteran:\nTanggal: {rec_date} ({shift})?"):
            db.delete_water_meter(meter_id)
            messagebox.showinfo("Berhasil", "Catatan flow meter berhasil dihapus!")
            self.refresh_data()

    # ==================== EKSPOR EXCEL ====================

    def _export_to_excel(self):
        """Ekspor data flow meter ke file Excel (.xlsx) dengan format rapi persis seperti sheet user"""
        if not HAS_OPENPYXL:
            messagebox.showerror("Error", "Library openpyxl belum terinstal di sistem!")
            return

        d_from = self.date_from_var.get().strip() or None
        d_to = self.date_to_var.get().strip() or None
        search = self.search_var.get().strip() or None
        is_owner = self.user.get('role', '') == 'owner'

        records = db.get_water_meters(d_from, d_to, search, limit=1000)
        if not records:
            messagebox.showinfo("Info", "Tidak ada data flow meter untuk diunduh.")
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Unduh Catatan Flow Meter ke Excel",
            defaultextension=".xlsx",
            initialfile=f"Catatan_Flow_Meter_Air_{datetime.now().strftime('%Y%m%d')}.xlsx",
            filetypes=[("Excel Workbook (*.xlsx)", "*.xlsx"), ("All Files (*.*)", "*.*")]
        )
        if not file_path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Flow Meter Air"

            # Title block
            ws.append(["LAPORAN PENCATATAN FLOW METER AIR - DEPO AIR"])
            ws.append([f"Periode: {d_from or 'Semua'} s/d {d_to or 'Hari ini'}  |  Diunduh: {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
            ws.append([])

            if is_owner:
                row4 = ["No", "Tanggal", "Shift", "Petugas",
                        "Flow Meter Bio", "", "", "", "",
                        "Flow Meter RO", "", "", "", "",
                        "Total Gabungan", "", "", "Catatan"]
                row5 = ["", "", "", "",
                        "Awal (L)", "Akhir (L)", "Liter Air", "Galon (21,5L)", "Omzet Bio (Rp)",
                        "Awal (L)", "Akhir (L)", "Liter Air", "Galon (20,5L)", "Omzet RO (Rp)",
                        "Total Liter", "Total Galon", "Total Omzet (Rp)", ""]
                num_cols = 18
            else:
                row4 = ["No", "Tanggal", "Shift", "Petugas",
                        "Flow Meter Bio", "", "", "",
                        "Flow Meter RO", "", "", "",
                        "Total Gabungan", "", "Catatan"]
                row5 = ["", "", "", "",
                        "Awal (L)", "Akhir (L)", "Liter Air", "Galon (21,5L)",
                        "Awal (L)", "Akhir (L)", "Liter Air", "Galon (20,5L)",
                        "Total Liter", "Total Galon", ""]
                num_cols = 15

            ws.append(row4)
            ws.append(row5)

            # Styling Headers
            header_fill_blue = PatternFill(start_color="1565C0", end_color="1565C0", fill_type="solid")
            header_fill_bio = PatternFill(start_color="1976D2", end_color="1976D2", fill_type="solid")
            header_fill_ro = PatternFill(start_color="0288D1", end_color="0288D1", fill_type="solid")
            header_fill_tot = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
            header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style='thin', color="CCCCCC"),
                right=Side(style='thin', color="CCCCCC"),
                top=Side(style='thin', color="CCCCCC"),
                bottom=Side(style='thin', color="CCCCCC")
            )

            # Apply fill & font to header rows
            for c_idx in range(1, num_cols + 1):
                cell1 = ws.cell(row=4, column=c_idx)
                cell2 = ws.cell(row=5, column=c_idx)
                cell1.font = header_font
                cell2.font = header_font
                cell1.alignment = Alignment(horizontal='center', vertical='center')
                cell2.alignment = Alignment(horizontal='center', vertical='center')

                if is_owner:
                    if c_idx <= 4 or c_idx == 18:
                        cell1.fill = header_fill_blue
                        cell2.fill = header_fill_blue
                    elif 5 <= c_idx <= 9:
                        cell1.fill = header_fill_bio
                        cell2.fill = header_fill_bio
                    elif 10 <= c_idx <= 14:
                        cell1.fill = header_fill_ro
                        cell2.fill = header_fill_ro
                    else:
                        cell1.fill = header_fill_tot
                        cell2.fill = header_fill_tot
                else:
                    if c_idx <= 4 or c_idx == 15:
                        cell1.fill = header_fill_blue
                        cell2.fill = header_fill_blue
                    elif 5 <= c_idx <= 8:
                        cell1.fill = header_fill_bio
                        cell2.fill = header_fill_bio
                    elif 9 <= c_idx <= 12:
                        cell1.fill = header_fill_ro
                        cell2.fill = header_fill_ro
                    else:
                        cell1.fill = header_fill_tot
                        cell2.fill = header_fill_tot

            # Merge grouped headers
            ws.merge_cells('A4:A5')
            ws.merge_cells('B4:B5')
            ws.merge_cells('C4:C5')
            ws.merge_cells('D4:D5')
            if is_owner:
                ws.merge_cells('E4:I4')
                ws.merge_cells('J4:N4')
                ws.merge_cells('O4:Q4')
                ws.merge_cells('R4:R5')
            else:
                ws.merge_cells('E4:H4')
                ws.merge_cells('I4:L4')
                ws.merge_cells('M4:N4')
                ws.merge_cells('O4:O5')

            # Populate data
            tot_b_lit = 0
            tot_b_gal = 0
            tot_b_rev = 0
            tot_r_lit = 0
            tot_r_gal = 0
            tot_r_rev = 0
            tot_all_lit = 0
            tot_all_gal = 0
            tot_all_rev = 0

            for i, r in enumerate(reversed(records), 1):
                tot_b_lit += r['bio_liters']
                tot_b_gal += r['bio_gallons']
                tot_b_rev += r['bio_revenue']
                tot_r_lit += r['ro_liters']
                tot_r_gal += r['ro_gallons']
                tot_r_rev += r['ro_revenue']
                tot_all_lit += r['total_liters']
                tot_all_gal += r['total_gallons']
                tot_all_rev += r['total_revenue']

                if is_owner:
                    row_data = [
                        i,
                        r['record_date'],
                        r['shift_name'],
                        r['user_name'] or '-',
                        r['bio_meter_start'],
                        r['bio_meter_end'],
                        r['bio_liters'],
                        r['bio_gallons'],
                        r['bio_revenue'],
                        r['ro_meter_start'],
                        r['ro_meter_end'],
                        r['ro_liters'],
                        r['ro_gallons'],
                        r['ro_revenue'],
                        r['total_liters'],
                        r['total_gallons'],
                        r['total_revenue'],
                        r['notes'] or '-'
                    ]
                else:
                    row_data = [
                        i,
                        r['record_date'],
                        r['shift_name'],
                        r['user_name'] or '-',
                        r['bio_meter_start'],
                        r['bio_meter_end'],
                        r['bio_liters'],
                        r['bio_gallons'],
                        r['ro_meter_start'],
                        r['ro_meter_end'],
                        r['ro_liters'],
                        r['ro_gallons'],
                        r['total_liters'],
                        r['total_gallons'],
                        r['notes'] or '-'
                    ]

                ws.append(row_data)

                curr_row = ws.max_row
                for col in range(1, num_cols + 1):
                    c = ws.cell(row=curr_row, column=col)
                    c.border = thin_border
                    c.font = Font(name="Segoe UI", size=10)
                    if col in [1, 2, 3]:
                        c.alignment = Alignment(horizontal='center')
                    elif col < num_cols:
                        c.alignment = Alignment(horizontal='right')
                        if is_owner and col in [9, 14, 17]:
                            c.number_format = '#,##0'
                        else:
                            c.number_format = '#,##0.0'

            # Row TOTAL
            ws.append([])
            if is_owner:
                tot_row_data = [
                    "", "TOTAL", "", "",
                    "", "", tot_b_lit, tot_b_gal, tot_b_rev,
                    "", "", tot_r_lit, tot_r_gal, tot_r_rev,
                    tot_all_lit, tot_all_gal, tot_all_rev, ""
                ]
            else:
                tot_row_data = [
                    "", "TOTAL", "", "",
                    "", "", tot_b_lit, tot_b_gal,
                    "", "", tot_r_lit, tot_r_gal,
                    tot_all_lit, tot_all_gal, ""
                ]
            ws.append(tot_row_data)

            tot_row_idx = ws.max_row
            tot_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
            for col in range(1, num_cols + 1):
                c = ws.cell(row=tot_row_idx, column=col)
                c.font = Font(name="Segoe UI", size=11, bold=True)
                c.fill = tot_fill
                c.border = thin_border
                if is_owner and col in [9, 14, 17]:
                    c.number_format = '#,##0'
                elif (is_owner and col in [7, 8, 12, 13, 15, 16]) or (not is_owner and col in [7, 8, 11, 12, 13, 14]):
                    c.number_format = '#,##0.0'

            # Auto fit column widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 11)

            wb.save(file_path)
            messagebox.showinfo("Berhasil", f"Catatan flow meter berhasil diunduh ke:\n{file_path}", parent=self)

        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengekspor file Excel:\n{e}", parent=self)
