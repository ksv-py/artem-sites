# Artem Sites — Site Management App (v1)

A mobile-first web app for Artem Interiors & Constructions (Delhi) to run
construction/interior sites from a phone, modelled on the Tasks.Bot Reel:
attendance with photo + location, photo-verified tasks, material requests
(including voice notes) that become purchase tasks, automatic overdue
escalation to the owner, all sites on one panel, and a daily report that
can be shared on WhatsApp.

## What it does

- **Owner dashboard** — all sites on one panel: progress, today's
  attendance, open/overdue task counts, plus a red escalation banner
  listing every overdue task with the site and how late it is.
- **Sites** — create/list sites (residential / commercial / turnkey /
  renovation). Workers are added per site.
- **Attendance** — a supervisor marks each worker Present / Absent /
  Half day, with a photo (phone camera) and GPS location recorded.
  Today's list and a date-wise history are shown.
- **Tasks** — daily work as tasks per site with an assignee and a due
  date/time. Marking a task done **requires a photo** (proof).
- **Material** — a request (item, quantity, needed-by date, optional
  voice note recorded in the browser) becomes a purchase task assigned
  to Mehul (Purchase).
- **Daily report** — pick a date (default today): attendance, tasks
  done with photos, open/overdue tasks, material requests. A
  "Share on WhatsApp" button opens a `wa.me` link with the report
  text prefilled (no WhatsApp API, just a share link).
- **Roles** — pick Owner or Supervisor on the home page. Owner sees
  everything; a supervisor picks their site and only sees that site.

## Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in a browser (or on a phone on the
same network via the machine's IP). The database file `artem.db` is
created on first boot with demo seed data. (On Debian/Ubuntu systems
where pip refuses system-wide installs, use a virtual environment:
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
then `.venv/bin/python app.py`.)

## Deploy on Render

The repo includes `render.yaml` (free plan). Render runs
`pip install -r requirements.txt` then `python app.py`. The app reads
the `PORT` environment variable. Note: on Render's free plan the
SQLite file and uploaded photos live on the instance disk, so data
resets on redeploy. Use a Render persistent disk or a hosted
database before using this for real sites.

## Demo seed data

On first boot the app seeds 4 demo sites (Site A, Site B, Site C,
Site D) and workers Raju, Sunil, Meena, Imran, Pappu, Gopal and
Mehul (Purchase), plus a few demo tasks and today's attendance, so
the dashboard is not empty. Raju supervises Site A. These are demo
names from the reference Reel, not real clients or projects. Delete
`artem.db` and restart to re-seed, or add real sites/workers from
the app (Owner only).

## v1 limitations (deliberate)

- **No login/passwords.** Role is picked on the home page and kept
  in a browser session. Anyone with the link can open it. Add real
  auth (per-supervisor accounts) before giving it to a team.
- **No face recognition.** Attendance uses a camera photo as proof;
  the app does not verify whose face is in the photo.
- **No geofence check.** GPS coordinates are recorded with
  attendance, but the app does not yet check whether the location is
  inside a site radius.
- **No WhatsApp Business API.** The daily report is shared via a
  `wa.me` share link the user taps; nothing is sent automatically.
- **SQLite + local files.** Fine for a small team on one server;
  move to a hosted database and object storage for real use.
- **No push notifications.** Overdue escalation shows on the
  dashboard and in the report; nothing pings the owner.
