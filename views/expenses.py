"""
Expenses View - Halaman pengeluaran
Mencatat pembelian air ke supplier, peralatan rusak, dll
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from styles import COLORS, FONTS, ICONS, format_currency
import database as db


CATEGORY_LABELS = {
    'supplier': '🚰 Beli Air Supplier',
    'peralatan': '🔧 Peralatan Rusak/Beli',
    'upah_kurir': '🚚 Upah Kurir',
    'lainnya': '📎 Lainnya',
}


class ExpensesView(tk.Frame):
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
            header, text=f"{ICONS['expense']}  Pengeluaran",
            font=FONTS['title'], bg=COLORS['bg_light'], fg=COLORS['text_dark']
        ).pack(side='left')

        add_btn = tk.Button(
            header, text=f"  {ICONS['add']}  Tambah Pengeluaran  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self._show_add_dialog, pady=8
        )
        add_btn.pack(side='right')
        add_btn.bind('<Enter>', lambda e: add_btn.config(bg=COLORS['primary_hover']))
        add_btn.bind('<Leave>', lambda e: add_btn.config(bg=COLORS['primary']))

        # Summary cards
        summary = tk.Frame(self, bg=COLORS['bg_light'])
        summary.pack(fill='x', padx=25, pady=(0, 15))
        summary.columnconfigure((0, 1, 2), weight=1)

        self.total_card = tk.Frame(summary, bg=COLORS['white'], padx=20, pady=15,
                                    highlightbackground=COLORS['border_light'], highlightthickness=1)
        self.total_card.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        tk.Label(self.total_card, text="Total Pengeluaran", font=FONTS['small_bold'],
                 bg=COLORS['white'], fg=COLORS['text_light']).pack(anchor='w')
        self.total_expense_label = tk.Label(self.total_card, text="Rp 0", font=FONTS['medium_number'],
                                             bg=COLORS['white'], fg=COLORS['danger'])
        self.total_expense_label.pack(anchor='w')

        self.supplier_card = tk.Frame(summary, bg=COLORS['white'], padx=20, pady=15,
                                       highlightbackground=COLORS['border_light'], highlightthickness=1)
        self.supplier_card.grid(row=0, column=1, sticky='nsew', padx=4)
        tk.Label(self.supplier_card, text="🚰 Supplier", font=FONTS['small_bold'],
                 bg=COLORS['white'], fg=COLORS['text_light']).pack(anchor='w')
        self.supplier_label = tk.Label(self.supplier_card, text="Rp 0", font=FONTS['medium_number'],
                                        bg=COLORS['white'], fg=COLORS['warning'])
        self.supplier_label.pack(anchor='w')

        self.equip_card = tk.Frame(summary, bg=COLORS['white'], padx=20, pady=15,
                                    highlightbackground=COLORS['border_light'], highlightthickness=1)
        self.equip_card.grid(row=0, column=2, sticky='nsew', padx=(8, 0))
        tk.Label(self.equip_card, text="🔧 Peralatan", font=FONTS['small_bold'],
                 bg=COLORS['white'], fg=COLORS['text_light']).pack(anchor='w')
        self.equip_label = tk.Label(self.equip_card, text="Rp 0", font=FONTS['medium_number'],
                                     bg=COLORS['white'], fg=COLORS['info'])
        self.equip_label.pack(anchor='w')

        # Filter
        filter_frame = tk.Frame(self, bg=COLORS['white'], padx=15, pady=10,
                                 highlightbackground=COLORS['border_light'], highlightthickness=1)
        filter_frame.pack(fill='x', padx=25, pady=(0, 15))

        tk.Label(filter_frame, text="Filter:", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(side='left', padx=(0, 10))

        self.cat_filter_var = tk.StringVar(value="all")
        for val, text in [("all", "Semua"), ("supplier", "🚰 Supplier"),
                           ("peralatan", "🔧 Peralatan"), ("lainnya", "📎 Lainnya")]:
            tk.Radiobutton(
                filter_frame, text=text, variable=self.cat_filter_var, value=val,
                font=FONTS['body'], bg=COLORS['white'], activebackground=COLORS['white'],
                selectcolor=COLORS['white'], command=self.refresh_data, cursor='hand2'
            ).pack(side='left', padx=5)

        # Tanggal filter
        tk.Label(filter_frame, text="   Dari:", font=FONTS['body'],
                 bg=COLORS['white'], fg=COLORS['text_medium']).pack(side='left', padx=(15, 5))

        self.date_from_var = tk.StringVar(value=datetime.now().replace(day=1).strftime("%Y-%m-%d"))
        tk.Entry(filter_frame, textvariable=self.date_from_var, font=FONTS['small'],
                 width=12, relief='solid', bd=1).pack(side='left')

        tk.Label(filter_frame, text="  s/d:", font=FONTS['body'],
                 bg=COLORS['white'], fg=COLORS['text_medium']).pack(side='left', padx=5)

        self.date_to_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        tk.Entry(filter_frame, textvariable=self.date_to_var, font=FONTS['small'],
                 width=12, relief='solid', bd=1).pack(side='left')

        filter_btn = tk.Button(
            filter_frame, text=f"  {ICONS['search']}  ", font=('Segoe UI', 12),
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=self.refresh_data, padx=8, pady=2
        )
        filter_btn.pack(side='left', padx=8)

        # ===== Action frame - pack di BOTTOM dulu =====
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
            cursor='hand2', command=self._delete_expense, pady=8, padx=12
        )
        del_btn.pack(side='left')
        del_btn.bind('<Enter>', lambda e: del_btn.config(bg='#B71C1C'))
        del_btn.bind('<Leave>', lambda e: del_btn.config(bg=COLORS['danger']))

        self.count_label = tk.Label(
            action_frame, text="", font=FONTS['small'],
            bg=COLORS['bg_light'], fg=COLORS['text_light']
        )
        self.count_label.pack(side='right')

        # ===== Tabel pengeluaran - pack SETELAH action_frame =====
        table_frame = tk.Frame(self, bg=COLORS['white'],
                                highlightbackground=COLORS['border_light'], highlightthickness=1)
        table_frame.pack(fill='both', expand=True, padx=25, pady=(0, 5))

        style = ttk.Style()
        style.configure('Expenses.Treeview',
                         background=COLORS['white'],
                         foreground=COLORS['text_dark'],
                         fieldbackground=COLORS['white'],
                         font=FONTS['table'],
                         rowheight=38)
        style.configure('Expenses.Treeview.Heading',
                         background=COLORS['primary'],
                         foreground=COLORS['text_white'],
                         font=FONTS['table_header'],
                         relief='flat')
        style.map('Expenses.Treeview.Heading',
                   background=[('active', COLORS['primary_hover'])])

        columns = ('id', 'date', 'category', 'description', 'amount', 'notes')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                  style='Expenses.Treeview', selectmode='browse')

        self.tree.heading('id', text='ID')
        self.tree.heading('date', text='Tanggal')
        self.tree.heading('category', text='Kategori')
        self.tree.heading('description', text='Deskripsi')
        self.tree.heading('amount', text='Jumlah')
        self.tree.heading('notes', text='Catatan')

        self.tree.column('id', width=50, anchor='center')
        self.tree.column('date', width=100, anchor='center')
        self.tree.column('category', width=160, anchor='w')
        self.tree.column('description', width=220, anchor='w')
        self.tree.column('amount', width=130, anchor='e')
        self.tree.column('notes', width=150, anchor='w')

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.tree.bind('<Double-1>', lambda e: self._show_edit_dialog())

    def refresh_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        start = self.date_from_var.get()
        end = self.date_to_var.get()
        cat_filter = self.cat_filter_var.get()

        expenses = db.get_all_expenses(start, end)

        total = 0
        supplier_total = 0
        equip_total = 0
        count = 0

        for exp in expenses:
            # Lewati pengeluaran upah kurir (dikelola di fitur Kurir)
            if exp['category'] == 'upah_kurir':
                continue

            if cat_filter != "all" and exp['category'] != cat_filter:
                continue

            cat_label = CATEGORY_LABELS.get(exp['category'], exp['category'])

            self.tree.insert('', 'end', values=(
                exp['id'], exp['expense_date'], cat_label,
                exp['description'], format_currency(exp['amount']),
                exp['notes'] or '-'
            ))

            total += exp['amount']
            if exp['category'] == 'supplier':
                supplier_total += exp['amount']
            elif exp['category'] == 'peralatan':
                equip_total += exp['amount']
            count += 1

        self.total_expense_label.config(text=format_currency(total))
        self.supplier_label.config(text=format_currency(supplier_total))
        self.equip_label.config(text=format_currency(equip_total))
        self.count_label.config(text=f"Total: {count} pengeluaran")

    def _show_add_dialog(self):
        self._show_expense_dialog("Tambah Pengeluaran")

    def _show_edit_dialog(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih pengeluaran yang ingin diedit!")
            return
        values = self.tree.item(selected[0])['values']
        exp = db.get_expense_by_id(values[0])
        if exp and (exp.get('is_auto') == 1 or exp.get('category') == 'upah_kurir' or exp.get('courier_id')):
            messagebox.showwarning("Peringatan", "Pengeluaran upah kurir dibuat secara otomatis dan tidak boleh diedit!")
            return
        self._show_expense_dialog("Edit Pengeluaran", values)

    def _show_expense_dialog(self, title, values=None):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("480x600")
        dialog.minsize(440, 500)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 240
        y = (dialog.winfo_screenheight() // 2) - 300
        dialog.geometry(f'+{x}+{y}')

        # Header
        tk.Label(dialog, text=title, font=FONTS['subtitle'],
                 bg=COLORS['white'], fg=COLORS['primary_dark']).pack(side='top', pady=(15, 10))

        sep = tk.Frame(dialog, bg=COLORS['accent_light'], height=2)
        sep.pack(side='top', fill='x', padx=30)

        # Tombol aksi - di-pack di BOTTOM terlebih dahulu agar selalu terlihat di layar
        btn_frame = tk.Frame(dialog, bg=COLORS['white'])
        btn_frame.pack(side='bottom', fill='x', padx=30, pady=15)

        # Form isian
        form = tk.Frame(dialog, bg=COLORS['white'], padx=30)
        form.pack(side='top', fill='both', expand=True, pady=10)

        # Kategori
        tk.Label(form, text="Kategori", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(3, 2))

        cat_var = tk.StringVar(value='supplier')
        if values:
            for key, label in CATEGORY_LABELS.items():
                if label == values[2]:
                    cat_var.set(key)
                    break

        cat_frame = tk.Frame(form, bg=COLORS['white'])
        cat_frame.pack(fill='x', pady=(0, 6))
        for val, text in [('supplier', '🚰 Supplier'), ('peralatan', '🔧 Peralatan'), ('lainnya', '📎 Lainnya')]:
            tk.Radiobutton(
                cat_frame, text=text, variable=cat_var, value=val,
                font=FONTS['body'], bg=COLORS['white'], activebackground=COLORS['white'],
                selectcolor=COLORS['white'], cursor='hand2'
            ).pack(side='left', padx=(0, 10))

        # Tanggal
        tk.Label(form, text="Tanggal", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(3, 2))
        date_var = tk.StringVar(value=values[1] if values else date.today().strftime("%Y-%m-%d"))
        date_entry = tk.Entry(form, textvariable=date_var, font=FONTS['input'],
                               relief='solid', bd=1, bg=COLORS['bg_light'])
        date_entry.pack(fill='x', ipady=5)
        date_entry.configure(highlightthickness=1, highlightcolor=COLORS['primary'],
                              highlightbackground=COLORS['border'])

        # Deskripsi
        tk.Label(form, text="Deskripsi", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(6, 2))
        desc_var = tk.StringVar(value=values[3] if values else "")
        tk.Entry(form, textvariable=desc_var, font=FONTS['input'],
                 relief='solid', bd=1, bg=COLORS['bg_light']).pack(fill='x', ipady=5)

        # Jumlah
        tk.Label(form, text="Jumlah (Rp)", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(6, 2))
        amount_str = ""
        if values:
            amount_str = str(values[4]).replace('Rp ', '').replace('.', '').replace(',', '')
        amount_var = tk.StringVar(value=amount_str)
        tk.Entry(form, textvariable=amount_var, font=FONTS['input'],
                 relief='solid', bd=1, bg=COLORS['bg_light']).pack(fill='x', ipady=5)

        # Catatan
        tk.Label(form, text="Catatan (opsional)", font=FONTS['body_bold'],
                 bg=COLORS['white'], fg=COLORS['text_dark']).pack(anchor='w', pady=(6, 2))
        notes_var = tk.StringVar(value=values[5] if values and values[5] != '-' else "")
        tk.Entry(form, textvariable=notes_var, font=FONTS['input'],
                 relief='solid', bd=1, bg=COLORS['bg_light']).pack(fill='x', ipady=5)

        def save():
            try:
                category = cat_var.get()
                expense_date = date_var.get().strip()
                description = desc_var.get().strip()
                amount = float(amount_var.get().replace('.', '').replace(',', ''))
                notes = notes_var.get().strip()

                if not description:
                    messagebox.showwarning("Peringatan", "Deskripsi harus diisi!", parent=dialog)
                    return
                if amount <= 0:
                    messagebox.showwarning("Peringatan", "Jumlah harus lebih dari 0!", parent=dialog)
                    return

                if values:
                    db.update_expense(values[0], category, description, amount, expense_date, notes)
                    messagebox.showinfo("Berhasil", "Pengeluaran berhasil diupdate!", parent=dialog)
                else:
                    db.add_expense(category, description, amount, expense_date, self.user['id'], notes)
                    messagebox.showinfo("Berhasil", "Pengeluaran berhasil ditambahkan!", parent=dialog)

                dialog.destroy()
                self.refresh_data()
            except ValueError:
                messagebox.showerror("Error", "Pastikan jumlah berupa angka yang valid!", parent=dialog)

        save_btn = tk.Button(
            btn_frame, text="  💾  Simpan  ", font=FONTS['button'],
            bg=COLORS['primary'], fg=COLORS['text_white'], relief='flat',
            cursor='hand2', command=save, padx=25, pady=8
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

    def _delete_expense(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih pengeluaran yang ingin dihapus!")
            return

        values = self.tree.item(selected[0])['values']
        exp = db.get_expense_by_id(values[0])
        if exp and (exp.get('is_auto') == 1 or exp.get('category') == 'upah_kurir' or exp.get('courier_id')):
            messagebox.showwarning("Peringatan", "Pengeluaran upah kurir dibuat secara otomatis dan tidak boleh dihapus!")
            return

        if messagebox.askyesno("Konfirmasi", f"Hapus pengeluaran '{values[3]}'?"):
            try:
                db.delete_expense(values[0])
                messagebox.showinfo("Berhasil", "Pengeluaran berhasil dihapus!")
                self.refresh_data()
            except PermissionError as e:
                messagebox.showwarning("Peringatan", str(e))
