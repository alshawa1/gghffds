"""
gui/styles.py
─────────────
Professional dark-theme color and font constants for the STC Operations GUI.
"""

# ─── Colour Palette ──────────────────────────────────────────────────────────

BG_DARK       = "#0d1117"   # Main window background
BG_CARD       = "#161b22"   # Card / panel background
BG_CARD_HOVER = "#1c2333"   # Card hover state
BG_SIDEBAR    = "#010409"   # Sidebar background
BG_HEADER     = "#0d1117"   # Header bar
BG_INPUT      = "#21262d"   # Input fields

ACCENT_BLUE   = "#1f6feb"   # Primary accent — blue
ACCENT_GREEN  = "#238636"   # Success / valid
ACCENT_RED    = "#da3633"   # Error / danger
ACCENT_ORANGE = "#d29922"   # Warning
ACCENT_PURPLE = "#8957e5"   # Info / secondary
ACCENT_TEAL   = "#1abc9c"   # Tertiary

TEXT_PRIMARY   = "#f0f6fc"  # Main text
TEXT_SECONDARY = "#8b949e"  # Muted / subtext
TEXT_MUTED     = "#484f58"  # Very muted

BORDER        = "#30363d"   # Default border
BORDER_FOCUS  = "#1f6feb"   # Focused input border

# Task card accent colors (one per task)
TASK_COLORS = [
    "#1f6feb",  # 1 — System Errors      — Blue
    "#238636",  # 2 — Contact Status     — Green
    "#d29922",  # 3 — Neglect            — Amber
    "#8957e5",  # 4 — Payments           — Purple
    "#1abc9c",  # 5 — Scheduling         — Teal
    "#da3633",  # 6 — Withdrawal         — Red
    "#f0883e",  # 7 — Target Customers   — Orange
    "#e91e8c",  # 8 — Full Report        — Pink
]

# ─── Fonts ───────────────────────────────────────────────────────────────────

FONT_TITLE_LARGE  = ("Segoe UI", 22, "bold")
FONT_TITLE        = ("Segoe UI", 16, "bold")
FONT_SUBTITLE     = ("Segoe UI", 12, "bold")
FONT_BODY         = ("Segoe UI", 10)
FONT_SMALL        = ("Segoe UI", 9)
FONT_MONO         = ("Consolas", 9)

# Arabic-capable fonts for mixed/Arabic text
FONT_ARABIC_TITLE = ("Tahoma", 16, "bold")
FONT_ARABIC_BODY  = ("Tahoma", 11)
FONT_ARABIC_SMALL = ("Tahoma", 9)

# ─── Sizing ──────────────────────────────────────────────────────────────────

WINDOW_WIDTH  = 1200
WINDOW_HEIGHT = 780
SIDEBAR_WIDTH = 220
HEADER_HEIGHT = 64
CARD_PADDING  = 18
CORNER_RADIUS = 8

# ─── Geometry helpers ────────────────────────────────────────────────────────

def center_window(win, w: int, h: int):
    """Center a Toplevel/Tk window on screen."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
