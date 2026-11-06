"""
Database module untuk Aplikasi Kasir Depo Air
Mengelola semua operasi database SQLite
"""

import sqlite3
import hashlib
import os
import sys
from datetime import datetime, timedelta


def _get_app_dir():
    """Mendapatkan direktori aplikasi (kompatibel PyInstaller .exe)"""
    if getattr(sys, 'frozen', False):
        # Jika dijalankan sebagai .exe (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Jika dijalankan sebagai script Python biasa
        return os.path.dirname(os.path.abspath(__file__))


DB_NAME = os.environ.get("DEPO_DB_NAME", "depo_air.db")
DB_PATH = os.path.join(_get_app_dir(), DB_NAME)


def set_db_name(name):
    """Mengubah target file database (misal: 'depo_air_test.db')"""
    global DB_NAME, DB_PATH
    DB_NAME = name
    DB_PATH = os.path.join(_get_app_dir(), DB_NAME)


def get_connection():
    """Mendapatkan koneksi database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password):
    """Hash password dengan SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def init_database():
    """Inisialisasi database dan tabel-tabel"""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabel Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('owner', 'kasir')),
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabel Products
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Galon',
            buy_price REAL DEFAULT 0,
            sell_price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            unit TEXT DEFAULT 'pcs',
            courier_fee_per_unit INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabel Customers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            debt_amount REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabel Couriers (Master Data Kurir)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            phone TEXT DEFAULT '',
            payment_type TEXT NOT NULL DEFAULT 'dikumpulkan' CHECK(payment_type IN ('langsung', 'dikumpulkan')),
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabel Transactions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            user_id INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            discount REAL DEFAULT 0,
            total REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            change_amount REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'cash' CHECK(payment_method IN ('cash', 'hutang')),
            status TEXT DEFAULT 'completed' CHECK(status IN ('completed', 'pending', 'cancelled', 'batal')),
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivery_fee REAL DEFAULT 0,
            is_delivery INTEGER DEFAULT 0,
            courier_name TEXT DEFAULT '',
            courier_id INTEGER,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id)
        )
    """)

    # Tabel Transaction Items
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Tabel Expenses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL CHECK(category IN ('supplier', 'peralatan', 'upah_kurir', 'lainnya')),
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date DATE NOT NULL,
            user_id INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            courier_id INTEGER,
            payment_date TIMESTAMP,
            is_auto INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id)
        )
    """)

    # Tabel Courier Payments (Riwayat Pembayaran Upah Kurir)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courier_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            courier_id INTEGER NOT NULL,
            total INTEGER NOT NULL,
            paid_at TIMESTAMP NOT NULL,
            paid_by INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            expense_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (courier_id) REFERENCES couriers(id),
            FOREIGN KEY (paid_by) REFERENCES users(id),
            FOREIGN KEY (expense_id) REFERENCES expenses(id)
        )
    """)

    # Tabel Courier Wages (Pencatatan Upah Kurir)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courier_wages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wage_date DATE NOT NULL,
            courier_id INTEGER NOT NULL,
            transaction_id INTEGER,
            amount INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'belum_dibayar' CHECK(status IN ('belum_dibayar', 'sudah_dibayar')),
            payment_id INTEGER,
            paid_at TIMESTAMP,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (courier_id) REFERENCES couriers(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id),
            FOREIGN KEY (payment_id) REFERENCES courier_payments(id)
        )
    """)

    # Tabel Debt Payments (Pembayaran Hutang)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Tabel Water Meters (Pencatatan Kilometer Air / Flow Meter)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS water_meters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_date DATE NOT NULL,
            shift_name TEXT NOT NULL DEFAULT 'Harian',
            user_id INTEGER,
            user_name TEXT DEFAULT '',
            bio_meter_start REAL NOT NULL DEFAULT 0,
            bio_meter_end REAL NOT NULL DEFAULT 0,
            bio_liters REAL NOT NULL DEFAULT 0,
            bio_liters_per_gallon REAL NOT NULL DEFAULT 21.5,
            bio_gallons REAL NOT NULL DEFAULT 0,
            bio_price_per_gallon REAL NOT NULL DEFAULT 5000,
            bio_revenue REAL NOT NULL DEFAULT 0,
            ro_meter_start REAL NOT NULL DEFAULT 0,
            ro_meter_end REAL NOT NULL DEFAULT 0,
            ro_liters REAL NOT NULL DEFAULT 0,
            ro_liters_per_gallon REAL NOT NULL DEFAULT 20.5,
            ro_gallons REAL NOT NULL DEFAULT 0,
            ro_price_per_gallon REAL NOT NULL DEFAULT 10000,
            ro_revenue REAL NOT NULL DEFAULT 0,
            total_liters REAL NOT NULL DEFAULT 0,
            total_gallons REAL NOT NULL DEFAULT 0,
            total_revenue REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'closed' CHECK(status IN ('open', 'closed')),
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Migrasi kolom tambahan products & transactions
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN courier_fee_per_unit INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN courier_id INTEGER")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN delivery_fee REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN is_delivery INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN courier_name TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE couriers ADD COLUMN is_deleted INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_deleted INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Migrasi CHECK pada tabel expenses (Syarat 7)
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='expenses'")
    exp_sql = cursor.fetchone()
    if exp_sql and 'upah_kurir' not in exp_sql[0]:
        cursor.execute("""
            CREATE TABLE expenses_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL CHECK(category IN ('supplier', 'peralatan', 'upah_kurir', 'lainnya')),
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                expense_date DATE NOT NULL,
                user_id INTEGER NOT NULL,
                notes TEXT DEFAULT '',
                courier_id INTEGER,
                payment_date TIMESTAMP,
                is_auto INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (courier_id) REFERENCES couriers(id)
            )
        """)
        cursor.execute("""
            INSERT INTO expenses_new (id, category, description, amount, expense_date, user_id, notes, courier_id, payment_date, is_auto, created_at)
            SELECT id, category, description, amount, expense_date, user_id, notes, courier_id, payment_date, is_auto, created_at
            FROM expenses
        """)
        cursor.execute("DROP TABLE expenses")
        cursor.execute("ALTER TABLE expenses_new RENAME TO expenses")

    # Migrasi tabel courier_wages ke status belum_dibayar/sudah_dibayar dan payment_id (Syarat 1 & 3)
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='courier_wages'")
    cw_sql = cursor.fetchone()
    if cw_sql and ('pending' in cw_sql[0] or 'payment_id' not in cw_sql[0]):
        cursor.execute("""
            CREATE TABLE courier_wages_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wage_date DATE NOT NULL,
                courier_id INTEGER NOT NULL,
                transaction_id INTEGER,
                amount INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'belum_dibayar' CHECK(status IN ('belum_dibayar', 'sudah_dibayar')),
                payment_id INTEGER,
                paid_at TIMESTAMP,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (courier_id) REFERENCES couriers(id),
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (payment_id) REFERENCES courier_payments(id)
            )
        """)
        cursor.execute("PRAGMA table_info(courier_wages)")
        cw_cols = [c[1] for c in cursor.fetchall()]
        has_cw_payment_id = 'payment_id' in cw_cols
        cursor.execute(f"""
            INSERT INTO courier_wages_new (id, wage_date, courier_id, transaction_id, amount, status, payment_id, paid_at, notes, created_at)
            SELECT id, wage_date, courier_id, transaction_id, amount,
                   CASE
                       WHEN status IN ('settled', 'collected', 'sudah_dibayar') THEN 'sudah_dibayar'
                       ELSE 'belum_dibayar'
                   END,
                   {'payment_id' if has_cw_payment_id else 'NULL'},
                   paid_at, notes, created_at
            FROM courier_wages
        """)
        cursor.execute("DROP TABLE courier_wages")
        cursor.execute("ALTER TABLE courier_wages_new RENAME TO courier_wages")

    # Migrasi kolom password_plain pada tabel users
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [c[1] for c in cursor.fetchall()]
    if 'password_plain' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password_plain TEXT")
        # Populate password_plain untuk user awal / eksisting jika cocok
        cursor.execute("UPDATE users SET password_plain = 'owner123' WHERE username = 'owner' AND (password_plain IS NULL OR password_plain = '')")
        cursor.execute("UPDATE users SET password_plain = 'kasir123' WHERE username = 'kasir' AND (password_plain IS NULL OR password_plain = '')")
        cursor.execute("UPDATE users SET password_plain = 'siti123' WHERE username = 'sitikasir' AND (password_plain IS NULL OR password_plain = '')")

    # Drop tabel lama delivery_fees dan courier_settlements (Syarat 4)
    cursor.execute("DROP TABLE IF EXISTS delivery_fees")
    cursor.execute("DROP TABLE IF EXISTS courier_settlements")

    # Insert default owner jika belum ada
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password_hash, password_plain, full_name, role) VALUES (?, ?, ?, ?, ?)",
            ("owner", hash_password("owner123"), "owner123", "Pemilik Depo", "owner")
        )

    conn.commit()
    conn.close()


