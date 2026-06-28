# JobConnect 🔧

> **Connecting informal workers to opportunities across Zambia.**

A Flask-based web platform that bridges the gap between skilled informal workers and employers — with built-in messaging, ratings, job reports, and a monetization layer ready for production.

---

## Features

### For Workers
- Register with skill category (formal / informal) and NRC verification
- Browse and apply for open jobs
- Receive and reply to messages from employers
- View personal job completion report and skill breakdown
- Earn star ratings from employers after each job
- Boost profile to appear at the top of employer searches

### For Employers
- Post jobs with skill, location, and pay details
- Manage applications — accept, reject, mark complete
- Rate workers after job completion
- Feature job listings to appear at the top of search results
- Freemium plan system (Free / Basic / Pro) with monthly post limits

### Platform
- Internal messaging system with thread support
- Auto-notifications (application received, accepted/rejected, rated)
- Admin revenue dashboard tracking all transactions
- 7% commission recorded on completed job payments
- Dark / light theme toggle

---

## Project Structure

```
JobConnect/
│
├── app.py                  # Main Flask application
│
├── static/
│   ├── style.css           # Full stylesheet
│   ├── background.jpeg     # Hero / auth background image
│   └── uploads/            # User profile pictures (gitignored)
│
├── templates/
│   ├── base.html                  # Shared layout & nav
│   ├── index.html                 # Landing page
│   ├── register.html              # Registration form
│   ├── login.html                 # Login form
│   ├── employee_dashboard.html    # Worker dashboard
│   ├── employer_dashboard.html    # Employer dashboard
│   ├── find_jobs.html             # Job search
│   ├── post_job.html              # Post a job
│   ├── inbox.html                 # Message inbox
│   ├── view_message.html          # Read a message
│   ├── send_message.html          # Compose message
│   ├── rate_worker.html           # Star rating form
│   ├── complete_job.html          # Mark job complete + pay
│   ├── my_report.html             # Worker report page
│   ├── worker_profile.html        # Public worker profile
│   ├── upgrade.html               # Plan upgrade page
│   ├── admin_revenue.html         # Revenue dashboard
│   └── settings.html              # User settings
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/kondwani97/JobConnect.com.git
cd JobConnect.com
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your background image
Place your hero image at:
```
static/background.jpeg
```

### 5. Run the app
```bash
python app.py
```

Open your browser at `http://127.0.0.1:5000`

---

## Monetization Model

| Revenue Stream       | Amount        | Who Pays     |
|----------------------|---------------|--------------|
| Basic Plan           | K150 / month  | Employer     |
| Pro Plan             | K400 / month  | Employer     |
| Featured Job Listing | K50 / 7 days  | Employer     |
| Worker Profile Boost | K30 / month   | Worker       |
| Platform Commission  | 7% of job pay | Employer     |

> Payment gateway (MTN MoMo / Airtel Money) integration coming in next phase.

---

## Legal & Compliance (Zambia)

- **Data Protection Act No. 3 of 2021** — user consent collected at registration; data minimisation enforced
- **Employment Act Cap 268** — platform is a marketplace, not an employer; stated in Terms of Service
- **ECTA** — registration constitutes a binding electronic agreement
- **NRC verification** — collected at registration for identity accountability and AML readiness
- **PACRA number** — required for Corporate Employers

---

## Roadmap

- [x] User registration & login (hashed passwords)
- [x] Job posting, browsing, and applying
- [x] Application lifecycle (pending → accepted → completed)
- [x] Messaging system with threads
- [x] Star ratings and job reports
- [x] Freemium plan gating
- [x] Featured job listings
- [x] Worker profile boost
- [x] Commission tracking
- [x] Admin revenue dashboard
- [ ] Dynamic registration form (NRC, PACRA, skill chips)
- [ ] PostgreSQL database integration
- [ ] Security hardening & authentication (OTP, lockout, HTTPS)
- [ ] MTN MoMo / Airtel Money payment integration
- [ ] SMS job alerts (Africa's Talking)
- [ ] NRC document upload & verification

---

## Tech Stack

- **Backend:** Python / Flask
- **Frontend:** Jinja2 templates, CSS (Barlow font, custom design system)
- **Auth:** Werkzeug password hashing
- **Database:** In-memory (PostgreSQL coming next)
- **Hosting:** TBD (Railway / Render recommended)

---

## Contributing

This project is under active development. Issues and pull requests welcome.

---

