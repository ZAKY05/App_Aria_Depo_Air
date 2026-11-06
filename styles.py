"""
Konfigurasi tema dan styling untuk Aplikasi Kasir Depo Air
Warna utama: Biru dan Putih
"""

# ==================== COLOR PALETTE ====================
COLORS = {
    'primary': '#1565C0',
    'primary_dark': '#0D47A1',
    'primary_light': '#1E88E5',
    'primary_hover': '#1976D2',
    'accent': '#42A5F5',
    'accent_light': '#90CAF9',

    'white': '#FFFFFF',
    'bg_light': '#F0F4F8',
    'bg_card': '#FFFFFF',
    'bg_sidebar': '#0D47A1',
    'bg_sidebar_hover': '#1565C0',
    'bg_sidebar_active': '#1E88E5',

    'text_dark': '#1A1A2E',
    'text_medium': '#4A5568',
    'text_light': '#718096',
    'text_white': '#FFFFFF',
    'text_sidebar': '#B3D4FC',

    'border': '#CBD5E0',
    'border_light': '#E2E8F0',

    'success': '#2E7D32',
    'success_bg': '#E8F5E9',
    'warning': '#F57F17',
    'warning_bg': '#FFF8E1',
    'danger': '#C62828',
    'danger_bg': '#FFEBEE',
    'info': '#1565C0',
    'info_bg': '#E3F2FD',
}

# ==================== FONTS ====================
FONTS = {
    'title': ('Segoe UI', 22, 'bold'),
    'subtitle': ('Segoe UI', 16, 'bold'),
    'heading': ('Segoe UI', 14, 'bold'),
    'body': ('Segoe UI', 11),
    'body_bold': ('Segoe UI', 11, 'bold'),
    'small': ('Segoe UI', 9),
    'small_bold': ('Segoe UI', 9, 'bold'),
    'button': ('Segoe UI', 11, 'bold'),
    'sidebar': ('Segoe UI', 12),
    'sidebar_bold': ('Segoe UI', 12, 'bold'),
    'input': ('Segoe UI', 11),
    'table': ('Segoe UI', 10),
    'table_header': ('Segoe UI', 10, 'bold'),
    'big_number': ('Segoe UI', 28, 'bold'),
    'medium_number': ('Segoe UI', 18, 'bold'),
    'login_title': ('Segoe UI', 26, 'bold'),
    'login_subtitle': ('Segoe UI', 12),
}

# ==================== SIZES ====================
SIZES = {
    'sidebar_width': 240,
    'header_height': 60,
    'padding': 20,
    'padding_small': 10,
    'padding_large': 30,
    'border_radius': 8,
    'input_height': 38,
    'button_height': 40,
    'card_padding': 20,
}

# ==================== ICONS (Unicode) ====================
ICONS = {
    'dashboard': '📊',
    'product': '📦',
    'customer': '👥',
    'transaction': '🛒',
    'expense': '💸',
    'report': '📈',
    'logout': '🚪',
    'add': '➕',
    'edit': '✏️',
    'delete': '🗑️',
    'search': '🔍',
    'money': '💰',
    'cart': '🛒',
    'user': '👤',
    'lock': '🔒',
    'warning': '⚠️',
    'check': '✅',
    'close': '❌',
    'refresh': '🔄',
    'print': '🖨️',
    'calendar': '📅',
    'store': '🏪',
    'water': '💧',
    'debt': '📋',
    'payment': '💳',
    'flowmeter': '⏱️',
    'save': '💾',
}


def format_currency(amount):
    """Format angka ke format Rupiah"""
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return "Rp 0"
    if amount < 0:
        return f"-Rp {abs(amount):,.0f}".replace(",", ".")
    return f"Rp {amount:,.0f}".replace(",", ".")


def format_number(number):
    """Format angka dengan pemisah ribuan"""
    try:
        return f"{int(number):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"


def format_decimal(number, decimals=1):
    """Format angka desimal standar Indonesia: ribuan titik (.), desimal koma (,)"""
    try:
        val = float(number)
        formatted = f"{val:,.{decimals}f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0"


def parse_locale_number(val_str):
    """
    Mengonversi input teks angka ke float secara aman.
    Mendukung format Indonesia (titik ribuan, koma desimal) maupun format desimal titik.
    Contoh:
      "4246.4"   -> 4246.4
      "4246,4"   -> 4246.4
      "4.246,4"  -> 4246.4
      "4,246.4"  -> 4246.4
    """
    if val_str is None:
        return 0.0
    s = str(val_str).strip()
    if not s:
        return 0.0
    if '.' in s and ',' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    return float(s)