# ==================== USER OPERATIONS ====================

def authenticate_user(username, password):
    """Autentikasi user, mengembalikan dict user atau None"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_active = 1 AND (is_deleted IS NULL OR is_deleted = 0)",
        (username, hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None


def get_all_users(role=None):
    """Mengambil semua user, opsional filter berdasarkan role"""
    conn = get_connection()
    cursor = conn.cursor()
    if role:
        cursor.execute("SELECT * FROM users WHERE role = ? AND (is_deleted IS NULL OR is_deleted = 0) ORDER BY full_name", (role,))
    else:
        cursor.execute("SELECT * FROM users WHERE (is_deleted IS NULL OR is_deleted = 0) ORDER BY role, full_name")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def get_user_by_id(user_id):
    """Mengambil user berdasarkan ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def add_user(username, password, full_name, role='kasir'):
    """Menambah user baru (registrasi kasir)"""
    conn = get_connection()
    cursor = conn.cursor()
    # Cek username unik (yang aktif / tidak terhapus)
    cursor.execute("SELECT id FROM users WHERE username = ? AND (is_deleted IS NULL OR is_deleted = 0)", (username,))
    if cursor.fetchone():
        conn.close()
        return None, "Username sudah digunakan!"
    cursor.execute(
        "INSERT INTO users (username, password_hash, password_plain, full_name, role) VALUES (?, ?, ?, ?, ?)",
        (username, hash_password(password), password, full_name, role)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id, "Berhasil"


def update_user(user_id, full_name, username):
    """Update data user"""
    conn = get_connection()
    cursor = conn.cursor()
    # Cek username unik (selain dirinya sendiri dan tidak terhapus)
    cursor.execute("SELECT id FROM users WHERE username = ? AND id != ? AND (is_deleted IS NULL OR is_deleted = 0)", (username, user_id))
    if cursor.fetchone():
        conn.close()
        return False, "Username sudah digunakan!"
    cursor.execute(
        "UPDATE users SET full_name = ?, username = ? WHERE id = ?",
        (full_name, username, user_id)
    )
    conn.commit()
    conn.close()
    return True, "Berhasil"


def update_user_password(user_id, new_password):
    """Update password user"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ?, password_plain = ? WHERE id = ?",
        (hash_password(new_password), new_password, user_id)
    )
    conn.commit()
    conn.close()


def toggle_user_active(user_id):
    """Aktifkan/nonaktifkan user"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        new_status = 0 if row['is_active'] else 1
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
    conn.close()


def delete_user(user_id):
    """
    Hapus user/kasir:
    - Jika user belum pernah memiliki riwayat transaksi, pengeluaran, pembayaran upah kurir, pembayaran hutang, atau flow meter,
      hapus permanen dari tabel users.
    - Jika sudah pernah ada riwayat transaksi/aktivitas, lakukan soft delete (is_active = 0, is_deleted = 1)
      serta ubah username agar username aslinya dapat dipakai kembali dan integritas database tetap terjaga.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,))
        trx_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,))
        exp_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM courier_payments WHERE paid_by = ?", (user_id,))
        cp_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM debt_payments WHERE user_id = ?", (user_id,))
        dp_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM water_meters WHERE user_id = ?", (user_id,))
        wm_count = cursor.fetchone()[0]

        total_activity = trx_count + exp_count + cp_count + dp_count + wm_count
        if total_activity == 0:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        else:
            cursor.execute("""
                UPDATE users
                SET is_active = 0,
                    is_deleted = 1,
                    username = username || '_del_' || id
                WHERE id = ?
            """, (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ==================== PRODUCT OPERATIONS ====================

def get_all_products(active_only=True):
    """Mengambil semua produk"""
    conn = get_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY name")
    else:
        cursor.execute("SELECT * FROM products ORDER BY name")
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return products


def get_product_by_id(product_id):
    """Mengambil produk berdasarkan ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    return dict(product) if product else None


def add_product(name, category, buy_price, sell_price, stock, unit, courier_fee_per_unit=0):
    """Menambah produk baru"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, category, buy_price, sell_price, stock, unit, courier_fee_per_unit) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, category, buy_price, sell_price, stock, unit, int(round(courier_fee_per_unit or 0)))
    )
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return product_id


def update_product(product_id, name, category, buy_price, sell_price, stock, unit, courier_fee_per_unit=0):
    """Update produk"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE products SET name=?, category=?, buy_price=?, sell_price=?, stock=?, unit=?,
           courier_fee_per_unit=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (name, category, buy_price, sell_price, stock, unit, int(round(courier_fee_per_unit or 0)), product_id)
    )
    conn.commit()
    conn.close()


def delete_product(product_id):
    """Soft delete produk"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


def update_stock(product_id, quantity_change):
    """Update stok produk (positif = tambah, negatif = kurang)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE products SET stock = stock + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (quantity_change, product_id)
    )
    conn.commit()
    conn.close()


# ==================== CUSTOMER OPERATIONS ====================

def get_all_customers(active_only=True):
    """Mengambil semua pelanggan"""
    conn = get_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM customers WHERE is_active = 1 ORDER BY name")
    else:
        cursor.execute("SELECT * FROM customers ORDER BY name")
    customers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return customers


def get_customer_by_id(customer_id):
    """Mengambil pelanggan berdasarkan ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    customer = cursor.fetchone()
    conn.close()
    return dict(customer) if customer else None


def add_customer(name, phone, address):
    """Menambah pelanggan baru"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)",
        (name, phone, address)
    )
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    return customer_id


def update_customer(customer_id, name, phone, address):
    """Update pelanggan"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE customers SET name=?, phone=?, address=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (name, phone, address, customer_id)
    )
    conn.commit()
    conn.close()


def delete_customer(customer_id):
    """Soft delete pelanggan"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE customers SET is_active = 0 WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()


def update_customer_debt(customer_id, amount_change, conn=None):
    """Update hutang pelanggan (positif = tambah hutang, negatif = bayar hutang)"""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE customers SET debt_amount = MAX(0, debt_amount + ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (amount_change, customer_id)
    )
    if should_close:
        conn.commit()
        conn.close()


