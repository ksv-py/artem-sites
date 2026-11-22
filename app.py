"""Artem Interiors & Constructions - Site Management App (v1).

A mobile-first web app for a builder running several sites:
attendance with photo + location, photo-verified tasks, material
requests (incl. voice notes) that become purchase tasks, automatic
overdue escalation, and a daily report shareable on WhatsApp.

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

    # today's attendance (demo, no photo)
    attendance = [
        (0, "Raju", "Present"),
        (0, "Sunil", "Present"),
        (0, "Mehul", "Present"),
        (1, "Meena", "Present"),
        (1, "Imran", "Absent"),
        (2, "Pappu", "Present"),
        (2, "Gopal", "Half day"),
    ]
    for site_idx, name, status in attendance:
        db.execute(
            "INSERT INTO attendance (site_id, worker_id, date, status, recorded_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (site_ids[site_idx], worker_ids[name], today, status, now),
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
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''} late"
    if hours >= 1:
        return f"{hours} hr{'s' if hours != 1 else ''} late"
    return "due now"


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


def site_visible(site_id):
    if session.get("role") == "owner":
        return True
    return session.get("site_id") == int(site_id)


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

    return dict(
        photo_url=photo_url,
        role=session.get("role"),
        my_site_id=session.get("site_id"),
        is_overdue=is_overdue,
        late_text=late_text,
    )


# ---------------------------------------------------------------- routes

@app.route("/")
def index():
    db = get_db()
    sites = db.execute("SELECT * FROM sites ORDER BY id").fetchall()
    return render_template("index.html", sites=sites)


@app.route("/set-role", methods=["POST"])
def set_role():
    role = request.form.get("role")
    if role == "owner":
        session["role"] = "owner"
        session.pop("site_id", None)
        return redirect(url_for("dashboard"))
    if role == "supervisor":
        site_id = request.form.get("site_id")
        if not site_id or not get_site(site_id):
            flash("Please pick your site.")
            return redirect(url_for("index"))
        session["role"] = "supervisor"
        session["site_id"] = int(site_id)
        return redirect(url_for("site_detail", site_id=site_id))
    flash("Please pick a role.")
    return redirect(url_for("index"))


@app.route("/switch-role")
def switch_role():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if session.get("role") != "owner":
        flash("Pick Owner to see all sites.")
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
    if not session.get("role"):
        return redirect(url_for("index"))
    if not site_visible(site_id):
        flash("You can only see your own site.")
        return redirect(url_for("site_detail", site_id=session.get("site_id")))
    site = get_site(site_id)
    if not site:
        flash("Site not found.")
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
        flash("Only the owner can add a site.")
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        typ = request.form.get("type", "Residential")
        if not name:
            flash("Site name is needed.")
            return redirect(url_for("site_new"))
        get_db().execute(
            "INSERT INTO sites (name, location, type, created_at) VALUES (?, ?, ?, ?)",
            (name, location, typ, now_str()))
        get_db().commit()
        flash(f"Site {name} added.")
        return redirect(url_for("dashboard"))
    return render_template("site_new.html")


@app.route("/site/<int:site_id>/workers/add", methods=["POST"])
def worker_add(site_id):
    if not session.get("role") or not site_visible(site_id):
        return redirect(url_for("index"))
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "Helper").strip()
    phone = request.form.get("phone", "").strip()
    if name:
        get_db().execute(
            "INSERT INTO workers (site_id, name, role, phone) VALUES (?, ?, ?, ?)",
            (site_id, name, role, phone))
        get_db().commit()
        flash(f"Worker {name} added to this site.")
    return redirect(url_for("site_detail", site_id=site_id))


@app.route("/attendance/<int:site_id>", methods=["GET", "POST"])
def attendance(site_id):
    if not session.get("role") or not site_visible(site_id):
        return redirect(url_for("index"))
    site = get_site(site_id)
    if not site:
        return redirect(url_for("index"))
    db = get_db()
    if request.method == "POST":
        worker_id = request.form.get("worker_id")
        status = request.form.get("status", "Present")
        lat = request.form.get("lat", "").strip()
        lng = request.form.get("lng", "").strip()
        photo = save_upload(request.files.get("photo"), ALLOWED_IMG)
        if worker_id and status in ("Present", "Absent", "Half day"):
            db.execute(
                "INSERT INTO attendance (site_id, worker_id, date, status, photo_path,"
                " lat, lng, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(site_id, worker_id, date) DO UPDATE SET"
                " status = excluded.status,"
                " photo_path = COALESCE(excluded.photo_path, attendance.photo_path),"
                " lat = excluded.lat, lng = excluded.lng,"
                " recorded_at = excluded.recorded_at",
                (site_id, worker_id, today_str(), status, photo, lat, lng, now_str()))
            db.commit()
            flash("Attendance saved.")
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


@app.route("/attendance/<int:site_id>/history")
def attendance_history(site_id):
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
            flash("Task added.")
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
        flash("Task not found.")
        return redirect(url_for("index"))
    if not session.get("role") or not site_visible(task["site_id"]):
        return redirect(url_for("index"))
    photo = save_upload(request.files.get("photo"), ALLOWED_IMG)
    if not photo:
        flash("A photo is needed to mark a task done. Take a photo of the finished work.")
        return redirect(url_for("tasks", site_id=task["site_id"]))
    db.execute(
        "UPDATE tasks SET status = 'done', photo_path = ?, completed_at = ? WHERE id = ?",
        (photo, now_str(), task_id))
    db.commit()
    flash("Task marked done with photo proof.")
    return redirect(url_for("tasks", site_id=task["site_id"]))


@app.route("/materials/<int:site_id>", methods=["GET", "POST"])
def materials(site_id):
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
            flash(f"Material request for {item} raised. Purchase task given to Mehul.")
        return redirect(url_for("materials", site_id=site_id))
    rows = db.execute(
        "SELECT * FROM material_requests WHERE site_id = ? ORDER BY id DESC",
        (site_id,)).fetchall()
    return render_template("materials.html", site=site, materials=rows,
                           today=today_str())


@app.route("/report")
def report():
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

    lines = [f"Artem Sites - Daily Report {day}",
             f"Attendance: {totals['present']} of {totals['workers']} present",
             f"Tasks done today: {totals['done']}",
             f"Tasks open: {totals['open']} (overdue: {totals['overdue']})", ""]
    for s in sections:
        lines.append(f"{s['site']['name']}: {s['stats']['present']}/{s['stats']['workers']}"
                     f" present, {len(s['done'])} done, {len(s['overdue'])} overdue")
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
