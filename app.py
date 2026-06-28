from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from collections import defaultdict
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "jobconnect_secret_change_in_production")

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─────────────────────────────────────────────
# PLAN DEFINITIONS
# Swap these values out when connecting real payments.
# ─────────────────────────────────────────────
PLANS = {
    "free":  {"name": "Free",    "price": 0,   "post_limit": 3,  "featured_limit": 0},
    "basic": {"name": "Basic",   "price": 150, "post_limit": 10, "featured_limit": 2},
    "pro":   {"name": "Pro",     "price": 400, "post_limit": None,"featured_limit": 10},
}

BOOST_PRICE     = 50    # K50 per featured listing (7 days)
WORKER_BOOST    = 30    # K30/month for worker profile boost
COMMISSION_RATE = 0.07  # 7% platform fee on payments


# ─────────────────────────────────────────────
# IN-MEMORY DATA STORE
# ─────────────────────────────────────────────
users        = []
jobs         = []
applications = []
messages     = []
ratings      = []
payments     = []   # payment / transaction records


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_user(name):
    return next((u for u in users if u['name'] == name), None)


def get_worker_rating(worker_name):
    stars = [r['stars'] for r in ratings if r['worker'] == worker_name]
    return round(sum(stars) / len(stars), 1) if stars else None


def get_job_report(worker_name):
    completed = [a for a in applications
                 if a['worker'] == worker_name and a['status'] == 'completed']
    by_category = defaultdict(int)
    for a in completed:
        by_category[a['job_skill']] += 1
    return {
        "total":       len(completed),
        "by_category": dict(by_category),
        "records":     completed
    }


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


# ── Plan / monetization helpers ───────────────

def get_plan(user):
    """Return the plan dict for a user."""
    return PLANS.get(user.get('plan', 'free'), PLANS['free'])


def posts_this_month(employer_name):
    """Count jobs posted by this employer in the current calendar month."""
    now = datetime.now()
    return sum(
        1 for j in jobs
        if j['employer'] == employer_name
        and j['posted_at'].startswith(now.strftime("%Y-%m"))
    )


def can_post(user):
    """Return (allowed: bool, reason: str)."""
    plan  = get_plan(user)
    limit = plan['post_limit']
    if limit is None:           # Pro — unlimited
        return True, ""
    used = posts_this_month(user['name'])
    if used < limit:
        return True, ""
    return False, (
        f"You've used all {limit} free posts this month. "
        f"Upgrade your plan to post more jobs."
    )


def is_featured(job):
    """True if the job's feature window hasn't expired."""
    until = job.get('featured_until')
    if not until:
        return False
    return datetime.now() <= datetime.strptime(until, "%Y-%m-%d %H:%M")


def record_payment(user_name, amount, ptype, ref=""):
    payments.append({
        "id":        len(payments),
        "user":      user_name,
        "amount":    amount,
        "type":      ptype,       # plan_upgrade | boost | worker_boost | commission
        "ref":       ref,
        "status":    "completed", # completed | pending | failed
        "paid_at":   datetime.now().strftime("%Y-%m-%d %H:%M")
    })


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name'].strip()
        password = request.form['password']
        role     = request.form['role']
        skill    = request.form.get('skill', '').strip()
        location = request.form.get('location', '').strip()

        if get_user(name):
            flash("Username already taken. Please choose another.")
            return redirect(url_for('register'))

        pic      = request.files.get('profile_pic')
        pic_name = ""
        if pic and pic.filename and allowed_file(pic.filename):
            pic_name = f"{name}_{pic.filename}"
            pic.save(os.path.join(UPLOAD_FOLDER, pic_name))

        user = {
            "id":             len(users),
            "name":           name,
            "skill":          skill,
            "location":       location,
            "password":       generate_password_hash(password),
            "role":           role,
            "profile_pic":    pic_name,
            "theme":          "light",
            "bio":            "",
            "phone":          request.form.get('phone', '').strip(),
            "joined":         datetime.now().strftime("%Y-%m-%d"),
            # ── monetization fields ──
            "plan":           "free",          # free | basic | pro
            "plan_expires":   None,            # date string or None
            "boosted":        False,           # worker profile boost
            "boost_expires":  None,
        }
        users.append(user)
        flash("Registration successful. Please login.")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name     = request.form['name'].strip()
        password = request.form['password']
        user     = get_user(name)

        if user and check_password_hash(user['password'], password):
            session['user'] = {k: v for k, v in user.items() if k != 'password'}
            return redirect(url_for('dashboard'))

        flash("Invalid login credentials.")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']

    if user['role'] == 'worker':
        report     = get_job_report(user['name'])
        avg_rating = get_worker_rating(user['name'])
        unread     = sum(1 for m in messages
                         if m['to'] == user['name'] and not m['read'])
        return render_template(
            'employee_dashboard.html',
            user=user,
            report=report,
            avg_rating=avg_rating,
            unread_count=unread,
            worker_boost_price=WORKER_BOOST
        )

    # employer
    my_jobs = [j for j in jobs if j['employer'] == user['name']]
    my_apps = [a for a in applications if a['employer'] == user['name']]
    unread  = sum(1 for m in messages
                  if m['to'] == user['name'] and not m['read'])

    plan      = get_plan(user)
    used      = posts_this_month(user['name'])
    limit     = plan['post_limit']
    allowpost, post_reason = can_post(user)

    return render_template(
        'employer_dashboard.html',
        user=user,
        my_jobs=my_jobs,
        applications=my_apps,
        unread_count=unread,
        plan=plan,
        posts_used=used,
        posts_limit=limit,
        can_post=allowpost,
        post_reason=post_reason,
        plans=PLANS,
        boost_price=BOOST_PRICE,
        is_featured=is_featured   # pass helper so template can call it
    )


# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        live = get_user(session['user']['name'])
        if live:
            live['skill']    = request.form.get('skill',    live['skill'])
            live['location'] = request.form.get('location', live['location'])
            live['theme']    = request.form.get('theme',    'light')
            live['bio']      = request.form.get('bio',      '')
            live['phone']    = request.form.get('phone',    '')
            session['user'].update({
                'skill':    live['skill'],
                'location': live['location'],
                'theme':    live['theme'],
                'bio':      live['bio'],
                'phone':    live['phone'],
            })
            session.modified = True
        flash("Settings updated.")

    return render_template('settings.html', user=session['user'])


# ─────────────────────────────────────────────
# PLAN UPGRADE
# ─────────────────────────────────────────────

@app.route('/upgrade', methods=['GET', 'POST'])
def upgrade():
    """Employer selects and 'pays' for a plan. Payment gateway hooks in here later."""
    if 'user' not in session or session['user']['role'] != 'employer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_plan = request.form.get('plan')
        if new_plan not in PLANS:
            flash("Invalid plan selected.")
            return redirect(url_for('upgrade'))

        live = get_user(session['user']['name'])
        if live:
            live['plan'] = new_plan
            # In production: verify payment receipt before setting plan.
            # For now we simulate immediate activation.
            record_payment(
                live['name'],
                PLANS[new_plan]['price'],
                'plan_upgrade',
                ref=new_plan
            )
            session['user']['plan'] = new_plan
            session.modified = True

        flash(f"Plan upgraded to {PLANS[new_plan]['name']}! "
              f"You now have "
              f"{'unlimited' if PLANS[new_plan]['post_limit'] is None else PLANS[new_plan]['post_limit']}"
              f" posts per month.")
        return redirect(url_for('dashboard'))

    return render_template(
        'upgrade.html',
        plans=PLANS,
        current_plan=session['user'].get('plan', 'free')
    )


# ─────────────────────────────────────────────
# WORKER PROFILE BOOST
# ─────────────────────────────────────────────

@app.route('/boost_profile', methods=['POST'])
def boost_profile():
    """Worker pays to be featured in search results for 30 days."""
    if 'user' not in session or session['user']['role'] != 'worker':
        return redirect(url_for('login'))

    live = get_user(session['user']['name'])
    if live:
        live['boosted']       = True
        live['boost_expires'] = datetime.now().strftime("%Y-%m-%d")  # +30 days in prod
        record_payment(live['name'], WORKER_BOOST, 'worker_boost')
        session['user']['boosted'] = True
        session.modified = True

    flash(f"Profile boosted for 30 days! You now appear at the top of employer searches.")
    return redirect(url_for('dashboard'))