def add_debt_payment(customer_id, amount, user_id, notes=""):
    """Catat pembayaran hutang"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """INSERT INTO debt_payments (customer_id, amount, payment_date, user_id, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (customer_id, amount, now_str, user_id, notes, now_str)
        )
        cursor.execute(
            "UPDATE customers SET debt_amount = MAX(0, debt_amount - ?), updated_at = ? WHERE id = ?",
            (amount, now_str, customer_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_debt_payments(customer_id):
    """Mengambil riwayat pembayaran hutang pelanggan"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT dp.*, u.full_name as user_name
           FROM debt_payments dp
           JOIN users u ON dp.user_id = u.id
           WHERE dp.customer_id = ?
           ORDER BY dp.created_at DESC, dp.id DESC""",
        (customer_id,)
    )
    payments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return payments


# ==================== TRANSACTION OPERATIONS ====================

def generate_invoice_number():
    """Generate nomor invoice unik"""
    now = datetime.now()
    prefix = now.strftime("INV%Y%m%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE invoice_number LIKE ?",
        (f"{prefix}%",)
    )
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"{prefix}{count:04d}"


def create_transaction(customer_id, user_id, items, payment_method, paid_amount, discount=0, notes="",
                       is_delivery=False, courier_name="", delivery_fee=0, courier_id=None):
    """
    Buat transaksi baru secara atomik.
    items: list of dict {'product_id', 'quantity', 'unit_price'}
    is_delivery: True jika pesanan diantar
    courier_id: ID kurir pengantar (wajib jika is_delivery=True)
    courier_name: nama kurir pengantar (opsional jika courier_id ada)
    delivery_fee: biaya antar pelanggan (belum final, default 0, tidak menambah total belanja pelanggan)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION")

        courier = None
        if is_delivery:
            if courier_id:
                cursor.execute("SELECT * FROM couriers WHERE id = ? AND is_active = 1", (courier_id,))
                courier = cursor.fetchone()
            elif courier_name:
                cursor.execute("SELECT * FROM couriers WHERE name = ? AND is_active = 1", (courier_name,))
                courier = cursor.fetchone()

            if not courier:
                raise ValueError("Kurir wajib dipilih untuk pesanan antar!")

            courier_id = courier['id']
            courier_name = courier['name']

        invoice = generate_invoice_number()
        subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
        # Syarat 11: Bagian ongkos antar yang dibayar pelanggan BELUM final. Jangan ubah total transaksi pelanggan.
        actual_delivery_fee = 0
        total = max(0, subtotal - discount)
        change_amount = max(0, paid_amount - total) if payment_method == 'cash' else 0

        cursor.execute(
            """INSERT INTO transactions
               (invoice_number, customer_id, user_id, subtotal, discount, total,
                paid_amount, change_amount, payment_method, status, notes,
                delivery_fee, is_delivery, courier_name, courier_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?)""",
            (invoice, customer_id, user_id, subtotal, discount, total,
             paid_amount, change_amount, payment_method, notes,
             actual_delivery_fee, 1 if is_delivery else 0, courier_name if is_delivery else '',
             courier_id if is_delivery else None)
        )
        transaction_id = cursor.lastrowid

        total_courier_wage = 0
        for item in items:
            cursor.execute("SELECT name, stock, courier_fee_per_unit FROM products WHERE id = ?", (item['product_id'],))
            product = cursor.fetchone()
            if not product:
                raise ValueError(f"Produk ID {item['product_id']} tidak ditemukan!")
            if product['stock'] < item['quantity']:
                raise ValueError(f"Stok untuk {product['name']} tidak mencukupi (tersedia {product['stock']}, diminta {item['quantity']})")

            fee_per_unit = product['courier_fee_per_unit'] or 0
            total_courier_wage += item['quantity'] * fee_per_unit

            cursor.execute(
                """INSERT INTO transaction_items
                   (transaction_id, product_id, product_name, quantity, unit_price, subtotal)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (transaction_id, item['product_id'], product['name'],
                 item['quantity'], item['unit_price'],
                 item['quantity'] * item['unit_price'])
            )

            # Kurangi stok
            cursor.execute(
                "UPDATE products SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (item['quantity'], item['product_id'])
            )

        # Jika hutang, tambahkan ke hutang pelanggan (upah kurir tetap tercatat)
        if payment_method == 'hutang' and customer_id:
            cursor.execute(
                "UPDATE customers SET debt_amount = debt_amount + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (total, customer_id)
            )

        # Catat upah kurir jika pesanan diantar
        if is_delivery and courier:
            now_dt = datetime.now()
            today_str = now_dt.strftime("%Y-%m-%d")
            now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

            if courier['payment_type'] == 'langsung':
                wage_status = 'sudah_dibayar'
                paid_at = now_str

                # Syarat 6: Pengeluaran 'upah_kurir' memuat nomor invoice, is_auto=1, courier_id
                expense_desc = f"Upah Kurir Langsung - {courier['name']} (Invoice #{invoice})"
                cursor.execute("""
                    INSERT INTO expenses
                    (category, description, amount, expense_date, user_id, notes, courier_id, payment_date, is_auto)
                    VALUES ('upah_kurir', ?, ?, ?, ?, ?, ?, ?, 1)
                """, (expense_desc, total_courier_wage, today_str, user_id,
                      f"Otomatis dari transaksi #{invoice}", courier_id, now_str))
                expense_id = cursor.lastrowid

                # Catat ke courier_payments (Syarat 1)
                cursor.execute("""
                    INSERT INTO courier_payments
                    (courier_id, total, paid_at, paid_by, notes, expense_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (courier_id, total_courier_wage, now_str, user_id,
                      f"Pembayaran langsung transaksi #{invoice}", expense_id))
                payment_id = cursor.lastrowid
            else:
                wage_status = 'belum_dibayar'
                paid_at = None
                payment_id = None

            cursor.execute(
                """INSERT INTO courier_wages
                   (wage_date, courier_id, transaction_id, amount, status, payment_id, paid_at, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (today_str, courier_id, transaction_id, total_courier_wage, wage_status,
                 payment_id, paid_at, f"Upah transaksi #{invoice}")
            )

        conn.commit()
        return transaction_id, invoice
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def cancel_transaction(transaction_id, user_role='owner'):
    """
    Batalkan transaksi (Syarat 5):
    - Status transaksi diubah menjadi 'batal'.
    - Stok barang dikembalikan.
    - Jika hutang, kurangi hutang pelanggan.
    - Upah kurir milik transaksi batal otomatis dikecualikan dari saldo.
    - Bila upahnya sudah dibayar, tampilkan peringatan ke Owner.
    - Jangan pakai ON DELETE CASCADE.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        trx = cursor.fetchone()
        if not trx:
            raise ValueError("Transaksi tidak ditemukan")
        if trx['status'] == 'batal':
            raise ValueError("Transaksi sudah dalam status batal")

        # Cek upah kurir
        cursor.execute("""
            SELECT cw.*, c.name as courier_name 
            FROM courier_wages cw 
            JOIN couriers c ON cw.courier_id = c.id 
            WHERE cw.transaction_id = ?
        """, (transaction_id,))
        wage = cursor.fetchone()

        warning = None
        if wage and wage['status'] == 'sudah_dibayar':
            warning = f"PERINGATAN: Upah kurir sebesar Rp {int(round(wage['amount'])):,} untuk {wage['courier_name']} sudah dibayar pada {wage['paid_at'] or '-'}. Harap sesuaikan pengeluaran kas secara manual."

        # Ubah status transaksi menjadi 'batal'
        cursor.execute("UPDATE transactions SET status = 'batal' WHERE id = ?", (transaction_id,))

        # Kembalikan stok produk
        cursor.execute("SELECT product_id, quantity FROM transaction_items WHERE transaction_id = ?", (transaction_id,))
        items = cursor.fetchall()
        for item in items:
            cursor.execute("UPDATE products SET stock = stock + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item['quantity'], item['product_id']))

        # Jika hutang, kurangi hutang pelanggan
        if trx['payment_method'] == 'hutang' and trx['customer_id']:
            cursor.execute("UPDATE customers SET debt_amount = MAX(0, debt_amount - ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?", (trx['total'], trx['customer_id']))

        conn.commit()
        return True, warning
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_transactions(start_date=None, end_date=None, limit=100):
    """Mengambil daftar transaksi"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT t.*, u.full_name as kasir_name,
               COALESCE(c.name, 'Umum') as customer_name
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN customers c ON t.customer_id = c.id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND DATE(t.created_at) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND DATE(t.created_at) <= ?"
        params.append(end_date)

    query += " ORDER BY t.created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transactions


def get_transaction_items(transaction_id):
    """Mengambil item-item transaksi"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM transaction_items WHERE transaction_id = ?",
        (transaction_id,)
    )
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def get_transaction_by_invoice(invoice_number):
    """Mengambil transaksi berdasarkan nomor invoice beserta items"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT t.*, u.full_name as kasir_name,
                  COALESCE(c.name, 'Umum') as customer_name
           FROM transactions t
           JOIN users u ON t.user_id = u.id
           LEFT JOIN customers c ON t.customer_id = c.id
           WHERE t.invoice_number = ?""",
        (invoice_number,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    trx = dict(row)
    cursor.execute("SELECT * FROM transaction_items WHERE transaction_id = ?", (trx['id'],))
    trx['items'] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return trx


# ==================== EXPENSE OPERATIONS ====================

def get_expense_by_id(expense_id):
    """Mengambil detail pengeluaran berdasarkan ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_expenses(start_date=None, end_date=None):
    """Mengambil semua pengeluaran"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT e.*, u.full_name as user_name
        FROM expenses e
        JOIN users u ON e.user_id = u.id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND e.expense_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND e.expense_date <= ?"
        params.append(end_date)

    query += " ORDER BY e.expense_date DESC, e.created_at DESC"
    cursor.execute(query, params)
    expenses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return expenses


def add_expense(category, description, amount, expense_date, user_id, notes="", courier_id=None, is_auto=0, payment_date=None):
    """Menambah pengeluaran"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO expenses (category, description, amount, expense_date, user_id, notes, courier_id, is_auto, payment_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (category, description, amount, expense_date, user_id, notes, courier_id, is_auto, payment_date)
    )
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()
    return expense_id


