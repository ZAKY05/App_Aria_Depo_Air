"""
Test script for Courier Wages (Upah Kurir) implementation.
Uses depo_air_test.db as required by user instruction #13.
"""
import os
import sys

# Ensure DEPO_DB_NAME points to depo_air_test.db
os.environ["DEPO_DB_NAME"] = "depo_air_test.db"

import database as db

def run_tests():
    print("=" * 60)
    print("STARTING TEST SUITE ON depo_air_test.db")
    print("=" * 60)
    
    # Initialize DB (runs migrations if not already run)
    db.init_database()
    
    conn = db.get_connection()
    c = conn.cursor()
    
    # -------------------------------------------------------------
    # Test 0: Meteran Air verification for 7-12 Oktober 2026
    # Must remain exactly Rp 6.005.150 (Scenario 6)
    # -------------------------------------------------------------
    print("\n[TEST 0] Verifikasi Omzet Meteran Air (7-12 Oktober 2026)...")
    c.execute("""
        SELECT COALESCE(SUM(total_revenue), 0)
        FROM water_meters
        WHERE record_date BETWEEN '2026-10-07' AND '2026-10-12'
    """)
    meter_rev = c.fetchone()[0]
    print(f"  -> Omzet Meteran Air 7-12 Okt 2026: Rp {int(meter_rev):,}")
    assert meter_rev == 6005150, f"FAILED: Expected 6005150, got {meter_rev}"
    print("  -> PASS: Omzet meteran air tetap Rp 6.005.150!")

    # -------------------------------------------------------------
    # Setup Test Data: Products, Users, Couriers
    # -------------------------------------------------------------
    print("\n[SETUP] Menyiapkan data uji kurir, kasir, owner, produk...")
    
    # Check or create Owner and Kasir
    c.execute("SELECT id, username, role FROM users WHERE role = 'owner' LIMIT 1")
    owner = c.fetchone()
    if not owner:
        owner_id = db.add_user("owner_test", "password", "Owner Test", "owner")
    else:
        owner_id = owner['id']
    
    c.execute("SELECT id, username, role FROM users WHERE role = 'kasir' LIMIT 1")
    kasir = c.fetchone()
    if not kasir:
        kasir_id = db.add_user("kasir_test", "password", "Kasir Test", "kasir")
    else:
        kasir_id = kasir['id']
        
    print(f"  -> Owner ID: {owner_id}, Kasir ID: {kasir_id}")
    
    # Create or update products with courier_fee_per_unit
    c.execute("SELECT id FROM products WHERE name = 'Galon Aqua Test' LIMIT 1")
    p1 = c.fetchone()
    if not p1:
        prod_galon_id = db.add_product("Galon Aqua Test", "Galon", 14000, 19000, 100, "galon", courier_fee_per_unit=2000)
    else:
        prod_galon_id = p1['id']
        db.update_product(prod_galon_id, "Galon Aqua Test", "Galon", 14000, 19000, 100, "galon", courier_fee_per_unit=2000)

    c.execute("SELECT id FROM products WHERE name = 'Es Kristal Test' LIMIT 1")
    p2 = c.fetchone()
    if not p2:
        prod_es_id = db.add_product("Es Kristal Test", "Lainnya", 5000, 10000, 100, "pcs", courier_fee_per_unit=1500)
    else:
        prod_es_id = p2['id']
        db.update_product(prod_es_id, "Es Kristal Test", "Lainnya", 5000, 10000, 100, "pcs", courier_fee_per_unit=1500)

    # Couriers: one 'langsung', one 'dikumpulkan'
    c.execute("SELECT id FROM couriers WHERE name = 'Kurir Langsung Test' LIMIT 1")
    c_l = c.fetchone()
    if not c_l:
        c_langsung_id = db.add_courier("Kurir Langsung Test", "0811111111", "langsung")
    else:
        c_langsung_id = c_l['id']
        db.update_courier(c_langsung_id, "Kurir Langsung Test", "0811111111", "langsung")

    c.execute("SELECT id FROM couriers WHERE name = 'Kurir Kumpul Test' LIMIT 1")
    c_k = c.fetchone()
    if not c_k:
        c_kumpul_id = db.add_courier("Kurir Kumpul Test", "0822222222", "dikumpulkan")
    else:
        c_kumpul_id = c_k['id']
        db.update_courier(c_kumpul_id, "Kurir Kumpul Test", "0822222222", "dikumpulkan")

    print(f"  -> Kurir Langsung ID: {c_langsung_id}, Kurir Kumpul ID: {c_kumpul_id}")
    
    # -------------------------------------------------------------
    # Skenario 1: Kurir "langsung"
    # Upah otomatis berstatus 'sudah_dibayar' dan muncul di Pengeluaran
    # saat transaksi disimpan. Keterangan pengeluaran memuat no invoice.
    # Total transaksi pelanggan TIDAK ditambahi ongkos antar (Syarat 11).
    # -------------------------------------------------------------
    print("\n[TEST 1] Skenario Kurir 'langsung'...")
    items_trx1 = [
        {'product_id': prod_galon_id, 'quantity': 3, 'unit_price': 19000}, # wage: 3 x 2000 = 6000
        {'product_id': prod_es_id, 'quantity': 2, 'unit_price': 10000},    # wage: 2 x 1500 = 3000
    ]
    # Expected customer total: 3*19000 + 2*10000 = 57000 + 20000 = 77000 (NO delivery fee added!)
    # Expected courier wage: 6000 + 3000 = 9000
    expected_total_1 = 77000
    expected_wage_1 = 9000
    
    trx1_id, inv1 = db.create_transaction(
        customer_id=None,
        user_id=kasir_id,
        items=items_trx1,
        payment_method='cash',
        paid_amount=100000,
        discount=0,
        is_delivery=True,
        courier_id=c_langsung_id
    )
    print(f"  -> Transaksi 1 berhasil: Inv={inv1}, ID={trx1_id}")
    
    # Verify transaction total in DB
    c.execute("SELECT total FROM transactions WHERE id = ?", (trx1_id,))
    t1_row = c.fetchone()
    assert t1_row['total'] == expected_total_1, f"FAILED: Total should be {expected_total_1}, got {t1_row['total']}"
    
    # Cek upah kurir di courier_wages
    c.execute("SELECT * FROM courier_wages WHERE transaction_id = ?", (trx1_id,))
    cw1 = c.fetchone()
    assert cw1 is not None, "FAILED: courier_wages not created!"
    assert cw1['amount'] == expected_wage_1, f"FAILED: Wage should be {expected_wage_1}, got {cw1['amount']}"
    assert cw1['status'] == 'sudah_dibayar', f"FAILED: Wage status should be 'sudah_dibayar', got {cw1['status']}"
    assert cw1['payment_id'] is not None, "FAILED: payment_id should not be None for kurir langsung"
    
    # Cek courier_payments
    c.execute("SELECT * FROM courier_payments WHERE id = ?", (cw1['payment_id'],))
    cp1 = c.fetchone()
    assert cp1 is not None, "FAILED: courier_payments record not created!"
    assert cp1['total'] == expected_wage_1
    assert cp1['courier_id'] == c_langsung_id
    
    # Cek pengeluaran (expenses)
    c.execute("SELECT * FROM expenses WHERE id = ?", (cp1['expense_id'],))
    exp1 = c.fetchone()
    assert exp1 is not None, "FAILED: expense record not created!"
    assert exp1['category'] == 'upah_kurir', f"FAILED: Category should be 'upah_kurir', got {exp1['category']}"
    assert exp1['amount'] == expected_wage_1
    assert exp1['is_auto'] == 1
    assert inv1 in exp1['description'], f"FAILED: Expense description should contain invoice {inv1}, got '{exp1['description']}'"
    print(f"  -> PASS: Upah langsung otomatis sudah_dibayar, tercatat di courier_payments & expenses (ket: '{exp1['description']}')!")

    # -------------------------------------------------------------
    # Skenario 2: Transaksi HUTANG yang diantar
    # Upah tetap tercatat, kurir 'dikumpulkan' berstatus belum_dibayar
    # Saldo bertambah.
    # -------------------------------------------------------------
    print("\n[TEST 2] Skenario Transaksi HUTANG yang diantar (kurir 'dikumpulkan')...")
    
    # Customer for debt
    c.execute("SELECT id FROM customers WHERE name = 'Pelanggan Uji Hutang' LIMIT 1")
    cust = c.fetchone()
    if not cust:
        cust_id = db.add_customer("Pelanggan Uji Hutang", "0833333333", "Jl. Mawar")
    else:
        cust_id = cust['id']
        
    items_trx2 = [
        {'product_id': prod_galon_id, 'quantity': 5, 'unit_price': 19000}, # 5 x 2000 = 10000
    ]
    # Total: 5 x 19000 = 95000. Customer debt increases by 95000. Courier wage = 10000.
    trx2_id, inv2 = db.create_transaction(
        customer_id=cust_id,
        user_id=kasir_id,
        items=items_trx2,
        payment_method='hutang',
        paid_amount=0,
        discount=0,
        is_delivery=True,
        courier_id=c_kumpul_id
    )
    print(f"  -> Transaksi 2 (Hutang) berhasil: Inv={inv2}, ID={trx2_id}")
    
    # Verify customer debt
    cust_data = db.get_customer_by_id(cust_id)
    assert cust_data['debt_amount'] >= 95000, f"Customer debt not updated! debt_amount={cust_data.get('debt_amount')}"
    
    # Verify courier wage
    c.execute("SELECT * FROM courier_wages WHERE transaction_id = ?", (trx2_id,))
    cw2 = c.fetchone()
    assert cw2 is not None, "FAILED: courier_wages not created for debt transaction!"
    assert cw2['amount'] == 10000, f"Expected wage 10000, got {cw2['amount']}"
    assert cw2['status'] == 'belum_dibayar', f"Expected status 'belum_dibayar', got {cw2['status']}"
    assert cw2['payment_id'] is None
    
    # Check courier balance
    def get_courier_balance(c_id):
        summary = db.get_courier_wage_summary(c_id)
        return summary[0]['balance'] if summary else 0

    bal_kumpul = get_courier_balance(c_kumpul_id)
    print(f"  -> Saldo kurir kumpul sekarang: Rp {bal_kumpul:,}")
    assert bal_kumpul >= 10000, "Saldo kurir kumpul should be at least 10000"
    print("  -> PASS: Transaksi HUTANG diantar tercatat upahnya dan berstatus belum_dibayar!")

    # -------------------------------------------------------------
    # Skenario 3: Transaksi dibatalkan (status 'batal')
    # Upahnya keluar dari saldo, upah sudah_dibayar beri peringatan
    # -------------------------------------------------------------
    print("\n[TEST 3] Skenario Transaksi Dibatalkan...")
    # Add another transaction for c_kumpul to test cancellation of unpaid wage
    items_trx3 = [
        {'product_id': prod_galon_id, 'quantity': 2, 'unit_price': 19000}, # 4000
    ]
    trx3_id, inv3 = db.create_transaction(
        customer_id=None,
        user_id=kasir_id,
        items=items_trx3,
        payment_method='cash',
        paid_amount=50000,
        discount=0,
        is_delivery=True,
        courier_id=c_kumpul_id
    )
    bal_before_cancel = get_courier_balance(c_kumpul_id)
    
    # Cancel transaction 3 (wage is belum_dibayar)
    success3, warning3 = db.cancel_transaction(trx3_id)
    assert success3 is True
    assert warning3 is None, f"Should not have wage warning for belum_dibayar, got {warning3}"
    
    bal_after_cancel = get_courier_balance(c_kumpul_id)
    print(f"  -> Saldo sebelum batal: {bal_before_cancel}, setelah batal: {bal_after_cancel}")
    assert bal_after_cancel == bal_before_cancel - 4000, f"Saldo should decrease by 4000, got diff {bal_before_cancel - bal_after_cancel}"
    
    # Now cancel transaction 1 (wage is ALREADY sudah_dibayar) -> should return warning!
    success1, warning1 = db.cancel_transaction(trx1_id)
    assert success1 is True
    assert warning1 is not None, "FAILED: cancel_transaction must return warning when wage is already paid!"
    print(f"  -> Peringatan pembatalan upah sudah dibayar: {warning1}")
    print("  -> PASS: Transaksi batal mengeluarkan upah dari saldo dan memberi peringatan jika sudah dibayar!")

    # -------------------------------------------------------------
    # Skenario 4: Role Check - Kasir memanggil fungsi bayar upah ditolak
    # -------------------------------------------------------------
    print("\n[TEST 4] Skenario Hak Akses: Kasir memanggil pay_courier_wages()...")
    permission_denied = False
    try:
        db.pay_courier_wages(c_kumpul_id, user_id=kasir_id, notes="Coba kasir bayar")
    except PermissionError as pe:
        permission_denied = True
        print(f"  -> Berhasil ditolak dengan PermissionError: {pe}")
    except Exception as e:
        print(f"  -> Error lain: {e}")
        
    assert permission_denied, "FAILED: Kasir memanggil pay_courier_wages() HARUS melempar PermissionError!"
    print("  -> PASS: Kasir ditolak saat memanggil fungsi bayar upah kurir!")

    # -------------------------------------------------------------
    # Skenario 5: Simulasi error di tengah proses bayar -> Rollback atomic
    # -------------------------------------------------------------
    print("\n[TEST 5] Simulasi error di tengah proses bayar upah (Atomic Rollback)...")
    
    # We will test atomic rollback by temporarily injecting a failure in pay_courier_wages
    bal_prior = get_courier_balance(c_kumpul_id)
    assert bal_prior > 0, "Kurir kumpul should have pending balance to test"
    
    # Let's verify by monkeypatching get_connection during pay_courier_wages to simulate failure during expense insertion
    original_get_conn = db.get_connection

    class FailingCursor:
        def __init__(self, real_cursor):
            self.real_cursor = real_cursor
        def execute(self, sql, *args, **kwargs):
            if "INSERT INTO expenses" in sql:
                raise RuntimeError("SIMULATED DATABASE DISK CRASH ON EXPENSES INSERTION")
            return self.real_cursor.execute(sql, *args, **kwargs)
        def fetchone(self):
            return self.real_cursor.fetchone()
        def fetchall(self):
            return self.real_cursor.fetchall()
        @property
        def lastrowid(self):
            return self.real_cursor.lastrowid
        def __getattr__(self, name):
            return getattr(self.real_cursor, name)

    class FailingConnection:
        def __init__(self, real_conn):
            self.real_conn = real_conn
        def cursor(self):
            return FailingCursor(self.real_conn.cursor())
        def commit(self):
            return self.real_conn.commit()
        def rollback(self):
            return self.real_conn.rollback()
        def close(self):
            return self.real_conn.close()
        def __getattr__(self, name):
            return getattr(self.real_conn, name)

    db.get_connection = lambda: FailingConnection(original_get_conn())
    
    simulated_failed = False
    try:
        db.pay_courier_wages(c_kumpul_id, user_id=owner_id, notes="Simulasi Error")
    except RuntimeError as re:
        simulated_failed = True
        print(f"  -> Error berhasil disimulasikan: {re}")
    finally:
        db.get_connection = original_get_conn
        
    assert simulated_failed, "Failed to simulate error"
    
    # Now verify database state: no courier_payments created, courier_wages still belum_dibayar, no expense created!
    c.execute("SELECT COUNT(*) FROM courier_payments WHERE notes = 'Simulasi Error'")
    assert c.fetchone()[0] == 0, "FAILED: courier_payments record was saved despite crash!"
    
    c.execute("SELECT COUNT(*) FROM expenses WHERE notes = 'Simulasi Error'")
    assert c.fetchone()[0] == 0, "FAILED: expense record was saved despite crash!"
    
    c.execute("SELECT status FROM courier_wages WHERE transaction_id = ?", (trx2_id,))
    assert c.fetchone()['status'] == 'belum_dibayar', "FAILED: wage status was changed to sudah_dibayar despite crash!"
    
    bal_after_sim = get_courier_balance(c_kumpul_id)
    assert bal_after_sim == bal_prior, f"FAILED: balance changed! prior={bal_prior}, after={bal_after_sim}"
    print("  -> PASS: Rollback berhasil 100%! Tidak ada data setengah tersimpan saat terjadi error!")

    # -------------------------------------------------------------
    # Skenario 5b: Pembayaran normal oleh Owner (Atomic Success)
    # -------------------------------------------------------------
    print("\n[TEST 5b] Pembayaran Upah Normal oleh Owner...")
    count_paid, total_paid, payment_id = db.pay_courier_wages(c_kumpul_id, user_id=owner_id, notes="Pembayaran Resmi")
    print(f"  -> Bayar sukses: Payment ID={payment_id}, Jumlah Transaksi={count_paid}, Total={total_paid}")
    
    assert total_paid >= 10000
    
    # Check wage is now 'sudah_dibayar' and payment_id is set
    c.execute("SELECT status, payment_id FROM courier_wages WHERE transaction_id = ?", (trx2_id,))
    cw2_after = c.fetchone()
    assert cw2_after['status'] == 'sudah_dibayar'
    assert cw2_after['payment_id'] == payment_id
    
    # Check courier_payments
    c.execute("SELECT * FROM courier_payments WHERE id = ?", (payment_id,))
    cp_rec = c.fetchone()
    assert cp_rec is not None
    assert cp_rec['total'] == total_paid
    assert cp_rec['paid_by'] == owner_id
    expense_id = cp_rec['expense_id']
    
    # Check expense
    c.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    exp_rec = c.fetchone()
    assert exp_rec is not None
    assert exp_rec['category'] == 'upah_kurir'
    assert exp_rec['is_auto'] == 1
    
    bal_after_pay = get_courier_balance(c_kumpul_id)
    print(f"  -> Saldo kurir kumpul setelah pelunasan: Rp {bal_after_pay:,}")
    assert bal_after_pay == 0, f"Expected balance 0, got {bal_after_pay}"
    print("  -> PASS: Pembayaran upah oleh Owner berhasil secara utuh dalam 1 transaksi!")

    # -------------------------------------------------------------
    # Skenario 6: Perlindungan Pengeluaran upah_kurir
    # Tidak bisa diedit atau dihapus dari Pengeluaran
    # -------------------------------------------------------------
    print("\n[TEST 6] Perlindungan Pengeluaran Otomatis (upah_kurir)...")
    cannot_delete = False
    try:
        db.delete_expense(expense_id)
    except (PermissionError, ValueError) as ve:
        cannot_delete = True
        print(f"  -> Hapus ditolak: {ve}")
    assert cannot_delete, "FAILED: Pengeluaran upah_kurir harusnya tidak bisa dihapus!"

    cannot_update = False
    try:
        db.update_expense(expense_id, "upah_kurir", "Coba ubah", 50000, "2026-10-19", "Coba ubah")
    except (PermissionError, ValueError) as ve:
        cannot_update = True
        print(f"  -> Edit ditolak: {ve}")
    assert cannot_update, "FAILED: Pengeluaran upah_kurir harusnya tidak bisa diedit!"
    print("  -> PASS: Pengeluaran upah_kurir terlindungi dari edit dan hapus!")

    # -------------------------------------------------------------
    # Skenario 7: Laporan dan Ringkasan Upah Kurir (Syarat 12)
    # -------------------------------------------------------------
    print("\n[TEST 7] Verifikasi Laporan Penjualan & Upah Kurir...")
    report = db.get_sales_report('daily', '2026-10-01', '2026-10-31')
    assert 'total_courier_debt' in report
    assert 'courier_summary' in report
    print(f"  -> Total Hutang Upah Kurir di Laporan: Rp {report['total_courier_debt']:,}")
    print(f"  -> Jumlah Kurir di Ringkasan Laporan: {len(report['courier_summary'])}")
    for cs in report['courier_summary']:
        print(f"     * {cs['courier_name']}: Total Upah=Rp {cs['total_wage']:,}, Dibayar=Rp {cs['paid_wage']:,}, Saldo=Rp {cs['balance']:,}")
    print("  -> PASS: Laporan memuat kartu hutang upah kurir dan ringkasan upah!")

    # -------------------------------------------------------------
    # Final Check: Meteran Air verification (Re-check)
    # -------------------------------------------------------------
    c.execute("""
        SELECT COALESCE(SUM(total_revenue), 0)
        FROM water_meters
        WHERE record_date BETWEEN '2026-10-07' AND '2026-10-12'
    """)
    meter_final = c.fetchone()[0]
    assert meter_final == 6005150, f"FAILED: Meter revenue altered! Got {meter_final}"
    print(f"\n[FINAL CHECK] Meteran Air 7-12 Okt 2026 tetap: Rp {int(meter_final):,} (KONSISTEN!)")
    
    conn.close()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! (100% OK)")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