# ─────────────────────────────────────────────
# JOB POSTING
# ─────────────────────────────────────────────

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if 'user' not in session or session['user']['role'] != 'employer':
        flash("Only employers can post jobs.")
        return redirect(url_for('login'))

    allowed, reason = can_post(session['user'])
    if not allowed:
        flash(reason)
        return redirect(url_for('upgrade'))

    if request.method == 'POST':
        job = {
            "id":             len(jobs),
            "employer":       session['user']['name'],
            "skill":          request.form['job_skill'].strip(),
            "desc":           request.form['job_desc'].strip(),
            "location":       request.form.get('job_location', '').strip(),
            "pay":            request.form.get('pay', '').strip(),
            "status":         "open",
            "posted_at":      datetime.now().strftime("%Y-%m-%d %H:%M"),
            "featured":       False,
            "featured_until": None,
        }
        jobs.append(job)
        flash("Job posted successfully.")
        return redirect(url_for('dashboard'))

    plan = get_plan(session['user'])
    return render_template('post_job.html', plan=plan, boost_price=BOOST_PRICE)


# ─────────────────────────────────────────────
# FEATURE A JOB (BOOST)
# ─────────────────────────────────────────────

@app.route('/feature_job/<int:job_id>', methods=['POST'])
def feature_job(job_id):
    """Employer pays to pin a job to the top of listings for 7 days."""
    if 'user' not in session or session['user']['role'] != 'employer':
        return redirect(url_for('login'))

    if job_id >= len(jobs):
        flash("Job not found.")
        return redirect(url_for('dashboard'))

    job = jobs[job_id]
    if job['employer'] != session['user']['name']:
        flash("Unauthorized.")
        return redirect(url_for('dashboard'))

    # In production: verify payment before activating.
    job['featured']       = True
    job['featured_until'] = (
        datetime.now().replace(
            day=min(datetime.now().day + 7, 28)   # simplified +7 days
        ).strftime("%Y-%m-%d %H:%M")
    )
    record_payment(session['user']['name'], BOOST_PRICE, 'boost', ref=str(job_id))
    flash(f"Job '{job['skill']}' is now featured for 7 days!")
    return redirect(url_for('dashboard'))


# ─────────────────────────────────────────────
# FIND JOBS  (featured jobs sort first)
# ─────────────────────────────────────────────

@app.route('/find_jobs', methods=['GET', 'POST'])
def find_jobs():
    if 'user' not in session or session['user']['role'] != 'worker':
        flash("Only workers can browse jobs.")
        return redirect(url_for('login'))

    open_jobs    = [j for j in jobs if j['status'] == 'open']
    skill_filter = ""
    loc_filter   = ""

    if request.method == 'POST':
        skill_filter = request.form.get('skill', '').lower().strip()
        loc_filter   = request.form.get('location', '').lower().strip()
        if skill_filter:
            open_jobs = [j for j in open_jobs if skill_filter in j['skill'].lower()]
        if loc_filter:
            open_jobs = [j for j in open_jobs
                         if loc_filter in j.get('location', '').lower()]

    # Featured jobs float to top
    open_jobs = sorted(open_jobs, key=lambda j: is_featured(j), reverse=True)

    applied_ids = {a['job_id'] for a in applications
                   if a['worker'] == session['user']['name']}

    # Boosted workers appear first in any employer-facing lists
    return render_template(
        'find_jobs.html',
        jobs=open_jobs,
        applied_ids=applied_ids,
        skill_filter=skill_filter,
        loc_filter=loc_filter,
        is_featured=is_featured
    )


# ─────────────────────────────────────────────
# APPLICATIONS
# ─────────────────────────────────────────────

@app.route('/apply/<int:job_id>')
def apply(job_id):
    if 'user' not in session or session['user']['role'] != 'worker':
        return redirect(url_for('login'))

    if job_id >= len(jobs):
        flash("Job not found.")
        return redirect(url_for('find_jobs'))

    job = jobs[job_id]
    already = any(a['job_id'] == job_id and a['worker'] == session['user']['name']
                  for a in applications)
    if already:
        flash("You have already applied for this job.")
        return redirect(url_for('find_jobs'))

    applications.append({
        "id":           len(applications),
        "job_id":       job_id,
        "job_skill":    job['skill'],
        "job_desc":     job['desc'],
        "employer":     job['employer'],
        "worker":       session['user']['name'],
        "status":       "pending",
        "applied_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "completed_at": None,
        "pay_amount":   None,   # filled when employer records payment
    })

    messages.append({
        "id":        len(messages),
        "from":      session['user']['name'],
        "to":        job['employer'],
        "subject":   f"New application for: {job['skill']}",
        "body":      (
            f"{session['user']['name']} has applied for your '{job['skill']}' job posting.\n"
            f"Log in to your dashboard to review and respond."
        ),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "read":      False,
        "thread_id": len(applications) - 1
    })

    flash("Application submitted successfully.")
    return redirect(url_for('find_jobs'))