def update_expense(expense_id, category, description, amount, expense_date, notes=""):
    """Update pengeluaran"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_auto, category FROM expenses WHERE id = ?", (expense_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Pengeluaran tidak ditemukan")
    if row['is_auto'] == 1 or row['category'] == 'upah_kurir':
        conn.close()
        raise PermissionError("Pengeluaran upah kurir otomatis tidak boleh diedit!")

    cursor.execute(
        "UPDATE expenses SET category=?, description=?, amount=?, expense_date=?, notes=? WHERE id=?",
        (category, description, amount, expense_date, notes, expense_id)
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id):
    """Hapus pengeluaran"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_auto, category FROM expenses WHERE id = ?", (expense_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Pengeluaran tidak ditemukan")
    if row['is_auto'] == 1 or row['category'] == 'upah_kurir':
        conn.close()
        raise PermissionError("Pengeluaran upah kurir otomatis tidak boleh dihapus!")

    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


# ==================== REPORT / DASHBOARD OPERATIONS ====================

def get_dashboard_stats():
    """Mengambil statistik untuk dashboard"""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    # Penjualan hari ini
    cursor.execute(
        "SELECT COALESCE(SUM(total), 0) FROM transactions WHERE DATE(created_at) = ? AND status = 'completed'",
        (today,)
    )
    today_sales = cursor.fetchone()[0]

    # Jumlah transaksi hari ini
    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE DATE(created_at) = ? AND status = 'completed'",
        (today,)
    )
    today_transactions = cursor.fetchone()[0]

    # Total hutang pelanggan
    cursor.execute("SELECT COALESCE(SUM(debt_amount), 0) FROM customers WHERE is_active = 1")
    total_debt = cursor.fetchone()[0]

    # Pengeluaran hari ini
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_date = ?",
        (today,)
    )
    today_expenses = cursor.fetchone()[0]

    # Total produk
    cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
    total_products = cursor.fetchone()[0]

    # Total pelanggan
    cursor.execute("SELECT COUNT(*) FROM customers WHERE is_active = 1")
    total_customers = cursor.fetchone()[0]

    # Penjualan bulan ini
    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COALESCE(SUM(total), 0) FROM transactions WHERE DATE(created_at) >= ? AND status = 'completed'",
        (month_start,)
    )
    month_sales = cursor.fetchone()[0]

    # Pengeluaran bulan ini
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_date >= ?",
        (month_start,)
    )
    month_expenses = cursor.fetchone()[0]

    # Stok rendah (< 10)
    cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1 AND stock < 10")
    low_stock_count = cursor.fetchone()[0]

    conn.close()

    return {
        'today_sales': today_sales,
        'today_transactions': today_transactions,
        'total_debt': total_debt,
        'today_expenses': today_expenses,
        'total_products': total_products,
        'total_customers': total_customers,
        'month_sales': month_sales,
        'month_expenses': month_expenses,
        'low_stock_count': low_stock_count,
    }


def is_water_refill_product(product_name, category=''):
    """Cek apakah produk merupakan air isi ulang (Bio / RO)"""
    if category and category.lower() == 'isi ulang':
        return True
    if not product_name:
        return False
    name = product_name.lower().strip()
    if 'isi ulang' in name or 'bio' in name or 'osmosis' in name:
        return True
    import re
    if re.search(r'\bro\b', name) or '(ro)' in name:
        return True
    return False


