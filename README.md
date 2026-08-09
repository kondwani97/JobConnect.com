# JobConnect

JobConnect is a Flask web app that connects Zambia's skilled tradespeople —
electricians, welders, tailors, drivers, and more — directly with employers
who need them. No agency, no middleman: workers build a profile and rating
history, employers post jobs and hire straight from the platform.

Built as a student project exploring technology for informal-sector and
skilled-trade work in Zambia.

## Features

- **Dual registration** — one flow for workers and employers, with
  role-specific fields (skill/experience for workers, company name for
  employers) and Zambian NRC-format validation.
- **Phone-based login** — no email required, since many informal workers
  don't use one.
- **Job posting & discovery** — employers post jobs by skill, location, pay;
  workers filter and apply in one click.
- **Application pipeline** — pending → accepted/rejected → completed, with
  automatic notifications at every step.
- **Ratings & reviews** — employers rate workers 1–5 stars after job
  completion; ratings roll up into a public profile and a personal work
  report.
- **In-app messaging** — direct threaded messages between workers and
  employers, auto-started when someone applies or gets accepted.
- **JSON API** — `/api/workers` and `/api/jobs` for a future mobile
  front end.

## Tech stack

- **Backend:** Flask 3, Werkzeug (password hashing)
- **Templates:** Jinja2
- **Frontend:** Hand-written CSS design system (no framework/build step),
  vanilla JavaScript for interactivity
- **Storage:** In-memory Python lists (see [Known limitations](#known-limitations))

## Project structure

```
jobconnect/
├── app.py                  # All routes, validation, and business logic
├── requirements.txt
├── .gitignore
├── static/
│   ├── css/
│   │   └── style.css       # Design tokens + components (buttons, cards,
│   │                       #   forms, the "ticket" job/application card)
│   ├── js/
│   │   └── main.js         # Star picker, password toggle, form helpers
│   └── uploads/            # User-uploaded profile pictures (gitignored)
└── templates/
    ├── base.html           # Shared layout: nav, flash messages, footer
    ├── index.html          # Landing page
    ├── register.html       # Worker/employer sign-up
    ├── login.html
    ├── worker_dashboard.html
    ├── employer_dashboard.html
    ├── post_job.html
    ├── browse_workers.html # Employer → search workers
    ├── find_jobs.html      # Worker → search jobs
    ├── complete_job.html
    ├── rate_worker.html
    ├── worker_profile.html
    ├── employer_profile.html
    ├── inbox.html
    ├── view_message.html
    ├── send_message.html
    ├── settings.html
    └── my_report.html      # Worker's personal job/ratings report
```

## Getting started

```bash
# 1. Clone and enter the project
git clone https://github.com/<your-username>/jobconnect.git
cd jobconnect

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Recommended) set a real secret key instead of the built-in fallback
export SECRET_KEY="a-long-random-string"     # Windows: set SECRET_KEY=...

# 5. Run it
python app.py
```

The app runs at `http://127.0.0.1:5000`.

## Known limitations

This is a working prototype, not production-ready. In priority order:

1. **No database.** `users`, `jobs`, `applications`, `messages`, and
   `ratings` are plain Python lists — all data is lost on restart and
   nothing is shared across worker processes. Swapping in SQLite/Postgres
   (e.g. via SQLAlchemy) is the top priority.
2. **`SECRET_KEY` has a hardcoded fallback** (`"jobconnect_secret_2025"`).
   Fine for local dev; the app should refuse to start in production without
   `SECRET_KEY` set in the environment.
3. **No pagination** on `/find_jobs`, `/browse_workers`, or the JSON API —
   fine at demo scale, will need it once listings grow.
4. **File upload hardening** — uploaded profile pictures are only checked
   by extension, not by content/MIME type or size, and filenames are just
   prefixed with the username rather than fully sanitized.
5. **`/inbox/<msg_id>` uses list position as the ID.** Deleting a message
   (if that's ever added) would silently break every link to messages after
   it. Worth switching to a stable UUID or DB primary key alongside the
   database migration.

## Roadmap ideas

- Migrate storage to a real database
- Email/SMS notifications alongside in-app messages
- Search radius / "near me" using device location
- USSD fallback for workers on basic phones (fits the low-connectivity,
  informal-sector context this project targets)
- Admin view for moderating job posts and disputes

## License

Add a license of your choice (MIT is a common default for student/portfolio
projects) before making the repository public.
