"""Artem Interiors & Constructions - Site Management App (v2).

A mobile-first web app for a builder running several sites:
attendance with photo + location, photo-verified tasks, material
requests (incl. voice notes) that become purchase tasks, automatic
overdue escalation, and a daily report shareable on WhatsApp.

v2 adds:
- Hindi / English toggle for the whole UI (session remembers it).
- Three roles: Worker (own attendance + own tasks only), Supervisor
  (everything for their site, incl. adding/editing attendance), Owner
  (everything, all sites).
- Worked-till on every attendance record: Normal (5 PM), 8 PM,
  12 AM (midnight), Overnight.

Stack: Python Flask + SQLite only. No external services.
Run:  pip install -r requirements.txt
      python app.py
"""
import os
import sqlite3
import uuid
from datetime import datetime, date
from urllib.parse import quote

from flask import (
    Flask, g, render_template, request, redirect, url_for,
    session, send_from_directory, flash,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "artem.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "artem-site-app-dev-key")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_IMG = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_AUDIO = {".webm", ".mp3", ".wav", ".ogg", ".m4a", ".mp4"}

WORKED_TILL_OPTIONS = ["Normal (5 PM)", "8 PM", "12 AM (midnight)", "Overnight"]
WORKED_TILL_DEFAULT = "Normal (5 PM)"

# ---------------------------------------------------------------- translations

T = {
    "en": {
        "home_title": "Artem Site Management",
        "lead": "All sites, attendance, tasks, material and daily report in one place.",
        "who_are_you": "Who are you?",
        "owner": "Owner",
        "supervisor": "Supervisor",
        "worker": "Worker",
        "owner_see_all": "Owner — see all sites",
        "supervisor_pick_site": "Supervisor — pick your site",
        "worker_pick": "Worker — pick your site and your name",
        "choose_site": "Choose a site",
        "choose_worker": "Choose your name",
        "open_my_site": "Open my site",
        "go_dashboard": "Go to dashboard",
        "go_my_site": "Go to my site",
        "go_my_page": "Go to my page",
        "signed_in_as": "You are signed in as",
        "sites": "Sites",
        "dashboard": "Dashboard",
        "all_sites_panel": "All Sites — One Panel",
        "needs_attention": "Needs attention",
        "overdue_tasks": "overdue tasks",
        "no_overdue": "No overdue tasks. All sites on track.",
        "tasks_done": "tasks done",
        "today": "Today",
        "workers_present": "workers present",
        "open_tasks": "Open tasks",
        "overdue": "overdue",
        "open_site": "Open site",
        "add_site": "+ Add a site",
        "daily_report": "Daily Report",
        "switch_role": "Switch role",
        "back": "Back",
        "attendance": "Attendance",
        "mark_attendance": "Mark attendance",
        "my_attendance": "My attendance",
        "my_page": "My page",
        "todays_list": "Today's list",
        "present": "Present",
        "absent": "Absent",
        "half_day": "Half day",
        "worked_till": "Worked till",
        "wt_normal": "Normal (5 PM)",
        "wt_8pm": "8 PM",
        "wt_12am": "12 AM (midnight)",
        "wt_overnight": "Overnight",
        "save_attendance": "Save attendance",
        "update_attendance": "Update attendance",
        "edit": "Edit",
        "photo_face": "Photo (face check — opens camera on phone)",
        "location_waiting": "Location: waiting for GPS…",
        "no_one_marked": "No one marked yet today.",
        "see_history": "See history",
        "attendance_history": "Attendance History",
        "no_attendance_day": "No attendance recorded on",
        "present_today": "present today",
        "tasks": "Tasks",
        "add_task": "Add a task",
        "work_to_do": "Work to do",
        "assign_to": "Assign to",
        "unassigned": "Unassigned",
        "due_datetime": "Due date and time",
        "photo_proof_needed": "Photo proof (needed to finish)",
        "mark_done_photo": "Mark done with photo",
        "done": "Done",
        "open": "Open",
        "proof_photo": "proof photo",
        "see_proof_photo": "See proof photo",
        "no_tasks": "No tasks yet for this site.",
        "material": "Material",
        "material_requests": "Material requests",
        "new_material_request": "New material request",
        "item": "Item",
        "quantity": "Quantity",
        "needed_by": "Needed by (date)",
        "voice_note": "Voice note (optional)",
        "raise_request": "Raise request",
        "no_material": "No material requests yet for this site.",
        "workers_on_site": "Workers on this site",
        "add_worker": "+ Add worker",
        "worker_name": "Worker name",
        "role_ph": "Role (mason, painter...)",
        "phone_optional": "Phone (optional)",
        "share_whatsapp": "Share on WhatsApp",
        "tasks_done_today": "tasks done today",
        "tasks_open": "tasks open",
        "tasks_done_today_label": "Tasks done today",
        "material_requested_today": "Material requested today",
        "report_text_label": "Report text (as shared on WhatsApp)",
        "date": "Date",
        "show": "Show",
        "present_count": "present",
        "site_name": "Site name",
        "location_address": "Location / address",
        "type": "Type",
        "save_site": "Save site",
        "add_site_title": "Add a site",
        "my_tasks": "My tasks",
        "no_my_tasks": "No tasks assigned to you.",
        "your_attendance_today": "Your attendance today",
        "not_marked_yet": "Not marked yet.",
        "your_history": "Your past attendance",
        "present_list": "Present",
        "absent_list": "Absent",
        "no_absent": "Everyone is present.",
        "no_present": "No one is present yet.",
        "photo": "photo",
        "location": "location",
        "due": "due",
        "no_date": "no date",
        "purchase": "Purchase",
        "status": "Status",
        "pick_site": "Please pick your site.",
        "pick_role": "Please pick a role.",
        "pick_site_name": "Please pick your site and your name.",
        "pick_owner_dashboard": "Pick Owner to see all sites.",
        "only_own_site": "You can only see your own site.",
        "site_not_found": "Site not found.",
        "owner_only_add_site": "Only the owner can add a site.",
        "site_name_needed": "Site name is needed.",
        "site_added": "Site {name} added.",
        "worker_added": "Worker {name} added to this site.",
        "attendance_saved": "Attendance saved.",
        "attendance_updated": "Attendance updated.",
        "task_added": "Task added.",
        "photo_needed": "A photo is needed to mark a task done. Take a photo of the finished work.",
        "task_done_msg": "Task marked done with photo proof.",
        "task_not_found": "Task not found.",
        "material_raised": "Material request for {item} raised. Purchase task given to Mehul.",
        "not_your_task": "That task is not assigned to you.",
        "workers_only_my": "Workers can only see their own page.",
    },
    "hi": {
        "home_title": "आर्टेम साइट मैनेजमेंट",
        "lead": "सभी साइट, हाज़िरी, काम, सामान और दैनिक रिपोर्ट एक जगह।",
        "who_are_you": "आप कौन हैं?",
        "owner": "मालिक",
        "supervisor": "सुपरवाइज़र",
        "worker": "मज़दूर",
        "owner_see_all": "मालिक — सभी साइट देखें",
        "supervisor_pick_site": "सुपरवाइज़र — अपनी साइट चुनें",
        "worker_pick": "मज़दूर — अपनी साइट और अपना नाम चुनें",
        "choose_site": "साइट चुनें",
        "choose_worker": "अपना नाम चुनें",
        "open_my_site": "मेरी साइट खोलें",
        "go_dashboard": "डैशबोर्ड पर जाएँ",
        "go_my_site": "मेरी साइट पर जाएँ",
        "go_my_page": "मेरे पेज पर जाएँ",
        "signed_in_as": "आप इस रूप में हैं",
        "sites": "साइट",
        "dashboard": "डैशबोर्ड",
        "all_sites_panel": "सभी साइट — एक जगह",
        "needs_attention": "ध्यान दें",
        "overdue_tasks": "देर वाले काम",
        "no_overdue": "कोई देर वाला काम नहीं। सभी साइट ठीक चल रही हैं।",
        "tasks_done": "काम पूरे",
        "today": "आज",
        "workers_present": "मज़दूर उपस्थित",
        "open_tasks": "बाकी काम",
        "overdue": "देर से",
        "open_site": "साइट खोलें",
        "add_site": "+ साइट जोड़ें",
        "daily_report": "दैनिक रिपोर्ट",
        "switch_role": "भूमिका बदलें",
        "back": "वापस",
        "attendance": "हाज़िरी",
        "mark_attendance": "हाज़िरी लगाएँ",
        "my_attendance": "मेरी हाज़िरी",
        "my_page": "मेरा पेज",
        "todays_list": "आज की सूची",
        "present": "उपस्थित",
        "absent": "अनुपस्थित",
        "half_day": "आधा दिन",
        "worked_till": "कब तक काम किया",
        "wt_normal": "सामान्य (शाम 5 बजे)",
        "wt_8pm": "रात 8 बजे",
        "wt_12am": "रात 12 बजे",
        "wt_overnight": "रात भर",
        "save_attendance": "हाज़िरी सहेजें",
        "update_attendance": "हाज़िरी बदलें",
        "edit": "बदलें",
        "photo_face": "फोटो (चेहरा जाँच — फ़ोन पर कैमरा खुलेगा)",
        "location_waiting": "जगह: GPS का इंतज़ार…",
        "no_one_marked": "आज अभी किसी की हाज़िरी नहीं लगी।",
        "see_history": "पिछला देखें",
        "attendance_history": "हाज़िरी का पिछला रिकॉर्ड",
        "no_attendance_day": "इस दिन कोई हाज़िरी नहीं लगी:",
        "present_today": "आज उपस्थित",
        "tasks": "काम",
        "add_task": "काम जोड़ें",
        "work_to_do": "क्या काम करना है",
        "assign_to": "किसको देना है",
        "unassigned": "किसी को नहीं दिया",
        "due_datetime": "कब तक पूरा करना है",
        "photo_proof_needed": "फोटो सबूत (पूरा करने के लिए ज़रूरी)",
        "mark_done_photo": "फोटो के साथ पूरा करें",
        "done": "पूरा हुआ",
        "open": "बाकी",
        "proof_photo": "सबूत फोटो",
        "see_proof_photo": "सबूत फोटो देखें",
        "no_tasks": "इस साइट पर अभी कोई काम नहीं है।",
        "material": "सामान",
        "material_requests": "सामान की माँग",
        "new_material_request": "नई सामान की माँग",
        "item": "सामान",
        "quantity": "मात्रा",
        "needed_by": "कब तक चाहिए (तारीख़)",
        "voice_note": "आवाज़ वाला नोट (अगर चाहें)",
        "raise_request": "माँग भेजें",
        "no_material": "इस साइट पर अभी कोई सामान की माँग नहीं है।",
        "workers_on_site": "इस साइट के मज़दूर",
        "add_worker": "+ मज़दूर जोड़ें",
        "worker_name": "मज़दूर का नाम",
        "role_ph": "काम (मिस्त्री, पेंटर...)",
        "phone_optional": "फ़ोन (अगर हो)",
        "share_whatsapp": "WhatsApp पर भेजें",
        "tasks_done_today": "आज पूरे हुए काम",
        "tasks_open": "बाकी काम",
        "tasks_done_today_label": "आज पूरे हुए काम",
        "material_requested_today": "आज माँगी गई सामान",
        "report_text_label": "रिपोर्ट का टेक्स्ट (WhatsApp पर जैसा भेजा जाएगा)",
        "date": "तारीख़",
        "show": "दिखाएँ",
        "present_count": "उपस्थित",
        "site_name": "साइट का नाम",
        "location_address": "जगह / पता",
        "type": "प्रकार",
        "save_site": "साइट सहेजें",
        "add_site_title": "साइट जोड़ें",
        "my_tasks": "मेरे काम",
        "no_my_tasks": "आपको कोई काम नहीं दिया गया है।",
        "your_attendance_today": "आज आपकी हाज़िरी",
        "not_marked_yet": "अभी नहीं लगी है।",
        "your_history": "आपकी पिछली हाज़िरी",
        "present_list": "उपस्थित",
        "absent_list": "अनुपस्थित",
        "no_absent": "सभी उपस्थित हैं।",
        "no_present": "अभी कोई उपस्थित नहीं है।",
        "photo": "फोटो",
        "location": "जगह",
        "due": "तक",
        "no_date": "तारीख़ नहीं",
        "purchase": "खरीद",
        "status": "स्थिति",
        "pick_site": "कृपया अपनी साइट चुनें।",
        "pick_role": "कृपया अपनी भूमिका चुनें।",
        "pick_site_name": "कृपया अपनी साइट और अपना नाम चुनें।",
        "pick_owner_dashboard": "सभी साइट देखने के लिए मालिक चुनें।",
        "only_own_site": "आप सिर्फ़ अपनी साइट देख सकते हैं।",
        "site_not_found": "साइट नहीं मिली।",
        "owner_only_add_site": "साइट सिर्फ़ मालिक जोड़ सकता है।",
        "site_name_needed": "साइट का नाम ज़रूरी है।",
        "site_added": "साइट {name} जोड़ी गई।",
        "worker_added": "मज़दूर {name} इस साइट पर जोड़ा गया।",
        "attendance_saved": "हाज़िरी सहेजी गई।",
        "attendance_updated": "हाज़िरी बदल दी गई।",
        "task_added": "काम जोड़ा गया।",
        "photo_needed": "काम पूरा करने के लिए फोटो ज़रूरी है। तैयार काम की फोटो लें।",
        "task_done_msg": "काम फोटो के साथ पूरा हुआ।",
        "task_not_found": "काम नहीं मिला।",
        "material_raised": "सामान {item} की माँग भेजी गई। खरीद का काम मेहुल को दिया गया।",
        "not_your_task": "यह काम आपको नहीं दिया गया है।",
        "workers_only_my": "मज़दूर सिर्फ़ अपना पेज देख सकते हैं।",
    },
}


def tr(key, **kw):
    lang = session.get("lang", "en")
    text = T.get(lang, T["en"]).get(key, T["en"].get(key, key))
    return text.format(**kw) if kw else text


def status_text(status):
    lang = session.get("lang", "en")
    mapping = {
        "Present": {"en": "Present", "hi": "उपस्थित"},
        "Absent": {"en": "Absent", "hi": "अनुपस्थित"},
        "Half day": {"en": "Half day", "hi": "आधा दिन"},
    }
    return mapping.get(status, {}).get(lang, status)


def wt_label(value):
    lang = session.get("lang", "en")
    mapping = {
        "Normal (5 PM)": {"en": "Normal (5 PM)", "hi": "सामान्य (शाम 5 बजे)"},
        "8 PM": {"en": "8 PM", "hi": "रात 8 बजे"},
        "12 AM (midnight)": {"en": "12 AM (midnight)", "hi": "रात 12 बजे"},
        "Overnight": {"en": "Overnight", "hi": "रात भर"},
    }
    return mapping.get(value, {}).get(lang, value)


def worked_till_text(value):
    """Short display form: 'till 8 PM' / 'रात 8 बजे तक'."""
    lang = session.get("lang", "en")
    mapping = {
        "Normal (5 PM)": {"en": "till 5 PM", "hi": "शाम 5 बजे तक"},
        "8 PM": {"en": "till 8 PM", "hi": "रात 8 बजे तक"},
        "12 AM (midnight)": {"en": "till 12 AM", "hi": "रात 12 बजे तक"},
        "Overnight": {"en": "Overnight", "hi": "रात भर"},
    }
    return mapping.get(value or WORKED_TILL_DEFAULT, {}).get(lang, value or "")


# ---------------------------------------------------------------- db

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT,
    type TEXT,
    status TEXT DEFAULT 'Active',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    role TEXT,
    phone TEXT,
    is_supervisor INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    worker_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    worked_till TEXT DEFAULT 'Normal (5 PM)',
    photo_path TEXT,
    lat TEXT,
    lng TEXT,
    recorded_at TEXT,
    UNIQUE(site_id, worker_id, date)
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    assigned_to TEXT,
    due_at TEXT,
    status TEXT DEFAULT 'open',
    kind TEXT DEFAULT 'work',
    photo_path TEXT,
    created_at TEXT,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS material_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    item TEXT NOT NULL,
    quantity TEXT,
    due_date TEXT,
    voice_path TEXT,
    status TEXT DEFAULT 'open',
    task_id INTEGER,
    created_at TEXT
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    # v2 migration: worked_till on attendance (live Render DBs from v1
    # do not have this column yet; ALTER keeps their data intact).
    cols = [r[1] for r in db.execute("PRAGMA table_info(attendance)").fetchall()]
    if "worked_till" not in cols:
        db.execute(
            "ALTER TABLE attendance ADD COLUMN worked_till"
            " TEXT DEFAULT 'Normal (5 PM)'")
    db.commit()
    if db.execute("SELECT COUNT(*) FROM sites").fetchone()[0] == 0:
        seed_db(db)


def seed_db(db):
    """Demo seed data. Clearly demo: Site A-D and the named workers
    come from the reference Reel; no real client data is invented."""
    today = date.today().isoformat()
    yesterday = (date.today().fromordinal(date.today().toordinal() - 1)).isoformat()
    tomorrow = (date.today().fromordinal(date.today().toordinal() + 1)).isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sites = [
        ("Site A", "Demo area, Delhi", "Residential"),
        ("Site B", "Demo area, Delhi", "Commercial"),
        ("Site C", "Demo area, Delhi", "Turnkey"),
        ("Site D", "Demo area, Delhi", "Renovation"),
    ]
    site_ids = []
    for name, loc, typ in sites:
        cur = db.execute(
            "INSERT INTO sites (name, location, type, created_at) VALUES (?, ?, ?, ?)",
            (name, loc, typ, now),
        )
        site_ids.append(cur.lastrowid)

    # workers: (site_index, name, role, is_supervisor)
    workers = [
        (0, "Raju", "Supervisor", 1),
        (0, "Sunil", "Mason", 0),
        (0, "Mehul", "Purchase", 0),
        (1, "Meena", "Painter", 0),
        (1, "Imran", "Carpenter", 0),
        (2, "Pappu", "Helper", 0),
        (2, "Gopal", "Mason", 0),
    ]
    worker_ids = {}
    for site_idx, name, role, sup in workers:
        cur = db.execute(
            "INSERT INTO workers (site_id, name, role, is_supervisor) VALUES (?, ?, ?, ?)",
            (site_ids[site_idx], name, role, sup),
        )
        worker_ids[name] = cur.lastrowid

    # today's attendance (demo, no photo): (site_index, name, status, worked_till)
    attendance = [
        (0, "Raju", "Present", "Normal (5 PM)"),
        (0, "Sunil", "Present", "8 PM"),
        (0, "Mehul", "Present", "Normal (5 PM)"),
        (1, "Meena", "Present", "Normal (5 PM)"),
        (1, "Imran", "Absent", "Normal (5 PM)"),
        (2, "Pappu", "Present", "Overnight"),
        (2, "Gopal", "Half day", "8 PM"),
    ]
    for site_idx, name, status, worked_till in attendance:
        db.execute(
            "INSERT INTO attendance (site_id, worker_id, date, status, worked_till,"
            " recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (site_ids[site_idx], worker_ids[name], today, status, worked_till, now),
        )

    # tasks: (site_index, title, assigned_to, due_at, status, kind, photo)
    tasks = [
        (0, "Slab - 3rd floor", "Raju", today + " 18:00", "open", "work", None),
        (0, "Buy cement - 20 bags", "Mehul (Purchase)", yesterday + " 11:00",
         "open", "purchase", None),
        (1, "Paint - living room", "Meena", tomorrow + " 18:00", "open", "work", None),
        (2, "False ceiling - bedroom", "Gopal", today + " 18:00", "open", "work", None),
        (3, "Kitchen tiles fitting", "Pappu", today + " 18:00", "open", "work", None),
        (3, "Site cleaning", "Pappu", today + " 12:00",
         "done", "work", "static/demo-proof.svg"),
    ]
    for site_idx, title, who, due, status, kind, photo in tasks:
        completed = now if status == "done" else None
        db.execute(
            "INSERT INTO tasks (site_id, title, assigned_to, due_at, status, kind,"
            " photo_path, created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (site_ids[site_idx], title, who, due, status, kind, photo, now, completed),
        )
    db.commit()


# ---------------------------------------------------------------- helpers

def today_str():
    return date.today().isoformat()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def parse_due(due_at):
    if not due_at:
        return None
    try:
        return datetime.strptime(due_at, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def is_overdue(task):
    if task["status"] != "open":
        return False
    due = parse_due(task["due_at"])
    return bool(due and due < datetime.now())


def late_text(task):
    due = parse_due(task["due_at"])
    if not due:
        return ""
    delta = datetime.now() - due
    days = delta.days
    hours = delta.seconds // 3600
    lang = session.get("lang", "en")
    if days >= 1:
        if lang == "hi":
            return f"{days} दिन देर"
        return f"{days} day{'s' if days != 1 else ''} late"
    if hours >= 1:
        if lang == "hi":
            return f"{hours} घंटे देर"
        return f"{hours} hr{'s' if hours != 1 else ''} late"
    return "अभी देना है" if lang == "hi" else "due now"


def save_upload(file_storage, allowed):
    """Save an uploaded file under uploads/ and return its stored path."""
    if not file_storage or not file_storage.filename:
        return None
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in allowed:
        return None
    name = uuid.uuid4().hex + ext
    file_storage.save(os.path.join(UPLOAD_DIR, name))
    return "uploads/" + name


def get_site(site_id):
    return get_db().execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()


def my_worker():
    wid = session.get("worker_id")
    if not wid:
        return None
    return get_db().execute("SELECT * FROM workers WHERE id = ?", (wid,)).fetchone()


def site_visible(site_id):
    role = session.get("role")
    if role == "owner":
        return True
    return session.get("site_id") == int(site_id)


def can_edit_attendance(site_id):
    role = session.get("role")
    if role == "owner":
        return True
    if role == "supervisor" and session.get("site_id") == int(site_id):
        return True
    return False


def site_stats(site_id, day=None):
    """Per-site numbers for a day (default today)."""
    db = get_db()
    day = day or today_str()
    workers = db.execute(
        "SELECT COUNT(*) FROM workers WHERE site_id = ?", (site_id,)).fetchone()[0]
    present = db.execute(
        "SELECT COUNT(*) FROM attendance WHERE site_id = ? AND date = ?"
        " AND status IN ('Present', 'Half day')",
        (site_id, day)).fetchone()[0]
    tasks = db.execute(
        "SELECT * FROM tasks WHERE site_id = ?", (site_id,)).fetchall()
    done = sum(1 for t in tasks if t["status"] == "done")
    total = len(tasks)
    open_tasks = [t for t in tasks if t["status"] == "open"]
    overdue = [t for t in open_tasks if is_overdue(t)]
    return {
        "workers": workers,
        "present": present,
        "tasks_total": total,
        "tasks_done": done,
        "tasks_open": len(open_tasks),
        "overdue": len(overdue),
        "progress": round(100 * done / total) if total else 0,
    }


@app.context_processor
def inject_helpers():
    def photo_url(path):
        if not path:
            return None
        if path.startswith("static/"):
            return url_for("static", filename=path[len("static/"):])
        if path.startswith("uploads/"):
            return url_for("uploaded_file", filename=path[len("uploads/"):])
        return path

    lang = session.get("lang", "en")
    return dict(
        photo_url=photo_url,
        role=session.get("role"),
        my_site_id=session.get("site_id"),
        my_worker_id=session.get("worker_id"),
        lang=lang,
        t=T.get(lang, T["en"]),
        status_text=status_text,
        wt_label=wt_label,
        worked_till_text=worked_till_text,
        worked_till_options=WORKED_TILL_OPTIONS,
        is_overdue=is_overdue,
        late_text=late_text,
    )


# ---------------------------------------------------------------- routes

@app.route("/")
def index():
    db = get_db()
    sites = db.execute("SELECT * FROM sites ORDER BY id").fetchall()
    all_workers = db.execute(
        "SELECT * FROM workers ORDER BY site_id, name").fetchall()
    return render_template("index.html", sites=sites, all_workers=all_workers)


@app.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in ("en", "hi"):
        session["lang"] = lang
    nxt = request.args.get("next") or request.referrer or url_for("index")
    if not nxt.startswith("/"):
        nxt = url_for("index")
    return redirect(nxt)


@app.route("/set-role", methods=["POST"])
def set_role():
    role = request.form.get("role")
    if role == "owner":
        session["role"] = "owner"
        session.pop("site_id", None)
        session.pop("worker_id", None)
        return redirect(url_for("dashboard"))
    if role == "supervisor":
        site_id = request.form.get("site_id")
        if not site_id or not get_site(site_id):
            flash(tr("pick_site"))
            return redirect(url_for("index"))
        session["role"] = "supervisor"
        session["site_id"] = int(site_id)
        session.pop("worker_id", None)
        return redirect(url_for("site_detail", site_id=site_id))
    if role == "worker":
        site_id = request.form.get("site_id")
        worker_id = request.form.get("worker_id")
        worker = None
        if site_id and worker_id:
            worker = get_db().execute(
                "SELECT * FROM workers WHERE id = ? AND site_id = ?",
                (worker_id, site_id)).fetchone()
        if not worker:
            flash(tr("pick_site_name"))
            return redirect(url_for("index"))
        session["role"] = "worker"
        session["site_id"] = int(site_id)
        session["worker_id"] = int(worker_id)
        return redirect(url_for("worker_page"))
    flash(tr("pick_role"))
    return redirect(url_for("index"))


@app.route("/switch-role")
def switch_role():
    session.clear()
    return redirect(url_for("index"))


@app.route("/my")
def worker_page():
    if session.get("role") != "worker":
        flash(tr("workers_only_my"))
        return redirect(url_for("index"))
    w = my_worker()
    if not w:
        session.clear()
        return redirect(url_for("index"))
    site = get_site(session.get("site_id"))
    if not site:
        session.clear()
        return redirect(url_for("index"))
    db = get_db()
    today_row = db.execute(
        "SELECT * FROM attendance WHERE site_id = ? AND worker_id = ? AND date = ?",
        (site["id"], w["id"], today_str())).fetchone()
    my_tasks = db.execute(
        "SELECT * FROM tasks WHERE site_id = ? AND (assigned_to = ? OR assigned_to = ?)"
        " ORDER BY CASE WHEN status = 'open' THEN 0 ELSE 1 END, due_at",
        (site["id"], w["name"], w["name"] + " (Purchase)")).fetchall()
    history = db.execute(
        "SELECT * FROM attendance WHERE site_id = ? AND worker_id = ?"
        " ORDER BY date DESC LIMIT 7",
        (site["id"], w["id"])).fetchall()
    return render_template("worker.html", worker=w, site=site,
                           today_row=today_row, my_tasks=my_tasks,
                           history=history, today=today_str())


@app.route("/dashboard")
def dashboard():
    if session.get("role") != "owner":
        flash(tr("pick_owner_dashboard"))
        return redirect(url_for("index"))
    db = get_db()
    sites = db.execute("SELECT * FROM sites ORDER BY id").fetchall()
    site_cards = []
    all_overdue = []
    for site in sites:
        stats = site_stats(site["id"])
        site_cards.append({"site": site, "stats": stats})
        for t in db.execute(
                "SELECT * FROM tasks WHERE site_id = ? AND status = 'open'",
                (site["id"],)).fetchall():
            if is_overdue(t):
                all_overdue.append({"task": t, "site": site})
    all_overdue.sort(key=lambda x: x["task"]["due_at"] or "")
    return render_template("dashboard.html", site_cards=site_cards,
                           overdue=all_overdue)


@app.route("/site/<int:site_id>")
def site_detail(site_id):
    if session.get("role") == "worker":
        return redirect(url_for("worker_page"))
    if not session.get("role"):
        return redirect(url_for("index"))
    if not site_visible(site_id):
        flash(tr("only_own_site"))
        return redirect(url_for("site_detail", site_id=session.get("site_id")))
    site = get_site(site_id)
    if not site:
        flash(tr("site_not_found"))
        return redirect(url_for("index"))
    db = get_db()
    workers = db.execute(
        "SELECT * FROM workers WHERE site_id = ? ORDER BY is_supervisor DESC, name",
        (site_id,)).fetchall()
    today_att = db.execute(
        "SELECT a.*, w.name AS worker_name FROM attendance a"
        " JOIN workers w ON w.id = a.worker_id"
        " WHERE a.site_id = ? AND a.date = ? ORDER BY w.name",
        (site_id, today_str())).fetchall()
    tasks = db.execute(
        "SELECT * FROM tasks WHERE site_id = ? ORDER BY"
        " CASE WHEN status = 'open' THEN 0 ELSE 1 END, due_at",
        (site_id,)).fetchall()
    materials = db.execute(
        "SELECT * FROM material_requests WHERE site_id = ? ORDER BY id DESC LIMIT 10",
        (site_id,)).fetchall()
    return render_template("site.html", site=site, workers=workers,
                           today_att=today_att, tasks=tasks,
                           materials=materials, stats=site_stats(site_id))


@app.route("/site/new", methods=["GET", "POST"])
def site_new():
    if session.get("role") != "owner":
        flash(tr("owner_only_add_site"))
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        typ = request.form.get("type", "Residential")
        if not name:
            flash(tr("site_name_needed"))
            return redirect(url_for("site_new"))
        get_db().execute(
            "INSERT INTO sites (name, location, type, created_at) VALUES (?, ?, ?, ?)",
            (name, location, typ, now_str()))
        get_db().commit()
        flash(tr("site_added", name=name))
        return redirect(url_for("dashboard"))
    return render_template("site_new.html")


@app.route("/site/<int:site_id>/workers/add", methods=["POST"])
def worker_add(site_id):
    if session.get("role") == "worker" or not session.get("role") \
            or not site_visible(site_id):
        return redirect(url_for("index"))
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "Helper").strip()
    phone = request.form.get("phone", "").strip()
    if name:
        get_db().execute(
            "INSERT INTO workers (site_id, name, role, phone) VALUES (?, ?, ?, ?)",
            (site_id, name, role, phone))
        get_db().commit()
        flash(tr("worker_added", name=name))
    return redirect(url_for("site_detail", site_id=site_id))


@app.route("/attendance/<int:site_id>", methods=["GET", "POST"])
def attendance(site_id):
    if session.get("role") == "worker":
        return redirect(url_for("worker_page"))
    if not session.get("role") or not site_visible(site_id):
        return redirect(url_for("index"))
    site = get_site(site_id)
    if not site:
        return redirect(url_for("index"))
    db = get_db()
    if request.method == "POST":
        worker_id = request.form.get("worker_id")
        status = request.form.get("status", "Present")
        worked_till = request.form.get("worked_till", WORKED_TILL_DEFAULT)
        if worked_till not in WORKED_TILL_OPTIONS:
            worked_till = WORKED_TILL_DEFAULT
        lat = request.form.get("lat", "").strip()
        lng = request.form.get("lng", "").strip()
        photo = save_upload(request.files.get("photo"), ALLOWED_IMG)
        worker = None
        if worker_id:
            worker = db.execute(
                "SELECT * FROM workers WHERE id = ? AND site_id = ?",
                (worker_id, site_id)).fetchone()
        if worker and status in ("Present", "Absent", "Half day"):
            db.execute(
                "INSERT INTO attendance (site_id, worker_id, date, status, worked_till,"
                " photo_path, lat, lng, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(site_id, worker_id, date) DO UPDATE SET"
                " status = excluded.status,"
                " worked_till = excluded.worked_till,"
                " photo_path = COALESCE(excluded.photo_path, attendance.photo_path),"
                " lat = excluded.lat, lng = excluded.lng,"
                " recorded_at = excluded.recorded_at",
                (site_id, worker_id, today_str(), status, worked_till, photo,
                 lat, lng, now_str()))
            db.commit()
            flash(tr("attendance_saved"))
        return redirect(url_for("attendance", site_id=site_id))
    workers = db.execute(
        "SELECT * FROM workers WHERE site_id = ? ORDER BY name", (site_id,)).fetchall()
    today_att = db.execute(
        "SELECT a.*, w.name AS worker_name, w.role AS worker_role FROM attendance a"
        " JOIN workers w ON w.id = a.worker_id"
        " WHERE a.site_id = ? AND a.date = ? ORDER BY w.name",
        (site_id, today_str())).fetchall()
    return render_template("attendance.html", site=site, workers=workers,
                           today_att=today_att, today=today_str())


@app.route("/attendance/<int:site_id>/self", methods=["POST"])
def attendance_self(site_id):
    """Worker self check-in: the worker is forced from the session,
    the form cannot mark anyone else."""
    if session.get("role") != "worker" or session.get("site_id") != site_id:
        return redirect(url_for("worker_page"))
    db = get_db()
    worker_id = session.get("worker_id")
    status = request.form.get("status", "Present")
    worked_till = request.form.get("worked_till", WORKED_TILL_DEFAULT)
    if worked_till not in WORKED_TILL_OPTIONS:
        worked_till = WORKED_TILL_DEFAULT
    lat = request.form.get("lat", "").strip()
    lng = request.form.get("lng", "").strip()
    photo = save_upload(request.files.get("photo"), ALLOWED_IMG)
    if status in ("Present", "Absent", "Half day"):
        db.execute(
            "INSERT INTO attendance (site_id, worker_id, date, status, worked_till,"
            " photo_path, lat, lng, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(site_id, worker_id, date) DO UPDATE SET"
            " status = excluded.status,"
            " worked_till = excluded.worked_till,"
            " photo_path = COALESCE(excluded.photo_path, attendance.photo_path),"
            " lat = excluded.lat, lng = excluded.lng,"
            " recorded_at = excluded.recorded_at",
            (site_id, worker_id, today_str(), status, worked_till, photo,
             lat, lng, now_str()))
        db.commit()
        flash(tr("attendance_saved"))
    return redirect(url_for("worker_page"))


@app.route("/attendance/<int:att_id>/edit", methods=["GET", "POST"])
def attendance_edit(att_id):
    db = get_db()
    att = db.execute(
        "SELECT a.*, w.name AS worker_name, w.role AS worker_role FROM attendance a"
        " JOIN workers w ON w.id = a.worker_id WHERE a.id = ?",
        (att_id,)).fetchone()
    if not att:
        flash(tr("site_not_found"))
        return redirect(url_for("index"))
    if not can_edit_attendance(att["site_id"]):
        flash(tr("only_own_site"))
        return redirect(url_for("index"))
    if request.method == "POST":
        status = request.form.get("status", att["status"])
        worked_till = request.form.get("worked_till", att["worked_till"])
        if status not in ("Present", "Absent", "Half day"):
            status = att["status"]
        if worked_till not in WORKED_TILL_OPTIONS:
            worked_till = att["worked_till"] or WORKED_TILL_DEFAULT
        db.execute(
            "UPDATE attendance SET status = ?, worked_till = ?, recorded_at = ?"
            " WHERE id = ?",
            (status, worked_till, now_str(), att_id))
        db.commit()
        flash(tr("attendance_updated"))
        return redirect(url_for("attendance", site_id=att["site_id"]))
    return render_template("attendance_edit.html", att=att,
                           site=get_site(att["site_id"]))


@app.route("/attendance/<int:site_id>/history")
def attendance_history(site_id):
    if session.get("role") == "worker":
        return redirect(url_for("worker_page"))
    if not session.get("role") or not site_visible(site_id):
        return redirect(url_for("index"))
    site = get_site(site_id)
    if not site:
        return redirect(url_for("index"))
    day = request.args.get("date", today_str())
    db = get_db()
    rows = db.execute(
        "SELECT a.*, w.name AS worker_name, w.role AS worker_role FROM attendance a"
        " JOIN workers w ON w.id = a.worker_id"
        " WHERE a.site_id = ? AND a.date = ? ORDER BY w.name",
        (site_id, day)).fetchall()
    return render_template("attendance_history.html", site=site, rows=rows, day=day)


@app.route("/tasks/<int:site_id>", methods=["GET", "POST"])
def tasks(site_id):
    if session.get("role") == "worker":
        return redirect(url_for("worker_page"))
    if not session.get("role") or not site_visible(site_id):
        return redirect(url_for("index"))
    site = get_site(site_id)
    if not site:
        return redirect(url_for("index"))
    db = get_db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        assigned_to = request.form.get("assigned_to", "").strip()
        due = request.form.get("due_at", "").strip().replace("T", " ")
        if title:
            db.execute(
                "INSERT INTO tasks (site_id, title, assigned_to, due_at, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (site_id, title, assigned_to, due, now_str()))
            db.commit()
            flash(tr("task_added"))
        return redirect(url_for("tasks", site_id=site_id))
    rows = db.execute(
        "SELECT * FROM tasks WHERE site_id = ? ORDER BY"
        " CASE WHEN status = 'open' THEN 0 ELSE 1 END, due_at",
        (site_id,)).fetchall()
    workers = db.execute(
        "SELECT * FROM workers WHERE site_id = ? ORDER BY name", (site_id,)).fetchall()
    return render_template("tasks.html", site=site, tasks=rows, workers=workers)


@app.route("/tasks/<int:task_id>/done", methods=["POST"])
def task_done(task_id):
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        flash(tr("task_not_found"))
        return redirect(url_for("index"))
    if session.get("role") == "worker":
        w = my_worker()
        if not w or task["assigned_to"] not in (w["name"], w["name"] + " (Purchase)"):
            flash(tr("not_your_task"))
            return redirect(url_for("worker_page"))
    elif not session.get("role") or not site_visible(task["site_id"]):
        return redirect(url_for("index"))
    photo = save_upload(request.files.get("photo"), ALLOWED_IMG)
    if not photo:
        flash(tr("photo_needed"))
        if session.get("role") == "worker":
            return redirect(url_for("worker_page"))
        return redirect(url_for("tasks", site_id=task["site_id"]))
    db.execute(
        "UPDATE tasks SET status = 'done', photo_path = ?, completed_at = ? WHERE id = ?",
        (photo, now_str(), task_id))
    db.commit()
    flash(tr("task_done_msg"))
    if session.get("role") == "worker":
        return redirect(url_for("worker_page"))
    return redirect(url_for("tasks", site_id=task["site_id"]))


@app.route("/materials/<int:site_id>", methods=["GET", "POST"])
def materials(site_id):
    if session.get("role") == "worker":
        return redirect(url_for("worker_page"))
    if not session.get("role") or not site_visible(site_id):
        return redirect(url_for("index"))
    site = get_site(site_id)
    if not site:
        return redirect(url_for("index"))
    db = get_db()
    if request.method == "POST":
        item = request.form.get("item", "").strip()
        quantity = request.form.get("quantity", "").strip()
        due_date = request.form.get("due_date", "").strip()
        voice = save_upload(request.files.get("voice"), ALLOWED_AUDIO)
        if item:
            due_at = (due_date + " 18:00") if due_date else ""
            cur = db.execute(
                "INSERT INTO tasks (site_id, title, assigned_to, due_at, kind, created_at)"
                " VALUES (?, ?, ?, ?, 'purchase', ?)",
                (site_id, f"Buy {item}" + (f" - {quantity}" if quantity else ""),
                 "Mehul (Purchase)", due_at, now_str()))
            task_id = cur.lastrowid
            db.execute(
                "INSERT INTO material_requests (site_id, item, quantity, due_date,"
                " voice_path, task_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (site_id, item, quantity, due_date, voice, task_id, now_str()))
            db.commit()
            flash(tr("material_raised", item=item))
        return redirect(url_for("materials", site_id=site_id))
    rows = db.execute(
        "SELECT * FROM material_requests WHERE site_id = ? ORDER BY id DESC",
        (site_id,)).fetchall()
    return render_template("materials.html", site=site, materials=rows,
                           today=today_str())


@app.route("/report")
def report():
    if session.get("role") == "worker":
        flash(tr("workers_only_my"))
        return redirect(url_for("worker_page"))
    if not session.get("role"):
        return redirect(url_for("index"))
    day = request.args.get("date", today_str())
    db = get_db()
    if session.get("role") == "owner":
        sites = db.execute("SELECT * FROM sites ORDER BY id").fetchall()
    else:
        sites = db.execute("SELECT * FROM sites WHERE id = ?",
                           (session.get("site_id"),)).fetchall()
    sections = []
    totals = {"present": 0, "workers": 0, "done": 0, "open": 0, "overdue": 0}
    for site in sites:
        stats = site_stats(site["id"], day)
        att = db.execute(
            "SELECT a.*, w.name AS worker_name FROM attendance a"
            " JOIN workers w ON w.id = a.worker_id"
            " WHERE a.site_id = ? AND a.date = ? ORDER BY w.name",
            (site["id"], day)).fetchall()
        done = db.execute(
            "SELECT * FROM tasks WHERE site_id = ? AND status = 'done'"
            " AND substr(completed_at, 1, 10) = ?",
            (site["id"], day)).fetchall()
        open_tasks = db.execute(
            "SELECT * FROM tasks WHERE site_id = ? AND status = 'open'",
            (site["id"],)).fetchall()
        overdue = [t for t in open_tasks if is_overdue(t)]
        mats = db.execute(
            "SELECT * FROM material_requests WHERE site_id = ?"
            " AND substr(created_at, 1, 10) = ?",
            (site["id"], day)).fetchall()
        totals["present"] += stats["present"]
        totals["workers"] += stats["workers"]
        totals["done"] += len(done)
        totals["open"] += len(open_tasks)
        totals["overdue"] += len(overdue)
        sections.append({
            "site": site, "stats": stats, "attendance": att,
            "done": done, "open": open_tasks, "overdue": overdue, "materials": mats,
        })

    lang = session.get("lang", "en")
    if lang == "hi":
        lines = [f"आर्टेम साइट्स - दैनिक रिपोर्ट {day}",
                 f"हाज़िरी: {totals['present']} में से {totals['workers']} उपस्थित",
                 f"आज पूरे हुए काम: {totals['done']}",
                 f"बाकी काम: {totals['open']} (देर से: {totals['overdue']})", ""]
    else:
        lines = [f"Artem Sites - Daily Report {day}",
                 f"Attendance: {totals['present']} of {totals['workers']} present",
                 f"Tasks done today: {totals['done']}",
                 f"Tasks open: {totals['open']} (overdue: {totals['overdue']})", ""]
    for s in sections:
        lines.append(f"{s['site']['name']}: {s['stats']['present']}/{s['stats']['workers']}"
                     f" present, {len(s['done'])} done, {len(s['overdue'])} overdue")
        for a in s["attendance"]:
            lines.append(f"  {a['worker_name']}: {status_text(a['status'])},"
                         f" {worked_till_text(a['worked_till'])}")
        for t in s["done"]:
            lines.append(f"  Done: {t['title']} ({t['assigned_to'] or '-'})")
        for t in s["overdue"]:
            lines.append(f"  OVERDUE: {t['title']} ({late_text(t)})")
        for m in s["materials"]:
            lines.append(f"  Material: {m['item']} {m['quantity'] or ''}")
    report_text = "\n".join(lines)
    wa_link = "https://wa.me/?text=" + quote(report_text)
    return render_template("report.html", day=day, sections=sections,
                           totals=totals, wa_link=wa_link,
                           report_text=report_text)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ---------------------------------------------------------------- main

with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