def get_sales_report(period='daily', start_date=None, end_date=None):
    """
    Mengambil laporan keuangan berdasarkan periode:
    - Omzet air (Bio & RO) dari flow meter
    - Penjualan barang non-air dari POS
    - Hutang baru dari transaksi POS metode 'hutang'
    - Pelunasan hutang dari debt_payments
    - Uang Masuk = Total Penjualan - Hutang Baru + Pelunasan Hutang
    - Selisih Kas = Uang Masuk - Total Pengeluaran
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()

    if not start_date:
        if period == 'daily':
            start_date = now.strftime("%Y-%m-%d")
            end_date = start_date
        elif period == 'weekly':
            start_date = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
        elif period == 'monthly':
            start_date = now.replace(day=1).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
        elif period == 'yearly':
            start_date = now.replace(month=1, day=1).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")

    # 1. Omzet air dari Flow Meter (water_meters) per tanggal
    cursor.execute("""
        SELECT 
            record_date,
            COALESCE(SUM(bio_revenue), 0) as bio_revenue,
            COALESCE(SUM(ro_revenue), 0) as ro_revenue,
            COALESCE(SUM(total_revenue), 0) as total_revenue
        FROM water_meters
        WHERE record_date BETWEEN ? AND ?
        GROUP BY record_date
        ORDER BY record_date DESC
    """, (start_date, end_date))
    water_rows = {
        row['record_date']: {
            'bio_revenue': int(round(row['bio_revenue'])),
            'ro_revenue': int(round(row['ro_revenue'])),
            'total_revenue': int(round(row['total_revenue'])),
        } for row in cursor.fetchall()
    }

    # 2. Penjualan barang selain isi ulang dari POS
    cursor.execute("""
        SELECT 
            DATE(t.created_at) as trx_date,
            ti.product_name,
            ti.subtotal,
            COALESCE(p.category, '') as category
        FROM transaction_items ti
        JOIN transactions t ON ti.transaction_id = t.id
        LEFT JOIN products p ON ti.product_id = p.id
        WHERE DATE(t.created_at) BETWEEN ? AND ? AND t.status = 'completed'
    """, (start_date, end_date))
    pos_items = cursor.fetchall()

    pos_other_by_date = {}
    for itm in pos_items:
        if not is_water_refill_product(itm['product_name'], itm['category']):
            d = itm['trx_date']
            pos_other_by_date[d] = pos_other_by_date.get(d, 0) + int(round(itm['subtotal']))

    # 3. Gabungkan data per tanggal untuk Tabel Pemasukan
    all_dates = set(water_rows.keys()) | set(pos_other_by_date.keys())
    if period == 'daily' and start_date:
        all_dates.add(start_date)

    daily_income = []
    total_bio_revenue = 0
    total_ro_revenue = 0
    total_other_sales = 0

    for d in sorted(all_dates, reverse=True):
        w = water_rows.get(d, {'bio_revenue': 0, 'ro_revenue': 0, 'total_revenue': 0})
        b = w['bio_revenue']
        r = w['ro_revenue']
        oth = pos_other_by_date.get(d, 0)
        tot = b + r + oth
        daily_income.append({
            'date': d,
            'bio_revenue': b,
            'ro_revenue': r,
            'other_sales': oth,
            'total': tot
        })
        total_bio_revenue += b
        total_ro_revenue += r
        total_other_sales += oth

    total_water_revenue = total_bio_revenue + total_ro_revenue
    total_sales = total_water_revenue + total_other_sales

    # 4. Hutang baru dari transaksi POS metode 'hutang'
    cursor.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM transactions
        WHERE DATE(created_at) BETWEEN ? AND ?
          AND status = 'completed'
          AND payment_method = 'hutang'
    """, (start_date, end_date))
    new_debt = int(round(cursor.fetchone()[0]))

    # 5. Pelunasan hutang pelanggan pada periode tersebut
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM debt_payments
        WHERE DATE(payment_date) BETWEEN ? AND ?
    """, (start_date, end_date))
    debt_collected = int(round(cursor.fetchone()[0]))

    # 6. Uang Masuk = Total Penjualan - Hutang Baru + Pelunasan Hutang
    cash_in = total_sales - new_debt + debt_collected

    # 7. Total pengeluaran
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE expense_date BETWEEN ? AND ?",
        (start_date, end_date)
    )
    total_expenses = int(round(cursor.fetchone()[0]))

    # 8. Selisih Kas = Uang Masuk - Total Pengeluaran
    net_cash = cash_in - total_expenses

    # 9. Detail transaksi POS
    cursor.execute("""
        SELECT t.*, u.full_name as kasir_name,
               COALESCE(c.name, 'Umum') as customer_name
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN customers c ON t.customer_id = c.id
        WHERE DATE(t.created_at) BETWEEN ? AND ? AND t.status = 'completed'
        ORDER BY t.created_at DESC
    """, (start_date, end_date))
    transactions = [dict(row) for row in cursor.fetchall()]

    # 10. Top products (dari POS)
    cursor.execute("""
        SELECT ti.product_name, SUM(ti.quantity) as total_qty, SUM(ti.subtotal) as total_revenue
        FROM transaction_items ti
        JOIN transactions t ON ti.transaction_id = t.id
        WHERE DATE(t.created_at) BETWEEN ? AND ? AND t.status = 'completed'
        GROUP BY ti.product_name
        ORDER BY total_qty DESC
        LIMIT 10
    """, (start_date, end_date))
    top_products = [dict(row) for row in cursor.fetchall()]

    # 11. Pengeluaran per kategori
    cursor.execute("""
        SELECT category, COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE expense_date BETWEEN ? AND ?
        GROUP BY category
    """, (start_date, end_date))
    expense_by_category = [{'category': row['category'], 'total': int(round(row['total']))} for row in cursor.fetchall()]

    # 12. Detail pengeluaran individual
    cursor.execute("""
        SELECT e.*, u.full_name as user_name
        FROM expenses e
        JOIN users u ON e.user_id = u.id
        WHERE e.expense_date BETWEEN ? AND ?
        ORDER BY e.expense_date DESC, e.created_at DESC
    """, (start_date, end_date))
    expenses = [dict(row) for row in cursor.fetchall()]

    # 13. Hutang upah kurir (saldo belum dibayar untuk transaksi aktif)
    cursor.execute("""
        SELECT COALESCE(SUM(cw.amount), 0)
        FROM courier_wages cw
        LEFT JOIN transactions t ON cw.transaction_id = t.id
        WHERE cw.status = 'belum_dibayar'
          AND (t.status IS NULL OR t.status != 'batal')
    """)
    total_courier_debt = int(round(cursor.fetchone()[0]))

    # 14. Ringkasan Upah per Kurir
    cursor.execute("""
        SELECT 
            c.id as courier_id,
            c.name as courier_name,
            c.payment_type,
            COUNT(CASE WHEN (t.status IS NULL OR t.status != 'batal') AND cw.id IS NOT NULL THEN cw.id ELSE NULL END) as total_deliveries,
            COALESCE(SUM(CASE WHEN t.status IS NULL OR t.status != 'batal' THEN cw.amount ELSE 0 END), 0) as total_wage,
            COALESCE(SUM(CASE WHEN (t.status IS NULL OR t.status != 'batal') AND cw.status = 'sudah_dibayar' THEN cw.amount ELSE 0 END), 0) as paid_wage,
            COALESCE(SUM(CASE WHEN (t.status IS NULL OR t.status != 'batal') AND cw.status = 'belum_dibayar' THEN cw.amount ELSE 0 END), 0) as balance
        FROM couriers c
        LEFT JOIN courier_wages cw ON c.id = cw.courier_id
        LEFT JOIN transactions t ON cw.transaction_id = t.id
        GROUP BY c.id, c.name, c.payment_type
        ORDER BY c.name
    """)
    courier_summary = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        'start_date': start_date,
        'end_date': end_date,
        'period': period,
        'total_bio_revenue': total_bio_revenue,
        'total_ro_revenue': total_ro_revenue,
        'total_water_revenue': total_water_revenue,
        'total_other_sales': total_other_sales,
        'total_sales': total_sales,
        'new_debt': new_debt,
        'debt_collected': debt_collected,
        'cash_in': cash_in,
        'total_expenses': total_expenses,
        'net_cash': net_cash,
        'daily_income': daily_income,
        'transactions': transactions,
        'total_count': len(transactions),
        'expense_by_category': expense_by_category,
        'expenses': expenses,
        'top_products': top_products,
        'total_courier_debt': total_courier_debt,
        'courier_summary': courier_summary,
    }


def get_recent_transactions(limit=5):
    """Mengambil transaksi terbaru untuk dashboard"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT t.invoice_number, COALESCE(c.name, 'Umum') as customer_name,
                  t.total, t.payment_method, t.created_at
           FROM transactions t
           LEFT JOIN customers c ON t.customer_id = c.id
           WHERE t.status = 'completed'
           ORDER BY t.created_at DESC LIMIT ?""",
        (limit,)
    )
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transactions


def get_low_stock_products(threshold=10):
    """Mengambil produk dengan stok rendah"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM products WHERE is_active = 1 AND stock < ? ORDER BY stock ASC",
        (threshold,)
    )
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return products


# ==================== COURIER & WAGE OPERATIONS ====================

def get_all_couriers(active_only=True):
    """Mengambil daftar semua kurir"""
    conn = get_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM couriers WHERE is_active = 1 AND (is_deleted IS NULL OR is_deleted = 0) ORDER BY name")
    else:
        cursor.execute("SELECT * FROM couriers WHERE (is_deleted IS NULL OR is_deleted = 0) ORDER BY is_active DESC, name ASC")
    couriers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return couriers


def get_courier_by_id(courier_id):
    """Mengambil data kurir berdasarkan ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM couriers WHERE id = ?", (courier_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_courier_by_name(name):
    """Mengambil data kurir berdasarkan nama"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM couriers WHERE name = ?", (name.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def add_courier(name, phone="", payment_type="dikumpulkan"):
    """Menambah kurir baru"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO couriers (name, phone, payment_type) VALUES (?, ?, ?)",
        (name.strip(), phone.strip(), payment_type)
    )
    conn.commit()
    courier_id = cursor.lastrowid
    conn.close()
    return courier_id


def update_courier(courier_id, name, phone, payment_type, is_active=1):
    """Update data kurir (Syarat 8: perubahan cara bayar hanya berlaku untuk transaksi berikutnya)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE couriers SET name = ?, phone = ?, payment_type = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (name.strip(), phone.strip(), payment_type, is_active, courier_id)
    )
    conn.commit()
    conn.close()