@app.route('/manage_application/<int:app_id>/<action>')
def manage_application(app_id, action):
    if 'user' not in session or session['user']['role'] != 'employer':
        return redirect(url_for('login'))

    if app_id >= len(applications):
        flash("Application not found.")
        return redirect(url_for('dashboard'))

    app_rec = applications[app_id]
    if app_rec['employer'] != session['user']['name']:
        flash("Unauthorized action.")
        return redirect(url_for('dashboard'))

    if action in ('accept', 'reject'):
        app_rec['status'] = 'accepted' if action == 'accept' else 'rejected'
        messages.append({
            "id":        len(messages),
            "from":      session['user']['name'],
            "to":        app_rec['worker'],
            "subject":   f"Your application was {app_rec['status']}",
            "body":      (
                f"Your application for '{app_rec['job_skill']}' has been "
                f"{'accepted! The employer will be in touch shortly.'
                   if action == 'accept' else 'not taken forward this time.'}"
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read":      False,
            "thread_id": app_id
        })
        flash(f"Application {app_rec['status']}.")

    return redirect(url_for('dashboard'))


@app.route('/complete_job/<int:app_id>', methods=['GET', 'POST'])
def complete_job(app_id):
    """Employer marks job complete and records pay amount (commission calculated)."""
    if 'user' not in session or session['user']['role'] != 'employer':
        return redirect(url_for('login'))

    if app_id >= len(applications):
        flash("Application not found.")
        return redirect(url_for('dashboard'))

    app_rec = applications[app_id]
    if app_rec['employer'] != session['user']['name']:
        flash("Unauthorized action.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        pay_amount = request.form.get('pay_amount', '').strip()
        try:
            pay_amount = float(pay_amount)
        except ValueError:
            pay_amount = 0.0

        commission = round(pay_amount * COMMISSION_RATE, 2)

        app_rec['status']       = 'completed'
        app_rec['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        app_rec['pay_amount']   = pay_amount

        if pay_amount > 0:
            record_payment(
                session['user']['name'],
                commission,
                'commission',
                ref=str(app_id)
            )

        flash(
            f"Job marked complete. "
            f"{'Platform fee: K' + str(commission) + '.' if commission else ''} "
            f"Please rate {app_rec['worker']}."
        )
        return redirect(url_for('rate_worker', app_id=app_id))

    return render_template('complete_job.html', app_rec=app_rec,
                           commission_rate=int(COMMISSION_RATE * 100))


# ─────────────────────────────────────────────
# RATING SYSTEM
# ─────────────────────────────────────────────

@app.route('/rate/<int:app_id>', methods=['GET', 'POST'])
def rate_worker(app_id):
    if 'user' not in session or session['user']['role'] != 'employer':
        return redirect(url_for('login'))

    if app_id >= len(applications):
        flash("Application not found.")
        return redirect(url_for('dashboard'))

    app_rec = applications[app_id]
    if app_rec['employer'] != session['user']['name']:
        flash("Unauthorized action.")
        return redirect(url_for('dashboard'))

    if app_rec['status'] != 'completed':
        flash("You can only rate completed jobs.")
        return redirect(url_for('dashboard'))

    already_rated = any(r['app_id'] == app_id and r['employer'] == session['user']['name']
                        for r in ratings)

    if request.method == 'POST' and not already_rated:
        stars   = max(1, min(5, int(request.form.get('stars', 3))))
        comment = request.form.get('comment', '').strip()

        ratings.append({
            "id":       len(ratings),
            "app_id":   app_id,
            "worker":   app_rec['worker'],
            "employer": session['user']['name'],
            "stars":    stars,
            "comment":  comment,
            "given_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        messages.append({
            "id":        len(messages),
            "from":      session['user']['name'],
            "to":        app_rec['worker'],
            "subject":   "You received a new rating",
            "body":      (
                f"{session['user']['name']} rated your work on '{app_rec['job_skill']}': "
                f"{'★' * stars}{'☆' * (5 - stars)}\n"
                f"Comment: {comment if comment else 'No comment left.'}"
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read":      False,
            "thread_id": app_id
        })
        flash(f"Rating submitted — {stars} star(s) given to {app_rec['worker']}.")
        return redirect(url_for('dashboard'))

    return render_template('rate_worker.html', app_rec=app_rec, already_rated=already_rated)


@app.route('/worker_profile/<n>')
def worker_profile(name):
    worker = get_user(name)
    if not worker or worker['role'] != 'worker':
        flash("Worker not found.")
        return redirect(url_for('index'))

    report         = get_job_report(name)
    avg_rating     = get_worker_rating(name)
    worker_ratings = [r for r in ratings if r['worker'] == name]

    return render_template(
        'worker_profile.html',
        worker=worker,
        report=report,
        avg_rating=avg_rating,
        worker_ratings=worker_ratings
    )


# ─────────────────────────────────────────────
# MESSAGING
# ─────────────────────────────────────────────

@app.route('/messages')
def inbox():
    if 'user' not in session:
        return redirect(url_for('login'))
    name     = session['user']['name']
    received = sorted([m for m in messages if m['to'] == name],
                      key=lambda m: m['timestamp'], reverse=True)
    sent     = sorted([m for m in messages if m['from'] == name],
                      key=lambda m: m['timestamp'], reverse=True)
    return render_template('inbox.html', received=received, sent=sent)


@app.route('/messages/read/<int:msg_id>')
def read_message(msg_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    if msg_id >= len(messages):
        flash("Message not found.")
        return redirect(url_for('inbox'))
    msg = messages[msg_id]
    if msg['to'] != session['user']['name']:
        flash("Unauthorized.")
        return redirect(url_for('inbox'))
    msg['read'] = True
    thread = []
    if msg.get('thread_id') is not None:
        thread = [m for m in messages
                  if m.get('thread_id') == msg['thread_id'] and m['id'] != msg['id']]
    return render_template('view_message.html', msg=msg, thread=thread)


@app.route('/messages/send', methods=['GET', 'POST'])
def send_message():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        recipient = request.form['to'].strip()
        subject   = request.form['subject'].strip()
        body      = request.form['body'].strip()
        thread_id = request.form.get('thread_id', '').strip()
        if not get_user(recipient):
            flash("Recipient not found.")
            return redirect(url_for('send_message'))
        if not body:
            flash("Message body cannot be empty.")
            return redirect(url_for('send_message'))
        messages.append({
            "id":        len(messages),
            "from":      session['user']['name'],
            "to":        recipient,
            "subject":   subject,
            "body":      body,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read":      False,
            "thread_id": int(thread_id) if thread_id.isdigit() else None
        })
        flash("Message sent.")
        return redirect(url_for('inbox'))
    return render_template(
        'send_message.html',
        prefill_to      = request.args.get('to', ''),
        prefill_subject = request.args.get('subject', ''),
        prefill_thread  = request.args.get('thread_id', '')
    )


# ─────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────

@app.route('/my_report')
def my_report():
    if 'user' not in session or session['user']['role'] != 'worker':
        return redirect(url_for('login'))
    name       = session['user']['name']
    report     = get_job_report(name)
    avg_rating = get_worker_rating(name)
    my_ratings = [r for r in ratings if r['worker'] == name]
    return render_template(
        'my_report.html',
        user=session['user'],
        report=report,
        avg_rating=avg_rating,
        my_ratings=my_ratings
    )


# ─────────────────────────────────────────────
# ADMIN — revenue overview (basic, no auth yet)
# ─────────────────────────────────────────────

@app.route('/admin/revenue')
def admin_revenue():
    if 'user' not in session:
        return redirect(url_for('login'))

    total     = sum(p['amount'] for p in payments)
    by_type   = defaultdict(float)
    for p in payments:
        by_type[p['type']] += p['amount']

    return render_template(
        'admin_revenue.html',
        payments=payments,
        total=total,
        by_type=dict(by_type)
    )


# ─────────────────────────────────────────────
# JSON API
# ─────────────────────────────────────────────

@app.route('/api/workers')
def api_workers():
    result = []
    for u in users:
        if u['role'] == 'worker':
            result.append({
                "name":       u['name'],
                "skill":      u['skill'],
                "location":   u['location'],
                "avg_rating": get_worker_rating(u['name']),
                "jobs_done":  get_job_report(u['name'])['total'],
                "boosted":    u.get('boosted', False)
            })
    # Boosted workers first
    result.sort(key=lambda w: w['boosted'], reverse=True)
    return jsonify(result)


@app.route('/api/job_report/<n>')
def api_job_report(name):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_job_report(name))


@app.route('/api/revenue')
def api_revenue():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(payments)


if __name__ == "__main__":
    app.run(debug=True)
