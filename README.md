# Artem Sites — Site Management App (v2)

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

## v2: Hindi / English, three roles, worked-till

- **Language button** — "हिन्दी" / "English" in the header on every
  page. It switches the whole UI between English and Hindi and
  remembers the choice for the session. Site and worker names stay
  as they are. Statuses translate too (Present = उपस्थित, Absent =
  अनुपस्थित, Half day = आधा दिन).
- **Three roles** — pick one on the home page:
  - **Worker (मज़दूर)** — picks their site and their own name. They
    can only mark their *own* attendance for today (with photo, GPS
    and worked-till) and see their *own* assigned tasks, which they
    can mark done with a photo. They cannot see the dashboard, other
    sites, other workers' attendance, or the daily report; blocked
    pages send them back to their own page.
  - **Supervisor (सुपरवाइज़र)** — picks their site. They see
    everything for that site: all tasks, and today's attendance split
    into Present and Absent lists. They can add attendance for any
    worker and edit any attendance entry (status and worked-till).
    They cannot see other sites or the owner dashboard.
  - **Owner (मालिक)** — everything across all sites, as in v1, and
    can edit any attendance entry too.
- **Worked-till** — every attendance record has a "worked till"
  field: Normal (5 PM), 8 PM, 12 AM (midnight), or Overnight. It is
  set on the attendance form (worker self check-in and supervisor /
  owner edit) and shown on the attendance list, the history, the
  site page and the daily report (e.g. "Raju — Present, till 8 PM").
  Overnight entries get a purple badge. The database column is added
  with ALTER TABLE if it is missing, so the live Render database
  from v1 keeps working on redeploy (old rows default to
  "Normal (5 PM)").

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

## v2 limitations (deliberate)

- **No login/passwords.** Role is picked on the home page and kept
  in a browser session. Anyone with the link can open it and pick
  any role, including a worker picking someone else's name. Add real
  auth (per-worker accounts / PINs) before giving it to a team.
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