def deactivate_courier(courier_id):
    """Soft delete kurir: kurir tidak dihapus, hanya dinonaktifkan (Syarat 8)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE couriers SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (courier_id,))
    conn.commit()
    conn.close()


def delete_courier(courier_id):
    """
    Hapus kurir:
    - Jika kurir belum pernah tercatat di transactions atau courier_wages, hapus permanen dari couriers.
    - Jika sudah pernah ada transaksi/upah, soft delete (is_active = 0, is_deleted = 1) agar integritas data & laporan tetap terjaga.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE courier_id = ?", (courier_id,))
        trx_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM courier_wages WHERE courier_id = ?", (courier_id,))
        wage_count = cursor.fetchone()[0]

        if trx_count == 0 and wage_count == 0:
            cursor.execute("DELETE FROM couriers WHERE id = ?", (courier_id,))
        else:
            cursor.execute("""
                UPDATE couriers 
                SET is_active = 0, is_deleted = 1, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (courier_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def toggle_courier_active(courier_id):
    """Aktifkan / nonaktifkan kurir"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM couriers WHERE id = ?", (courier_id,))
    row = cursor.fetchone()
    if row:
        new_val = 0 if row['is_active'] == 1 else 1
        cursor.execute("UPDATE couriers SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_val, courier_id))
        conn.commit()
    conn.close()


def get_all_courier_names(active_only=True):
    """Mengambil daftar nama kurir"""
    conn = get_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT name FROM couriers WHERE is_active = 1 AND (is_deleted IS NULL OR is_deleted = 0) ORDER BY name")
    else:
        cursor.execute("SELECT name FROM couriers WHERE (is_deleted IS NULL OR is_deleted = 0) ORDER BY name")
    names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return names


def get_courier_wages(courier_id=None, status=None, start_date=None, end_date=None):
    """
    Mengambil daftar rincian upah kurir (Syarat 9):
    id, tanggal, id kurir, id transaksi, jumlah upah, status, tanggal bayar
    Mendukung filter kurir, status, dan rentang tanggal.
    """
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT cw.*, c.name as courier_name, c.payment_type,
               t.invoice_number, t.status as transaction_status,
               COALESCE(cust.name, 'Umum') as customer_name
        FROM courier_wages cw
        JOIN couriers c ON cw.courier_id = c.id
        LEFT JOIN transactions t ON cw.transaction_id = t.id
        LEFT JOIN customers cust ON t.customer_id = cust.id
        WHERE 1=1
    """
    params = []
    if courier_id:
        query += " AND cw.courier_id = ?"
        params.append(courier_id)
    else:
        query += " AND (c.is_deleted IS NULL OR c.is_deleted = 0)"
    if status and status != 'Semua':
        query += " AND cw.status = ?"
        params.append(status)
    if start_date:
        query += " AND cw.wage_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND cw.wage_date <= ?"
        params.append(end_date)

    query += " ORDER BY cw.created_at DESC"
    cursor.execute(query, params)
    wages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return wages


def get_courier_wage_summary(courier_id=None):
    """
    Mengambil ringkasan per kurir:
    - total_deliveries
    - total_wage
    - paid_wage
    - unpaid_wage (sisa saldo belum dibayar)
    Transaksi dengan status 'batal' dikecualikan dari saldo.
    """
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            c.id as courier_id,
            c.name as courier_name,
            c.phone,
            c.payment_type,
            c.is_active,
            COUNT(DISTINCT CASE WHEN (t.status IS NULL OR t.status != 'batal') AND cw.id IS NOT NULL THEN COALESCE(cw.transaction_id, cw.id) ELSE NULL END) as total_deliveries,
            COALESCE(SUM(CASE WHEN t.status IS NULL OR t.status != 'batal' THEN cw.amount ELSE 0 END), 0) as total_wage,
            COALESCE(SUM(CASE WHEN (t.status IS NULL OR t.status != 'batal') AND cw.status = 'sudah_dibayar' THEN cw.amount ELSE 0 END), 0) as paid_wage,
            COALESCE(SUM(CASE WHEN (t.status IS NULL OR t.status != 'batal') AND cw.status = 'belum_dibayar' THEN cw.amount ELSE 0 END), 0) as balance
        FROM couriers c
        LEFT JOIN courier_wages cw ON c.id = cw.courier_id
        LEFT JOIN transactions t ON cw.transaction_id = t.id
        WHERE (c.is_deleted IS NULL OR c.is_deleted = 0)
    """
    params = []
    if courier_id:
        query += " AND c.id = ?"
        params.append(courier_id)
    query += """
        GROUP BY c.id, c.name, c.phone, c.payment_type, c.is_active
        ORDER BY c.is_active DESC, c.name ASC
    """
    cursor.execute(query, params)
    summary = []
    for row in cursor.fetchall():
        d = dict(row)
        d['total_wage'] = int(round(d['total_wage']))
        d['paid_wage'] = int(round(d['paid_wage']))
        d['balance'] = int(round(d['balance']))
        summary.append(d)
    conn.close()
    return summary


def get_courier_stats():
    """Statistik kurir untuk kartu ringkasan"""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    # Total belum dibayar (transaksi aktif)
    cursor.execute("""
        SELECT COALESCE(SUM(cw.amount), 0), COUNT(DISTINCT COALESCE(cw.transaction_id, cw.id))
        FROM courier_wages cw
        LEFT JOIN transactions t ON cw.transaction_id = t.id
        LEFT JOIN couriers c ON cw.courier_id = c.id
        WHERE cw.status = 'belum_dibayar'
          AND (t.status IS NULL OR t.status != 'batal')
          AND (c.is_deleted IS NULL OR c.is_deleted = 0)
    """)
    row_unpaid = cursor.fetchone()
    unpaid_total = int(round(row_unpaid[0]))
    unpaid_count = row_unpaid[1]

    # Total sudah dibayar (transaksi aktif)
    cursor.execute("""
        SELECT COALESCE(SUM(cw.amount), 0), COUNT(DISTINCT COALESCE(cw.transaction_id, cw.id))
        FROM courier_wages cw
        LEFT JOIN transactions t ON cw.transaction_id = t.id
        LEFT JOIN couriers c ON cw.courier_id = c.id
        WHERE cw.status = 'sudah_dibayar'
          AND (t.status IS NULL OR t.status != 'batal')
          AND (c.is_deleted IS NULL OR c.is_deleted = 0)
    """)
    row_paid = cursor.fetchone()
    paid_total = int(round(row_paid[0]))
    paid_count = row_paid[1]

    # Antaran hari ini
    cursor.execute("""
        SELECT COALESCE(SUM(cw.amount), 0), COUNT(DISTINCT COALESCE(cw.transaction_id, cw.id))
        FROM courier_wages cw
        LEFT JOIN transactions t ON cw.transaction_id = t.id
        LEFT JOIN couriers c ON cw.courier_id = c.id
        WHERE cw.wage_date = ?
          AND (t.status IS NULL OR t.status != 'batal')
          AND (c.is_deleted IS NULL OR c.is_deleted = 0)
    """, (today,))
    row_today = cursor.fetchone()
    today_total = int(round(row_today[0]))
    today_count = row_today[1]

    conn.close()
    return {
        'unpaid_total': unpaid_total,
        'unpaid_count': unpaid_count,
        'paid_total': paid_total,
        'paid_count': paid_count,
        'today_total': today_total,
        'today_count': today_count,
    }


def pay_courier_wages(courier_id, user_id, notes="", amount=None):
    """
    Bayar upah kurir (Syarat 1, 2, 3, fleksibel/cicil):
    - Cek role Owner di logika program (bukan hanya menyembunyikan tombol).
    - Memilih kurir, menampilkan saldo belum dibayar.
    - Fleksibel: bisa bayar lunas (amount=None atau amount=balance) atau dicicil (amount < balance).
    - Satu transaksi database atomik:
      1. Alokasi pembayaran secara FIFO untuk upah-upah belum_dibayar.
         Jika ada upah yang terbayar sebagian, baris dipisah:
         bagian yang terbayar status='sudah_dibayar', sisa belum terbayar dimasukkan baris baru status='belum_dibayar'.
      2. Buat SATU baris Pengeluaran (expenses) kategori 'upah_kurir' dengan is_auto=1.
      3. Buat baris courier_payments (id, courier_id, total, paid_at, paid_by, notes, expense_id).
      Gagal di tengah = rollback semua.
    Returns (count_paid, pay_amount, payment_id)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Validasi role owner di logika program (Syarat 3)
    cursor.execute("SELECT role, full_name FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    if not user_row or user_row['role'] != 'owner':
        conn.close()
        raise PermissionError("Akses ditolak: Hanya Owner yang dapat melakukan pembayaran upah kurir!")

    cursor.execute("SELECT * FROM couriers WHERE id = ?", (courier_id,))
    courier = cursor.fetchone()
    if not courier:
        conn.close()
        raise ValueError("Kurir tidak ditemukan!")

    try:
        cursor.execute("BEGIN TRANSACTION")

        # Ambil upah berstatus belum_dibayar untuk transaksi yang aktif (bukan batal) urut FIFO
        cursor.execute("""
            SELECT cw.id, cw.amount, cw.transaction_id, cw.wage_date
            FROM courier_wages cw
            LEFT JOIN transactions t ON cw.transaction_id = t.id
            WHERE cw.courier_id = ?
              AND cw.status = 'belum_dibayar'
              AND (t.status IS NULL OR t.status != 'batal')
            ORDER BY cw.wage_date ASC, cw.id ASC
        """, (courier_id,))
        unpaid_wages = cursor.fetchall()

        if not unpaid_wages:
            conn.rollback()
            return 0, 0, None

        total_unpaid = sum(int(round(w['amount'])) for w in unpaid_wages)
        if total_unpaid <= 0:
            conn.rollback()
            return 0, 0, None

        # Tentukan nominal pembayaran
        if amount is None or amount >= total_unpaid:
            pay_amount = total_unpaid
        else:
            pay_amount = int(round(amount))

        if pay_amount <= 0:
            conn.rollback()
            raise ValueError("Nominal pembayaran harus lebih dari 0!")

        now_dt = datetime.now()
        today_str = now_dt.strftime("%Y-%m-%d")
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        is_cicil = (pay_amount < total_unpaid)
        cicil_text = " (Cicilan)" if is_cicil else ""

        # Hitung berapa antaran yang tercakup dalam pembayaran ini
        temp_rem = pay_amount
        covered_count = 0
        for w in unpaid_wages:
            if temp_rem <= 0:
                break
            covered_count += 1
            temp_rem -= int(round(w['amount']))

        desc = f"Pembayaran Upah Kurir{cicil_text}: {courier['name']} ({covered_count} antaran)"
        default_note = f"Cicilan upah kurir {courier['name']}" if is_cicil else f"Pelunasan saldo upah kurir {courier['name']}"
        exp_notes = notes.strip() or default_note

        # Buat SATU catatan Pengeluaran kategori 'upah_kurir'
        cursor.execute("""
            INSERT INTO expenses
            (category, description, amount, expense_date, user_id, notes, courier_id, payment_date, is_auto)
            VALUES ('upah_kurir', ?, ?, ?, ?, ?, ?, ?, 1)
        """, (desc, pay_amount, today_str, user_id, exp_notes, courier_id, now_str))
        expense_id = cursor.lastrowid

        # Buat baris courier_payments
        cursor.execute("""
            INSERT INTO courier_payments
            (courier_id, total, paid_at, paid_by, notes, expense_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (courier_id, pay_amount, now_str, user_id, notes.strip(), expense_id))
        payment_id = cursor.lastrowid

        # Alokasikan pembayaran secara FIFO
        remaining_to_pay = pay_amount
        paid_wage_ids = []

        for w in unpaid_wages:
            if remaining_to_pay <= 0:
                break
            w_id = w['id']
            w_amt = int(round(w['amount']))
            w_trx_id = w['transaction_id']
            w_date = w['wage_date']

            if remaining_to_pay >= w_amt:
                paid_wage_ids.append(w_id)
                remaining_to_pay -= w_amt
            else:
                # Dibayar sebagian: baris ini diupdate sebesar part_paid
                part_paid = remaining_to_pay
                part_unpaid = w_amt - remaining_to_pay

                cursor.execute("""
                    UPDATE courier_wages
                    SET amount = ?, status = 'sudah_dibayar', payment_id = ?, paid_at = ?
                    WHERE id = ?
                """, (part_paid, payment_id, now_str, w_id))

                # Buat baris baru untuk sisa upah yang belum dibayar
                cursor.execute("""
                    INSERT INTO courier_wages
                    (courier_id, transaction_id, amount, status, wage_date, created_at)
                    VALUES (?, ?, ?, 'belum_dibayar', ?, ?)
                """, (courier_id, w_trx_id, part_unpaid, w_date, now_str))

                remaining_to_pay = 0
                break

        if paid_wage_ids:
            placeholders = ','.join(['?'] * len(paid_wage_ids))
            cursor.execute(f"""
                UPDATE courier_wages
                SET status = 'sudah_dibayar', payment_id = ?, paid_at = ?
                WHERE id IN ({placeholders})
            """, [payment_id, now_str] + paid_wage_ids)

        conn.commit()
        return covered_count, pay_amount, payment_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_courier_payments(courier_id=None):
    """
    Mengambil riwayat pembayaran upah kurir dari tabel courier_payments (Syarat 1)
    """
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT cp.*, c.name as courier_name, u.full_name as paid_by_name,
               e.description as expense_description
        FROM courier_payments cp
        JOIN couriers c ON cp.courier_id = c.id
        LEFT JOIN users u ON cp.paid_by = u.id
        LEFT JOIN expenses e ON cp.expense_id = e.id
        WHERE 1=1
    """
    params = []
    if courier_id:
        query += " AND cp.courier_id = ?"
        params.append(courier_id)
    query += " ORDER BY cp.paid_at DESC"
    cursor.execute(query, params)
    payments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return payments


# ==================== WATER METER OPERATIONS (FLOW METER) ====================

def calculate_water_meter_values(bio_meter_start, bio_meter_end, ro_meter_start, ro_meter_end,
                                 bio_lpg=21.5, bio_price=5000.0, ro_lpg=20.5, ro_price=10000.0, status='closed'):
    """Helper untuk menghitung liter, galon, dan omzet air secara akurat"""
    if status == 'open':
        bio_liters = 0.0
        bio_gallons = 0.0
        bio_revenue = 0.0
        ro_liters = 0.0
        ro_gallons = 0.0
        ro_revenue = 0.0
    else:
        bio_liters = max(0.0, round(float(bio_meter_end) - float(bio_meter_start), 2))
        bio_gallons = round(bio_liters / float(bio_lpg), 2) if float(bio_lpg) > 0 else 0.0
        bio_revenue = round(bio_gallons * float(bio_price))

        ro_liters = max(0.0, round(float(ro_meter_end) - float(ro_meter_start), 2))
        ro_gallons = round(ro_liters / float(ro_lpg), 2) if float(ro_lpg) > 0 else 0.0
        ro_revenue = round(ro_gallons * float(ro_price))

    total_liters = round(bio_liters + ro_liters, 2)
    total_gallons = round(bio_gallons + ro_gallons, 2)
    total_revenue = round(bio_revenue + ro_revenue)

    return {
        'bio_liters': bio_liters,
        'bio_gallons': bio_gallons,
        'bio_revenue': bio_revenue,
        'ro_liters': ro_liters,
        'ro_gallons': ro_gallons,
        'ro_revenue': ro_revenue,
        'total_liters': total_liters,
        'total_gallons': total_gallons,
        'total_revenue': total_revenue,
    }


def add_water_meter(record_date, shift_name, user_id, user_name,
                    bio_meter_start, bio_meter_end, ro_meter_start, ro_meter_end,
                    bio_lpg=21.5, bio_price=5000.0, ro_lpg=20.5, ro_price=10000.0,
                    status='closed', notes=''):
    """Menambah catatan flow meter air baru"""
    vals = calculate_water_meter_values(
        bio_meter_start, bio_meter_end, ro_meter_start, ro_meter_end,
        bio_lpg, bio_price, ro_lpg, ro_price, status
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO water_meters (
            record_date, shift_name, user_id, user_name,
            bio_meter_start, bio_meter_end, bio_liters, bio_liters_per_gallon, bio_gallons, bio_price_per_gallon, bio_revenue,
            ro_meter_start, ro_meter_end, ro_liters, ro_liters_per_gallon, ro_gallons, ro_price_per_gallon, ro_revenue,
            total_liters, total_gallons, total_revenue, status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record_date, shift_name, user_id, user_name,
        float(bio_meter_start), float(bio_meter_end), vals['bio_liters'], float(bio_lpg), vals['bio_gallons'], float(bio_price), vals['bio_revenue'],
        float(ro_meter_start), float(ro_meter_end), vals['ro_liters'], float(ro_lpg), vals['ro_gallons'], float(ro_price), vals['ro_revenue'],
        vals['total_liters'], vals['total_gallons'], vals['total_revenue'], status, notes
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_water_meter(meter_id, record_date, shift_name, user_name,
                       bio_meter_start, bio_meter_end, ro_meter_start, ro_meter_end,
                       bio_lpg=21.5, bio_price=5000.0, ro_lpg=20.5, ro_price=10000.0,
                       status='closed', notes=''):
    """Update catatan flow meter air"""
    vals = calculate_water_meter_values(
        bio_meter_start, bio_meter_end, ro_meter_start, ro_meter_end,
        bio_lpg, bio_price, ro_lpg, ro_price, status
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE water_meters SET
            record_date = ?, shift_name = ?, user_name = ?,
            bio_meter_start = ?, bio_meter_end = ?, bio_liters = ?, bio_liters_per_gallon = ?, bio_gallons = ?, bio_price_per_gallon = ?, bio_revenue = ?,
            ro_meter_start = ?, ro_meter_end = ?, ro_liters = ?, ro_liters_per_gallon = ?, ro_gallons = ?, ro_price_per_gallon = ?, ro_revenue = ?,
            total_liters = ?, total_gallons = ?, total_revenue = ?, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        record_date, shift_name, user_name,
        float(bio_meter_start), float(bio_meter_end), vals['bio_liters'], float(bio_lpg), vals['bio_gallons'], float(bio_price), vals['bio_revenue'],
        float(ro_meter_start), float(ro_meter_end), vals['ro_liters'], float(ro_lpg), vals['ro_gallons'], float(ro_price), vals['ro_revenue'],
        vals['total_liters'], vals['total_gallons'], vals['total_revenue'], status, notes, meter_id
    ))
    conn.commit()
    conn.close()


def close_water_meter_shift(meter_id, bio_meter_end, ro_meter_end, notes=None):
    """Tutup shift meteran dengan memasukkan meter akhir dan menghitung hasil"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM water_meters WHERE id = ?", (meter_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    rec = dict(row)
    bio_start = rec['bio_meter_start']
    ro_start = rec['ro_meter_start']
    bio_lpg = rec['bio_liters_per_gallon']
    bio_price = rec['bio_price_per_gallon']
    ro_lpg = rec['ro_liters_per_gallon']
    ro_price = rec['ro_price_per_gallon']
    final_notes = notes if notes is not None else rec['notes']

    vals = calculate_water_meter_values(
        bio_start, bio_meter_end, ro_start, ro_meter_end,
        bio_lpg, bio_price, ro_lpg, ro_price, status='closed'
    )

    cursor.execute("""
        UPDATE water_meters SET
            bio_meter_end = ?, bio_liters = ?, bio_gallons = ?, bio_revenue = ?,
            ro_meter_end = ?, ro_liters = ?, ro_gallons = ?, ro_revenue = ?,
            total_liters = ?, total_gallons = ?, total_revenue = ?,
            status = 'closed', notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        float(bio_meter_end), vals['bio_liters'], vals['bio_gallons'], vals['bio_revenue'],
        float(ro_meter_end), vals['ro_liters'], vals['ro_gallons'], vals['ro_revenue'],
        vals['total_liters'], vals['total_gallons'], vals['total_revenue'],
        final_notes, meter_id
    ))
    conn.commit()
    conn.close()
    return True


def delete_water_meter(meter_id):
    """Hapus catatan flow meter"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM water_meters WHERE id = ?", (meter_id,))
    conn.commit()
    conn.close()


def get_water_meters(date_from=None, date_to=None, search=None, limit=300):
    """Mengambil daftar catatan flow meter dengan opsi filter tanggal dan pencarian"""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM water_meters WHERE 1=1"
    params = []

    if date_from:
        query += " AND record_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND record_date <= ?"
        params.append(date_to)
    if search:
        query += " AND (shift_name LIKE ? OR user_name LIKE ? OR notes LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY record_date DESC, id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_water_meter_by_id(meter_id):
    """Ambil satu data water meter berdasarkan ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM water_meters WHERE id = ?", (meter_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_latest_water_meter():
    """Mengambil catatan meteran terakhir yang sudah selesai untuk referensi meter awal berikutnya"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM water_meters
        WHERE status = 'closed' AND bio_meter_end > 0
        ORDER BY record_date DESC, id DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_open_water_meter_shift(user_id=None):
    """Mengecek apakah ada shift meteran yang saat ini masih berstatus 'open'"""
    conn = get_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM water_meters WHERE status = 'open' AND user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    else:
        cursor.execute("SELECT * FROM water_meters WHERE status = 'open' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_water_meter_summary(date_from=None, date_to=None):
    """Mengambil total ringkasan liter, galon, dan omzet flow meter dalam rentang tanggal"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            COALESCE(SUM(bio_liters), 0) as total_bio_liters,
            COALESCE(SUM(bio_gallons), 0) as total_bio_gallons,
            COALESCE(SUM(bio_revenue), 0) as total_bio_revenue,
            COALESCE(SUM(ro_liters), 0) as total_ro_liters,
            COALESCE(SUM(ro_gallons), 0) as total_ro_gallons,
            COALESCE(SUM(ro_revenue), 0) as total_ro_revenue,
            COALESCE(SUM(total_liters), 0) as total_liters,
            COALESCE(SUM(total_gallons), 0) as total_gallons,
            COALESCE(SUM(total_revenue), 0) as total_revenue,
            COUNT(*) as record_count
        FROM water_meters
        WHERE status = 'closed'
    """
    params = []
    if date_from:
        query += " AND record_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND record_date <= ?"
        params.append(date_to)

    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {
        'total_bio_liters': 0, 'total_bio_gallons': 0, 'total_bio_revenue': 0,
        'total_ro_liters': 0, 'total_ro_gallons': 0, 'total_ro_revenue': 0,
        'total_liters': 0, 'total_gallons': 0, 'total_revenue': 0,
        'record_count': 0
    }


def get_water_meter_reconciliation(target_date):
    """
    Rekonsiliasi data fisik meteran air dengan penjualan kasir (POS) pada tanggal tertentu.
    Menghitung selisih galon fisik vs galon terjual di kasir.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Total dari Flow Meter pada tanggal target
    cursor.execute("""
        SELECT
            COALESCE(SUM(bio_liters), 0) as meter_bio_liters,
            COALESCE(SUM(bio_gallons), 0) as meter_bio_gallons,
            COALESCE(SUM(bio_revenue), 0) as meter_bio_revenue,
            COALESCE(SUM(ro_liters), 0) as meter_ro_liters,
            COALESCE(SUM(ro_gallons), 0) as meter_ro_gallons,
            COALESCE(SUM(ro_revenue), 0) as meter_ro_revenue,
            COALESCE(SUM(total_liters), 0) as meter_total_liters,
            COALESCE(SUM(total_gallons), 0) as meter_total_gallons,
            COALESCE(SUM(total_revenue), 0) as meter_total_revenue
        FROM water_meters
        WHERE record_date = ? AND status = 'closed'
    """, (target_date,))
    meter_data = dict(cursor.fetchone())

    # 2. Penjualan Kasir POS pada tanggal target
    # Cari item dengan nama mengandung 'Bio' dan 'RO'
    cursor.execute("""
        SELECT
            ti.product_name,
            SUM(ti.quantity) as qty,
            SUM(ti.subtotal) as total_sales
        FROM transaction_items ti
        JOIN transactions t ON ti.transaction_id = t.id
        WHERE DATE(t.created_at) = ? AND t.status != 'cancelled'
        GROUP BY ti.product_name
    """, (target_date,))
    pos_items = cursor.fetchall()

    pos_bio_qty = 0
    pos_bio_sales = 0.0
    pos_ro_qty = 0
    pos_ro_sales = 0.0
    pos_other_qty = 0
    pos_other_sales = 0.0

    for item in pos_items:
        p_name = item['product_name'].lower()
        if 'bio' in p_name:
            pos_bio_qty += item['qty']
            pos_bio_sales += item['total_sales']
        elif 'ro' in p_name or 'osmosis' in p_name:
            pos_ro_qty += item['qty']
            pos_ro_sales += item['total_sales']
        else:
            pos_other_qty += item['qty']
            pos_other_sales += item['total_sales']

    # Total keseluruhan transaksi POS pada tanggal tersebut
    cursor.execute("""
        SELECT COALESCE(SUM(total), 0), COUNT(*)
        FROM transactions
        WHERE DATE(created_at) = ? AND status != 'cancelled'
    """, (target_date,))
    row_t = cursor.fetchone()
    pos_total_sales = row_t[0]
    pos_trx_count = row_t[1]

    conn.close()

    # Hitung selisih (Kasir vs Meteran)
    # Selisih galon: Kasir - Meteran (Jika negatif, air keluar lebih banyak daripada tercatat kasir)
    diff_bio_qty = pos_bio_qty - meter_data['meter_bio_gallons']
    diff_bio_sales = pos_bio_sales - meter_data['meter_bio_revenue']
    diff_ro_qty = pos_ro_qty - meter_data['meter_ro_gallons']
    diff_ro_sales = pos_ro_sales - meter_data['meter_ro_revenue']
    diff_total_sales = pos_total_sales - meter_data['meter_total_revenue']

    return {
        'target_date': target_date,
        'meter': meter_data,
        'pos': {
            'bio_qty': pos_bio_qty,
            'bio_sales': pos_bio_sales,
            'ro_qty': pos_ro_qty,
            'ro_sales': pos_ro_sales,
            'other_qty': pos_other_qty,
            'other_sales': pos_other_sales,
            'total_sales': pos_total_sales,
            'trx_count': pos_trx_count,
        },
        'diff': {
            'bio_qty': round(diff_bio_qty, 2),
            'bio_sales': round(diff_bio_sales),
            'ro_qty': round(diff_ro_qty, 2),
            'ro_sales': round(diff_ro_sales),
            'total_sales': round(diff_total_sales),
        }
    }
