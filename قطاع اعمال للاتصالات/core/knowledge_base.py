import sqlite3
import os
import logging
from datetime import datetime

_log = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "copilot_memory.db")

# Default pre-trained column synonyms
PRETRAINED_MAPPINGS = {
    "remaining_balance": [
        "متبقي سداد موثق", "متبقي السداد", "متبقي سداد العقد",
        "Balance Due", "Current Balance Due", "الرصيد المتبقي", "المتبقي"
    ],
    "debt_amount": [
        "مبلغ المديونية", "مبلغ الميدونية", "Balance Due", "مبلغ التعديل"
    ],
    "paid_amount": [
        "مبلغ السداد", "Payment Amount", "مبالغ وعود السداد"
    ],
    "national_id": [
        "رقم الهوية", "الهوية", "Customer ID"
    ],
    "main_id": [
        "الرقم الرئيسي", "رقم الحساب", "Account No.", "Service No.", "رقم المديونية"
    ],
    "customer_name": [
        "اسم العميل", "Customer Name"
    ],
    "collector": [
        "اسم المحصل", "المحصل", "الموظف", "المحصل الجديد"
    ],
    "supervisor": [
        "المشرف", "المشرف موثق السداد"
    ],
    "main_status": [
        "الحالة الرئيسية", "الحالة", "حالة الحساب"
    ],
    "followup_note": [
        "المتابعة", "آخر متابعة على العميل", "أخر متابعة للعميل",
        "الملاحظات", "الملاحظة"
    ],
    "portfolio_name": [
        "اسم الحاوية", "المحافظ", "الجهة"
    ]
}

# Default SOP rules
DEFAULT_RULES = {
    "neglect_exclusion_keywords": "مقطوع,الرقم غير صحيح,لا يخص,لايخص",
    "target_customer_keywords": "ع الراتب,علي الراتب,على الراتب,يوم 1,حساب مواطن,اخر الشهر,بسدد,منتظم",
    "target_customer_positive_statuses": "سداد جزئي,واعد بالسداد,وعد السداد,متوفي والورثة",
    "target_customer_negative_override": "لا يرد,مغلق",
    "balancing_min_chunk": "150",
    "excel_version_suffix": "v2"
}


class CopilotKnowledgeBase:
    """
    قاعدة المعرفة المستمرة للـ AI Operations Copilot باستخدام SQLite.
    تحفظ سياسات الشركة، مرادفات الأعمدة، وسجل القرارات والتعديلات.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            # 1. SOP & Company Rules
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sop_rules (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    updated_at TEXT NOT NULL
                )
            """)
            # 2. Schema Column Mappings & Synonyms
            cur.execute("""
                CREATE TABLE IF NOT EXISTS column_mappings (
                    column_raw TEXT PRIMARY KEY,
                    target_field TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    status TEXT DEFAULT 'approved',
                    updated_at TEXT NOT NULL
                )
            """)
            # 3. Supervisor Registry
            cur.execute("""
                CREATE TABLE IF NOT EXISTS supervisor_registry (
                    supervisor_name TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'active',
                    collector_count INTEGER DEFAULT 0,
                    notes TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            # 4. Execution Audit Log
            cur.execute("""
                CREATE TABLE IF NOT EXISTS execution_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_filename TEXT,
                    output_filename TEXT,
                    action_taken TEXT NOT NULL,
                    rows_affected INTEGER DEFAULT 0,
                    cols_affected TEXT,
                    reason TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

        # Seed pre-trained mappings and default rules if empty
        self._seed_defaults()

    def _seed_defaults(self):
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            # Seed rules
            for k, v in DEFAULT_RULES.items():
                cur.execute(
                    "INSERT OR IGNORE INTO sop_rules (key, value, category, updated_at) VALUES (?, ?, 'sop', ?)",
                    (k, v, now)
                )
            # Seed mappings
            for target_field, synonyms in PRETRAINED_MAPPINGS.items():
                for syn in synonyms:
                    cur.execute(
                        "INSERT OR IGNORE INTO column_mappings (column_raw, target_field, confidence, status, updated_at) VALUES (?, ?, 1.0, 'approved', ?)",
                        (syn, target_field, now)
                    )
            conn.commit()

    # ── Mappings API ──────────────────────────────────────────────────────────
    def get_column_mapping(self, column_name: str) -> dict | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM column_mappings WHERE column_raw = ?", (column_name.strip(),))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_approved_mappings(self) -> dict[str, str]:
        """Returns dict: {column_raw: target_field} for approved columns."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT column_raw, target_field FROM column_mappings WHERE status = 'approved'")
            return {row["column_raw"]: row["target_field"] for row in cur.fetchall()}

    def save_column_mapping(self, column_raw: str, target_field: str, confidence: float = 1.0, status: str = "approved"):
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO column_mappings (column_raw, target_field, confidence, status, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(column_raw) DO UPDATE SET
                    target_field=excluded.target_field,
                    confidence=excluded.confidence,
                    status=excluded.status,
                    updated_at=excluded.updated_at
            """, (column_raw.strip(), target_field, confidence, status, now))
            conn.commit()

    # ── SOP Rules API ─────────────────────────────────────────────────────────
    def get_rule(self, key: str, default: str = "") -> str:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM sop_rules WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    def set_rule(self, key: str, value: str, category: str = "custom"):
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sop_rules (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category, updated_at=excluded.updated_at
            """, (key, value, category, now))
            conn.commit()

    # ── Supervisor Registry API ───────────────────────────────────────────────
    def register_supervisors(self, supervisors: list[str]):
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            for sup in supervisors:
                if sup and str(sup).strip():
                    cur.execute("""
                        INSERT OR IGNORE INTO supervisor_registry (supervisor_name, status, updated_at)
                        VALUES (?, 'active', ?)
                    """, (str(sup).strip(), now))
            conn.commit()

    def get_supervisors_status(self) -> dict[str, str]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT supervisor_name, status FROM supervisor_registry")
            return {row["supervisor_name"]: row["status"] for row in cur.fetchall()}

    def update_supervisor_status(self, supervisor_name: str, status: str):
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE supervisor_registry SET status = ?, updated_at = ? WHERE supervisor_name = ?
            """, (status, now, supervisor_name))
            conn.commit()

    # ── Audit Log API ─────────────────────────────────────────────────────────
    def log_execution(self, original_filename: str, output_filename: str, action_taken: str, rows_affected: int = 0, cols_affected: str = "", reason: str = ""):
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO execution_audit (original_filename, output_filename, action_taken, rows_affected, cols_affected, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (original_filename, output_filename, action_taken, rows_affected, cols_affected, reason, now))
            conn.commit()

    def get_audit_logs(self, limit: int = 50) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM execution_audit ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]
