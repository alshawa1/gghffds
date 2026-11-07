"""
gui/ai_panel.py
───────────────
AI Agent Panel — A built-in conversational assistant that understands
STC Saudi Arabia's debt collection operations and this system's full logic.

The agent runs locally using a rules-based + pattern-matching engine
(no API key required) and answers questions about:
  - Module logic (errors, contact, neglect, payments, scheduling, etc.)
  - How the system works step by step
  - How to interpret results (إضافة, حذف, تعديل, جدولة مؤكدة, ...)
  - Definition of all columns and KPIs
  - Answering quick stats from the last run

It uses keyword matching against a local knowledge base to give
relevant, contextual Arabic answers.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from typing import Dict, Any, Callable

from gui.styles import (
    ACCENT_BLUE, BG_CARD, BG_DARK,
    FONT_ARABIC_BODY, FONT_ARABIC_SMALL, FONT_ARABIC_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY,
)

# ── Knowledge Base ─────────────────────────────────────────────────────────────

KB: list[tuple[list[str], str]] = [
    # === System Overview ===
    (["نظام", "system", "شو يعمل", "ايه", "بيعمل ايه", "يعمل إيه"],
     "النظام ده بيساعدك تعمل تحليل كامل لعمليات تحصيل الديون في STC السعودية.\n"
     "عندنا 7 مهام رئيسية:\n"
     "1️⃣ أخطاء النظام — كشف البيانات الغلط\n"
     "2️⃣ التوصل وعدم التوصل — مين اتوصلنا بيه\n"
     "3️⃣ الإهمال — مين ملقاوش متابعة\n"
     "4️⃣ السدادات والتسوية — مطابقة مبالغ مهارة × الشركة\n"
     "5️⃣ الجدولة — تصنيف العملاء المجدولين\n"
     "6️⃣ السحب والتدوير — توصية بسحب العملاء أو إدارتهم\n"
     "7️⃣ العملاء المستهدفة — تحديد الأهداف الإيجابية والسلبية"),

    # === Task 4 — Payments ===
    (["اضافه", "إضافة", "إضافه", "addition"],
     "الإضافة: مبلغ السداد في ملف الشركة أكبر من مبلغ مهارة.\n"
     "يعني مهارة ناقصة ومحتاج تضيف المبلغ ده في نظامها.\n"
     "الفرق = الشركة - مهارة → موجب → إضافة ✅"),

    (["مراجعه", "مراجعة", "review"],
     "المراجعة: مبلغ مهارة أكبر من الشركة.\n"
     "يعني في مبلغ زيادة في مهارة محتاج تتفقد سببه.\n"
     "الفرق = الشركة - مهارة → سالب → مراجعة 🔍"),

    (["مطابق", "matched", "مطابق"],
     "مطابق: مبلغ الشركة يساوي مبلغ مهارة تماماً.\n"
     "الفرق = صفر → مطابق ✅\n"
     "مش محتاج أي تعديل."),

    (["حذف", "delete"],
     "حذف: الشركة مبلغها صفر لكن مهارة فيها مبلغ.\n"
     "يعني المبلغ ده مش موجود في الشركة أصلاً → نحذفه من مهارة 🗑️"),

    (["تعديل", "edit", "تعديل"],
     "تعديل: الشركة فيها مبلغ أقل من مهارة.\n"
     "مبلغ التعديل = مهارة + الفرق = قيمة الشركة الصحيحة ✏️\n"
     "يعني بنخلي مهارة تساوي قيمة الشركة."),

    (["مبلغ التعديل", "adjustment amount"],
     "مبلغ التعديل = مهارة + الفرق\n"
     "= مهارة + (الشركة - مهارة)\n"
     "= قيمة الشركة\n"
     "يعني المبلغ الصح اللي المفروض يكون في مهارة بعد التعديل."),

    (["فرق", "الفرق", "difference"],
     "الفرق = الشركة - مهارة\n"
     "لو موجب: الشركة أكبر → إضافة\n"
     "لو صفر: مطابق\n"
     "لو الشركة = 0 ومهارة > 0: حذف\n"
     "لو الشركة > 0 والشركة < مهارة: تعديل"),

    (["sumif", "سامإف", "sumif شرح"],
     "في شيت الإضافة بنعمل SUMIF:\n"
     "بنجمع كل مبالغ سداد الشركة لكل رقم حساب (حتى لو متكرر)\n"
     "بعدين بنحذف التكرارات ونشيل أول صف لكل حساب مع المجموع الكلي.\n"
     "نفس الطريقة بنعملها لمهارة — بعدين نقارن."),

    # === Task 5 — Scheduling ===
    (["جدوله", "جدولة", "scheduling"],
     "الجدولة بتمر بـ3 خطوات:\n"
     "1. نحسب نسبة السداد = سدادات موثقة / مبلغ المديونية\n"
     "2. نحسب نسبة متبقي = متبقي سداد / مبلغ المديونية\n"
     "3. نجيب من سداد مهارة: عدد الدفعات، أول دفعة، آخر دفعة\n"
     "4. نشيل من مش عنده دفعات، أو نسبة سداد > 100، أو نسبة متبقي = 0\n"
     "5. نصنف: جدولة مؤكدة / احتمال / متعثر"),

    (["جدوله مؤكده", "جدولة مؤكدة", "confirmed"],
     "جدولة مؤكدة: آخر دفعة في السنة الحالية (2026) من شهر 10 فأكثر\n"
     "يعني العميل دافع قريب في ربع السنة الأخير ← متابعة نشطة 📌"),

    (["احتمال", "potential", "محتمل"],
     "احتمال: آخر دفعة في السنة الحالية قبل شهر 10\n"
     "أو في السنة الماضية من شهر 10 فأكثر\n"
     "يعني العميل دافع بس مش قريب جداً → احتمال يكمل 🔁"),

    (["متعثر", "defaulted", "متعثر"],
     "متعثر: آخر دفعة قبل السنة الماضية\n"
     "أو في السنة الماضية قبل شهر 10\n"
     "يعني العميل مش بادي علامات نشاط ⚠️"),

    # === Task 7 — Target Customers ===
    (["ايجابي", "إيجابي", "positive"],
     "إيجابي: عميل عنده مؤشرات تدل إنه هيدفع.\n"
     "مثل: وعد بالسداد، أول الشهر، ترتيب سداد، قسط، تسوية.\n"
     "ده العميل اللي المفروض تركز عليه 🌟"),

    (["سلبي", "negative"],
     "سلبي: عميل مش عنده مؤشرات دفع.\n"
     "مثل: لا يرد، مغلق، خارج التغطية، رسالة صوتية.\n"
     "ده العميل اللي صعب التواصل معاه 🔴"),

    # === Task 3 — Neglect ===
    (["اهمال", "إهمال", "neglect", "مهمل"],
     "الإهمال: عميل مش عنده متابعة من أكتر من 7 أيام.\n"
     "بنشوف عمود 'آخر متابعة على العميل'.\n"
     "لو الفرق بالأيام من النهارده > 7 → مهمل 😴\n"
     "لو < 7 → نشط ✅"),

    # === Task 2 — Contact ===
    (["توصل", "التوصل", "contact"],
     "التوصل: عميل اتوصلنا بيه.\n"
     "بنشوف الحالة الرئيسية والملاحظة.\n"
     "لو فيه وعد سداد أو قسط أو تسوية → تم التوصل ✅\n"
     "لو لا يرد أو مغلق → عدم التوصل 📵"),

    # === Task 1 — System Errors ===
    (["خطا", "خطأ", "اخطاء", "أخطاء", "error"],
     "أخطاء النظام بتكشف 4 أنواع:\n"
     "1️⃣ رقم رئيسي فاضي → 'يجب وضع رقم رئيسي'\n"
     "2️⃣ حالة سداد مش منطقية (مسدد وعنده رصيد) → 'خطأ حالة السداد'\n"
     "3️⃣ وعد سداد قديم أو ما فيش → 'يجب تحديث وعد السداد'\n"
     "4️⃣ ملاحظة فاضية أو عامة → 'يجب تحديث الإفادة'"),

    # === Column Definitions ===
    (["مبلغ المديونيه", "مبلغ المديونية", "debt amount"],
     "مبلغ المديونية: المبلغ الأصلي المديون على العميل قبل أي سداد."),

    (["سدادات موثقه", "السدادات الموثقة", "documented payments"],
     "السدادات الموثقة: مجموع المدفوعات الموثقة في النظام حتى الآن."),

    (["متبقي", "متبقي سداد", "remaining"],
     "متبقي سداد موثق: ما تبقى على العميل بعد خصم السدادات الموثقة.\n"
     "= مبلغ المديونية - السدادات الموثقة"),

    (["رقم المديونيه", "رقم المديونية", "debt number"],
     "رقم المديونية: الرقم الفريد لكل ملف مديونية.\n"
     "مختلف عن رقم الحساب — عميل واحد ممكن يكون عنده أكتر من مديونية."),

    (["رقم الحساب", "account number"],
     "رقم الحساب: رقم الحساب التجاري للعميل.\n"
     "بيستخدم كمفتاح للربط بين ملف الشركة وملف مهارة والمحفظة."),

    (["رقم رئيسي", "الرقم الرئيسي", "primary id"],
     "الرقم الرئيسي: رقم هوية أو رقم تعريفي رئيسي للعميل في نظام STC.\n"
     "لو فاضي → خطأ في النظام يجب تصحيحه."),

    # === Files ===
    (["محفظه", "محفظة", "portfolio", "المحفظه الموزعه"],
     "المحفظة الموزعة: ملف الرئيسي اللي فيه كل العملاء المسندين للفريق.\n"
     "فيه اسم العميل، رقم الحساب، رقم المديونية، الحالة، المشرف، المحصل... إلخ"),

    (["سداد مهاره", "سداد مهارة", "maharah payments"],
     "سداد مهارة: ملف يحتوي على كل السدادات المسجلة في نظام مهارة.\n"
     "فيه رقم الحساب، مبلغ السداد، تاريخ السداد، وغيرها."),

    (["سداد الشركه", "سداد الشركة", "company payments"],
     "سداد الشركة: ملف السدادات الرسمية من طرف STC.\n"
     "بيستخدم كمرجع رئيسي لمقارنة ومطابقة مبالغ مهارة."),

    (["وعود السداد", "promise to pay"],
     "وعود السداد: ملف فيه وعود العملاء بالسداد.\n"
     "فيه رقم الحساب، تاريخ الوعد، واللي بيستخدم في الجدولة وأخطاء النظام."),

    # === Output Sheets ===
    (["شيت الاضافه", "شيت الإضافة", "addition sheet"],
     "شيت الإضافة: العملاء اللي السداد في الشركة أكبر من مهارة.\n"
     "المفروض تضيفهم في نظام مهارة.\n"
     "فيه: رقم الحساب، مبلغ الشركة، مبلغ مهارة، الفرق، المشرف، المحصل."),

    (["شيت التسويه", "شيت التسوية", "settlement sheet"],
     "شيت التسوية: بيوضح نوع التسوية لكل عميل (كاملة أو جزئية).\n"
     "تسوية كاملة: متبقي = 0\n"
     "تسوية جزئية: متبقي > 0"),

    (["شيت الحذف والتعديل", "edit delete sheet"],
     "شيت الحذف والتعديل: العملاء اللي في مهارة بس الشركة مختلفة.\n"
     "القرار: مطابق / تعديل / حذف\n"
     "مبلغ التعديل = قيمة الشركة (المبلغ الصح)"),

    # === How to use ===
    (["ازاي", "كيف", "how to", "استخدام", "بشغل"],
     "طريقة الاستخدام:\n"
     "1. من القائمة اختار المهمة اللي عايزها\n"
     "2. رفع الملفات المطلوبة (المحفظة، سداد مهارة، سداد الشركة...)\n"
     "3. اضغط 'تشغيل'\n"
     "4. استنى الـ processing ينتهي\n"
     "5. افتح ملف الإكسل الناتج أو احفظه في مسار تاني"),

    # === General STC context ===
    (["stc", "الاتصالات السعودية", "شركة الاتصالات"],
     "شركة الاتصالات السعودية (STC) هي أكبر شركة اتصالات في السعودية.\n"
     "ملفات الديون التجارية (B2C/B2B) بتتوزع على فرق تحصيل متخصصة.\n"
     "مهارة هي منصة إدارة المهام وتوثيق التحصيل."),

    (["مهاره", "مهارة", "maharah"],
     "مهارة: نظام إدارة العمليات اللي بيستخدمه فريق التحصيل.\n"
     "فيه تسجيل السدادات، المتابعات، وعود السداد، والحالات.\n"
     "النظام ده بيتكامل مع مهارة ويقارن بياناتها مع ملفات الشركة."),

    (["محصل", "collector"],
     "المحصل: الموظف المسؤول عن متابعة العملاء والتواصل معهم.\n"
     "في التقارير بيظهر أداء كل محصل بشكل منفصل."),

    (["مشرف", "supervisor"],
     "المشرف: مسؤول فريق المحصلين.\n"
     "التقارير بتعرض إحصائيات مجمعة لكل مشرف ومحصليه."),
]


def _match_kb(query: str) -> str:
    """Match user query against knowledge base using keyword overlap."""
    query_lower = query.lower().strip()
    best_score = 0
    best_answer = None

    for keywords, answer in KB:
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > best_score:
            best_score = score
            best_answer = answer

    if best_score == 0:
        # Try broader single-word match
        words = query_lower.split()
        for kw_list, answer in KB:
            for kw in kw_list:
                if any(w in kw or kw in w for w in words):
                    return answer
        return None

    return best_answer


def _build_stats_summary(stats: Dict[str, Any]) -> str:
    """Build a readable stats summary from last run."""
    if not stats:
        return "لسه ما تم تشغيل أي مهمة. شغّل مهمة الأول من القائمة."
    lines = ["📊 نتائج آخر تشغيل:"]
    for k, v in stats.items():
        lines.append(f"  • {k}: {v}")
    return "\n".join(lines)


# ── AI Panel Widget ────────────────────────────────────────────────────────────

class AiPanel(tk.Toplevel):
    """Floating AI assistant chat window."""

    AGENT_NAME = "مساعد STC الذكي"
    AGENT_COLOR = "58a6ff"
    USER_COLOR   = "3fb950"

    GREETING = (
        "مرحباً! أنا مساعدك الذكي المتخصص في عمليات تحصيل الديون في STC.\n\n"
        "أقدر أساعدك في:\n"
        "• شرح كيفية عمل أي مهمة في النظام\n"
        "• تفسير النتائج (إضافة، حذف، تعديل، جدولة...)\n"
        "• معنى أي عمود أو مصطلح\n"
        "• عرض ملخص آخر نتائج\n\n"
        "اكتب سؤالك بالعربي 👇"
    )

    def __init__(self, parent, stats: Dict[str, Any]):
        super().__init__(parent)
        self._stats = stats
        self.title(f"🤖 {self.AGENT_NAME}")
        self.configure(bg=BG_DARK)
        self.geometry("520x620")
        self.resizable(True, True)
        self._build()
        self._post_agent(self.GREETING)

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg="#010409", height=50)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)
        hdr.grid_propagate(False)
        tk.Label(hdr, text=f"🤖  {self.AGENT_NAME}",
                 font=FONT_ARABIC_TITLE,
                 bg="#010409", fg="#58a6ff").pack(expand=True)

        # ── Chat area ─────────────────────────────────────────────────────────
        chat_frame = tk.Frame(self, bg=BG_DARK)
        chat_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self._chat = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            font=("Tahoma", 10),
            relief="flat",
            state=tk.DISABLED,
            bd=0,
        )
        self._chat.pack(fill="both", expand=True)
        self._chat.tag_config("agent",  foreground="#58a6ff", font=("Tahoma", 10))
        self._chat.tag_config("user",   foreground="#3fb950", font=("Tahoma", 10, "bold"))
        self._chat.tag_config("label",  foreground="#8b949e", font=("Tahoma", 9))
        self._chat.tag_config("normal", foreground="#c9d1d9", font=("Tahoma", 10))

        # ── Input area ────────────────────────────────────────────────────────
        inp_frame = tk.Frame(self, bg=BG_DARK, padx=10, pady=8)
        inp_frame.grid(row=2, column=0, sticky="ew")
        inp_frame.columnconfigure(0, weight=1)

        self._entry = tk.Entry(
            inp_frame,
            bg=BG_CARD, fg=TEXT_PRIMARY,
            font=("Tahoma", 11),
            relief="flat",
            insertbackground="white",
        )
        self._entry.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0, 8))
        self._entry.bind("<Return>", lambda e: self._on_send())

        tk.Button(
            inp_frame,
            text="إرسال ▶",
            font=FONT_ARABIC_BODY,
            bg=ACCENT_BLUE, fg="white",
            activebackground="#1158c7",
            relief="flat", bd=0,
            padx=14, pady=6,
            cursor="hand2",
            command=self._on_send,
        ).grid(row=0, column=1)

        # Quick action buttons
        btn_row = tk.Frame(self, bg=BG_DARK, padx=10, pady=(0, 8))
        btn_row.grid(row=3, column=0, sticky="ew")
        quick = [
            ("📊 آخر نتائج", "اعرض ملخص آخر النتائج"),
            ("📖 شرح الإضافة", "اشرح لي الإضافة"),
            ("📖 شرح الجدولة", "اشرح لي الجدولة"),
            ("❓ مساعدة", "ازاي أستخدم النظام"),
        ]
        for txt, cmd in quick:
            tk.Button(
                btn_row, text=txt,
                font=("Tahoma", 9),
                bg="#21262d", fg=TEXT_SECONDARY,
                activebackground="#30363d",
                relief="flat", bd=0,
                padx=8, pady=4,
                cursor="hand2",
                command=lambda c=cmd: self._inject(c),
            ).pack(side="left", padx=3)

        self._entry.focus_set()

    def _inject(self, text: str):
        """Inject a quick action into the entry and send."""
        self._entry.delete(0, tk.END)
        self._entry.insert(0, text)
        self._on_send()

    def _on_send(self):
        query = self._entry.get().strip()
        if not query:
            return
        self._entry.delete(0, tk.END)
        self._post_user(query)
        # Process in background so UI stays responsive
        threading.Thread(target=self._process, args=(query,), daemon=True).start()

    def _process(self, query: str):
        """Run the knowledge-base lookup and post the answer."""
        import time
        time.sleep(0.2)   # tiny delay for natural feel

        q_lower = query.lower()

        # Special commands
        if any(w in q_lower for w in ["نتائج", "ملخص", "اعرض", "statistics", "stats"]):
            answer = _build_stats_summary(self._stats)
        else:
            answer = _match_kb(query)
            if answer is None:
                answer = (
                    "لم أجد إجابة محددة لسؤالك.\n"
                    "جرب تسأل عن:\n"
                    "• الإضافة / التعديل / الحذف / مطابق\n"
                    "• الجدولة / الإهمال / التوصل\n"
                    "• معنى عمود معين\n"
                    "• آخر نتائج التشغيل"
                )

        self.after(0, self._post_agent, answer)

    def _post_user(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        self._append(f"\n[{ts}] أنت:\n", "label")
        self._append(text + "\n", "user")

    def _post_agent(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        self._append(f"\n[{ts}] {self.AGENT_NAME}:\n", "label")
        self._append(text + "\n", "agent")

    def _append(self, text: str, tag: str):
        self._chat.config(state=tk.NORMAL)
        self._chat.insert(tk.END, text, tag)
        self._chat.see(tk.END)
        self._chat.config(state=tk.DISABLED)
