from flask import (Flask, render_template, request,
                   redirect, url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from collections import defaultdict
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "jobconnect_secret_2025")

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ═══════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════

SKILLS = [
    "Plumber",
    "Electrician",
    "Welder",
    "Carpenter",
    "Painter",
    "Mason / Bricklayer",
    "Mechanic",
    "Gardener",
    "Security Guard",
    "Cleaner / Housekeeper",
    "Driver",
    "Tailor / Seamstress",
    "Barber / Hair Stylist",
    "Cook / Chef",
    "General Labourer",
    "Tiler",
    "Glazier",
    "Roofer",
    "Plaster / Screeder",
    "Solar Installer",
]

EXPERIENCE_LEVELS = ["Entry (0-1 years)", "Mid (2-4 years)", "Senior (5+ years)"]

ZAMBIA_LOCATIONS = [
    "Lusaka", "Kitwe", "Ndola", "Livingstone",
    "Kabwe", "Chipata", "Solwezi", "Mansa",
    "Kasama", "Mongu", "Chingola", "Mufulira",
    "Luanshya", "Kafue", "Choma",
]


# ═══════════════════════════════════════════════
# IN-MEMORY DATA STORE
# Each list maps directly to a future database table.
# ═══════════════════════════════════════════════
users        = []   # all registered users
jobs         = []   # job postings by employers
applications = []   # worker applications to jobs
messages     = []   # messages between workers and employers
ratings      = []   # employer ratings for workers


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════

def get_user(name):
    """Find user by username."""
    return next((u for u in users if u['name'] == name), None)


def get_user_by_phone(phone):
    """Find user by phone number."""
    return next((u for u in users if u.get('phone') == phone), None)


def get_worker_rating(worker_name):
    """
    Calculate average star rating for a worker.
    Returns None if no ratings exist yet.
    """
    worker_ratings = [r['stars'] for r in ratings
                      if r['worker'] == worker_name]
    if not worker_ratings:
        return None
    return round(sum(worker_ratings) / len(worker_ratings), 1)


def get_worker_rating_count(worker_name):
    """Return total number of ratings a worker has received."""
    return sum(1 for r in ratings if r['worker'] == worker_name)


def get_job_report(worker_name):
    """
    Build a job completion summary for a worker.
    Returns total completed, breakdown by skill, and full records.
    """
    completed = [a for a in applications
                 if a['worker'] == worker_name
                 and a['status'] == 'completed']
    by_skill = defaultdict(int)
    for a in completed:
        by_skill[a['job_skill']] += 1
    return {
        "total":    len(completed),
        "by_skill": dict(by_skill),
        "records":  completed,
    }


def get_unread_count(username):
    """Count unread messages for a user."""
    return sum(1 for m in messages
               if m['to'] == username and not m['read'])


def allowed_file(filename):
    """Check if uploaded file has an allowed image extension."""
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower()
            in {'png', 'jpg', 'jpeg', 'gif'})


def validate_nrc(nrc):
    """
    Basic NRC format check for Zambia.
    Format: 123456/78/9
    """
    import re
    return bool(re.match(r'^\d{6}/\d{2}/\d{1}$', nrc.strip()))


def age_from_dob(dob_string):
    """Calculate age in years from a date string (YYYY-MM-DD)."""
    dob = datetime.strptime(dob_string, "%Y-%m-%d")
    return (datetime.now() - dob).days // 365


def nrc_exists(nrc):
    """Check if an NRC number is already registered."""
    return any(u.get('nrc_number') == nrc for u in users)


def phone_exists(phone):
    """Check if a phone number is already registered."""
    return any(u.get('phone') == phone for u in users)


def name_exists(name):
    """Check if a username is already taken."""
    return any(u['name'] == name for u in users)


# ═══════════════════════════════════════════════
# AUTH — REGISTER / LOGIN / LOGOUT
# ═══════════════════════════════════════════════

@app.route('/')
def index():
    """Landing page."""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registration for both workers and employers.
    Workers provide: name, phone, NRC, DOB, skill,
                     experience, location, bio, password.
    Employers provide: name, phone, NRC, DOB,
                       company name (optional), location, password.
    """
    if request.method == 'POST':

        # ── Core fields (everyone) ──
        name          = request.form.get('name', '').strip()
        phone         = request.form.get('phone', '').strip()
        nrc_number    = request.form.get('nrc_number', '').strip()
        date_of_birth = request.form.get('date_of_birth', '').strip()
        location      = request.form.get('location', '').strip()
        password      = request.form.get('password', '')
        confirm_pass  = request.form.get('confirm_password', '')
        role          = request.form.get('role', '')
        consent       = request.form.get('consent')

        # ── Worker specific ──
        skill      = request.form.get('skill', '').strip()
        experience = request.form.get('experience', '').strip()
        bio        = request.form.get('bio', '').strip()

        # ── Employer specific ──
        company_name = request.form.get('company_name', '').strip()

        # ── Profile picture ──
        pic      = request.files.get('profile_pic')
        pic_name = ""

        # ── Validation ──
        errors = []

        if not name:
            errors.append("Full name is required.")
        elif name_exists(name):
            errors.append("Username already taken.")

        if not phone:
            errors.append("Phone number is required.")
        elif phone_exists(phone):
            errors.append("Phone number already registered.")

        if not nrc_number:
            errors.append("NRC number is required.")
        elif not validate_nrc(nrc_number):
            errors.append("Invalid NRC format. Use: 123456/78/9")
        elif nrc_exists(nrc_number):
            errors.append("NRC number already registered.")

        if not date_of_birth:
            errors.append("Date of birth is required.")
        else:
            try:
                age = age_from_dob(date_of_birth)
                if age < 18:
                    errors.append("You must be 18 or older to register.")
            except ValueError:
                errors.append("Invalid date of birth.")

        if not location:
            errors.append("Location is required.")

        if not role or role not in ('worker', 'employer'):
            errors.append("Please select a role.")

        if role == 'worker' and not skill:
            errors.append("Please select your skill.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        elif password != confirm_pass:
            errors.append("Passwords do not match.")

        if not consent:
            errors.append("You must agree to the Terms of Service.")

        if errors:
            for error in errors:
                flash(error)
            return render_template(
                'register.html',
                skills=SKILLS,
                experience_levels=EXPERIENCE_LEVELS,
                locations=ZAMBIA_LOCATIONS,
                form=request.form
            )

        # ── Save profile picture ──
        if pic and pic.filename and allowed_file(pic.filename):
            pic_name = f"{name}_{pic.filename}"
            pic.save(os.path.join(UPLOAD_FOLDER, pic_name))

        # ── Create user record ──
        user = {
            "id":            len(users),
            "name":          name,
            "phone":         phone,
            "nrc_number":    nrc_number,
            "date_of_birth": date_of_birth,
            "location":      location,
            "password":      generate_password_hash(password),
            "role":          role,
            "profile_pic":   pic_name,
            "bio":           bio,
            "theme":         "light",
            "joined":        datetime.now().strftime("%Y-%m-%d"),
            # Worker fields
            "skill":         skill      if role == 'worker'   else None,
            "experience":    experience if role == 'worker'   else None,
            # Employer fields
            "company_name":  company_name if role == 'employer' else None,
        }
        users.append(user)
        flash("Registration successful! Please log in.")
        return redirect(url_for('login'))

    return render_template(
        'register.html',
        skills=SKILLS,
        experience_levels=EXPERIENCE_LEVELS,
        locations=ZAMBIA_LOCATIONS,
        form={}
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login using phone number and password.
    Phone number is used as the unique identifier
    since most informal workers may not have email.
    """
    if request.method == 'POST':
        phone    = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        user = get_user_by_phone(phone)

        if user and check_password_hash(user['password'], password):
            # Store session — never include password hash
            session['user'] = {k: v for k, v in user.items()
                               if k != 'password'}
            flash(f"Welcome back, {user['name']}!")
            return redirect(url_for('dashboard'))

        flash("Invalid phone number or password.")
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Clear session and redirect to home."""
    session.clear()
    return redirect(url_for('index'))


# ═══════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════

@app.route('/dashboard')
def dashboard():
    """
    Route to the correct dashboard based on user role.
    Workers see their job history, ratings, and job feed.
    Employers see their posted jobs and applications received.
    """
    if 'user' not in session:
        return redirect(url_for('login'))

    user   = session['user']
    unread = get_unread_count(user['name'])

    if user['role'] == 'worker':
        report     = get_job_report(user['name'])
        avg_rating = get_worker_rating(user['name'])
        rating_count = get_worker_rating_count(user['name'])

        # Recent open jobs matching worker's skill
        matching_jobs = [
            j for j in jobs
            if j['status'] == 'open'
            and j['skill'].lower() == (user.get('skill') or '').lower()
        ][:5]

        # Worker's own applications
        my_applications = [
            a for a in applications
            if a['worker'] == user['name']
        ]

        return render_template(
            'worker_dashboard.html',
            user=user,
            report=report,
            avg_rating=avg_rating,
            rating_count=rating_count,
            unread_count=unread,
            matching_jobs=matching_jobs,
            my_applications=my_applications,
        )

    # ── Employer dashboard ──
    my_jobs = [j for j in jobs
               if j['employer'] == user['name']]

    my_applications = [
        a for a in applications
        if a['employer'] == user['name']
    ]

    # Group applications by job for easy display
    apps_by_job = defaultdict(list)
    for a in my_applications:
        apps_by_job[a['job_id']].append(a)

    return render_template(
        'employer_dashboard.html',
        user=user,
        my_jobs=my_jobs,
        my_applications=my_applications,
        apps_by_job=dict(apps_by_job),
        unread_count=unread,
    )


# ═══════════════════════════════════════════════
# JOBS — POST, BROWSE, APPLY
# ═══════════════════════════════════════════════

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    """
    Employers post a job with skill required,
    location, description, and pay.
    """
    if 'user' not in session or session['user']['role'] != 'employer':
        flash("Only employers can post jobs.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        skill    = request.form.get('skill', '').strip()
        location = request.form.get('location', '').strip()
        desc     = request.form.get('description', '').strip()
        pay      = request.form.get('pay', '').strip()

        if not skill or not location or not desc:
            flash("Skill, location and description are required.")
            return render_template(
                'post_job.html',
                skills=SKILLS,
                locations=ZAMBIA_LOCATIONS,
                form=request.form
            )

        job = {
            "id":        len(jobs),
            "employer":  session['user']['name'],
            "skill":     skill,
            "location":  location,
            "desc":      desc,
            "pay":       pay,
            "status":    "open",
            "posted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        jobs.append(job)
        flash("Job posted successfully.")
        return redirect(url_for('dashboard'))

    return render_template(
        'post_job.html',
        skills=SKILLS,
        locations=ZAMBIA_LOCATIONS,
        form={}
    )


@app.route('/browse_workers', methods=['GET', 'POST'])
def browse_workers():
    """
    Employers search for workers by skill and location.
    Results show worker name, skill, experience,
    location, rating and completed jobs.
    """
    if 'user' not in session or session['user']['role'] != 'employer':
        flash("Only employers can browse workers.")
        return redirect(url_for('login'))

    worker_list  = [u for u in users if u['role'] == 'worker']
    skill_filter = request.form.get('skill', '').strip()
    loc_filter   = request.form.get('location', '').strip()

    if request.method == 'POST':
        if skill_filter:
            worker_list = [w for w in worker_list
                           if skill_filter.lower() in w['skill'].lower()]
        if loc_filter:
            worker_list = [w for w in worker_list
                           if loc_filter.lower() in w['location'].lower()]

    # Attach rating and job count to each worker
    enriched = []
    for w in worker_list:
        enriched.append({
            **w,
            "avg_rating":   get_worker_rating(w['name']),
            "rating_count": get_worker_rating_count(w['name']),
            "jobs_done":    get_job_report(w['name'])['total'],
        })

    # Sort: highest rated first, then most jobs done
    enriched.sort(
        key=lambda w: (w['avg_rating'] or 0, w['jobs_done']),
        reverse=True
    )

    return render_template(
        'browse_workers.html',
        workers=enriched,
        skills=SKILLS,
        locations=ZAMBIA_LOCATIONS,
        skill_filter=skill_filter,
        loc_filter=loc_filter,
    )


@app.route('/find_jobs', methods=['GET', 'POST'])
def find_jobs():
    """
    Workers browse open jobs.
    Can filter by skill and location.
    Shows which jobs they have already applied to.
    """
    if 'user' not in session or session['user']['role'] != 'worker':
        flash("Only workers can browse jobs.")
        return redirect(url_for('login'))

    open_jobs    = [j for j in jobs if j['status'] == 'open']
    skill_filter = request.form.get('skill', '').strip()
    loc_filter   = request.form.get('location', '').strip()

    if request.method == 'POST':
        if skill_filter:
            open_jobs = [j for j in open_jobs
                         if skill_filter.lower() in j['skill'].lower()]
        if loc_filter:
            open_jobs = [j for j in open_jobs
                         if loc_filter.lower() in j['location'].lower()]

    # Most recent first
    open_jobs = sorted(open_jobs,
                       key=lambda j: j['posted_at'],
                       reverse=True)

    applied_ids = {
        a['job_id'] for a in applications
        if a['worker'] == session['user']['name']
    }

    return render_template(
        'find_jobs.html',
        jobs=open_jobs,
        applied_ids=applied_ids,
        skill_filter=skill_filter,
        loc_filter=loc_filter,
        skills=SKILLS,
        locations=ZAMBIA_LOCATIONS,
    )


@app.route('/apply/<int:job_id>')
def apply(job_id):
    """
    Worker applies for a job.
    Prevents duplicate applications.
    Sends auto-message to employer on application.
    """
    if 'user' not in session or session['user']['role'] != 'worker':
        return redirect(url_for('login'))

    if job_id >= len(jobs):
        flash("Job not found.")
        return redirect(url_for('find_jobs'))

    job = jobs[job_id]

    if job['status'] != 'open':
        flash("This job is no longer available.")
        return redirect(url_for('find_jobs'))

    already_applied = any(
        a['job_id'] == job_id
        and a['worker'] == session['user']['name']
        for a in applications
    )
    if already_applied:
        flash("You have already applied for this job.")
        return redirect(url_for('find_jobs'))

    applications.append({
        "id":           len(applications),
        "job_id":       job_id,
        "job_skill":    job['skill'],
        "job_location": job['location'],
        "job_desc":     job['desc'],
        "employer":     job['employer'],
        "worker":       session['user']['name'],
        "worker_phone": session['user'].get('phone', ''),
        "status":       "pending",
        "applied_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "completed_at": None,
        "pay_amount":   None,
    })

    # Notify employer
    messages.append({
        "id":        len(messages),
        "from":      session['user']['name'],
        "to":        job['employer'],
        "subject":   f"New application — {job['skill']}",
        "body":      (
            f"{session['user']['name']} has applied for your "
            f"'{job['skill']}' job in {job['location']}.\n\n"
            f"Worker details:\n"
            f"Phone: {session['user'].get('phone', 'N/A')}\n"
            f"Experience: {session['user'].get('experience', 'N/A')}\n"
            f"Location: {session['user'].get('location', 'N/A')}\n\n"
            f"Log in to accept or reject this application."
        ),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "read":      False,
        "thread_id": len(applications) - 1,
    })

    flash("Application submitted! The employer will be notified.")
    return redirect(url_for('find_jobs'))


# ═══════════════════════════════════════════════
# APPLICATIONS MANAGEMENT
# ═══════════════════════════════════════════════

@app.route('/application/<int:app_id>/<action>')
def manage_application(app_id, action):
    """
    Employer accepts or rejects a worker application.
    On acceptance, worker receives notification with
    employer's phone number for direct contact.
    """
    if 'user' not in session or session['user']['role'] != 'employer':
        return redirect(url_for('login'))

    if app_id >= len(applications):
        flash("Application not found.")
        return redirect(url_for('dashboard'))

    app_rec = applications[app_id]

    if app_rec['employer'] != session['user']['name']:
        flash("Unauthorized.")
        return redirect(url_for('dashboard'))

    if action == 'accept':
        app_rec['status'] = 'accepted'

        # Notify worker with employer contact details
        messages.append({
            "id":        len(messages),
            "from":      session['user']['name'],
            "to":        app_rec['worker'],
            "subject":   f"Application accepted — {app_rec['job_skill']}",
            "body":      (
                f"Great news! Your application for "
                f"'{app_rec['job_skill']}' in "
                f"{app_rec['job_location']} has been accepted.\n\n"
                f"Employer contact details:\n"
                f"Name: {session['user']['name']}\n"
                f"Phone: {session['user'].get('phone', 'N/A')}\n"
                f"{'Company: ' + session['user']['company_name'] if session['user'].get('company_name') else ''}\n\n"
                f"Please get in touch to confirm the start date and details."
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read":      False,
            "thread_id": app_id,
        })
        flash(f"Application accepted. {app_rec['worker']} has been notified.")

    elif action == 'reject':
        app_rec['status'] = 'rejected'

        # Notify worker of rejection
        messages.append({
            "id":        len(messages),
            "from":      session['user']['name'],
            "to":        app_rec['worker'],
            "subject":   f"Application update — {app_rec['job_skill']}",
            "body":      (
                f"Thank you for your interest in the "
                f"'{app_rec['job_skill']}' position.\n"
                f"Unfortunately we have decided not to proceed "
                f"with your application at this time.\n"
                f"We wish you the best in your job search."
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read":      False,
            "thread_id": app_id,
        })
        flash("Application rejected. Worker has been notified.")

    return redirect(url_for('dashboard'))


@app.route('/complete/<int:app_id>', methods=['GET', 'POST'])
def complete_job(app_id):
    """
    Employer marks a job as completed.
    Records the amount paid to the worker.
    Redirects to rating page after completion.
    """
    if 'user' not in session or session['user']['role'] != 'employer':
        return redirect(url_for('login'))

    if app_id >= len(applications):
        flash("Application not found.")
        return redirect(url_for('dashboard'))

    app_rec = applications[app_id]

    if app_rec['employer'] != session['user']['name']:
        flash("Unauthorized.")
        return redirect(url_for('dashboard'))

    if app_rec['status'] != 'accepted':
        flash("You can only complete accepted jobs.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            pay_amount = float(request.form.get('pay_amount', 0))
        except ValueError:
            pay_amount = 0.0

        app_rec['status']       = 'completed'
        app_rec['pay_amount']   = pay_amount
        app_rec['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Notify worker
        messages.append({
            "id":        len(messages),
            "from":      session['user']['name'],
            "to":        app_rec['worker'],
            "subject":   f"Job completed — {app_rec['job_skill']}",
            "body":      (
                f"Your job '{app_rec['job_skill']}' has been "
                f"marked as completed by {session['user']['name']}.\n"
                f"Amount paid: K{pay_amount:,.2f}\n\n"
                f"Thank you for your hard work!"
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read":      False,
            "thread_id": app_id,
        })

        flash("Job marked as complete. Please rate the worker.")
        return redirect(url_for('rate_worker', app_id=app_id))

    return render_template('complete_job.html', app_rec=app_rec)


# ═══════════════════════════════════════════════
# RATINGS
# ═══════════════════════════════════════════════

@app.route('/rate/<int:app_id>', methods=['GET', 'POST'])
def rate_worker(app_id):
    """
    Employer rates a worker after job completion.
    1-5 stars with an optional written comment.
    Each job can only be rated once.
    """
    if 'user' not in session or session['user']['role'] != 'employer':
        return redirect(url_for('login'))

    if app_id >= len(applications):
        flash("Application not found.")
        return redirect(url_for('dashboard'))

    app_rec = applications[app_id]

    if app_rec['employer'] != session['user']['name']:
        flash("Unauthorized.")
        return redirect(url_for('dashboard'))

    if app_rec['status'] != 'completed':
        flash("You can only rate completed jobs.")
        return redirect(url_for('dashboard'))

    already_rated = any(
        r['app_id'] == app_id
        for r in ratings
    )

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
            "given_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })

        # Notify worker of new rating
        messages.append({
            "id":        len(messages),
            "from":      session['user']['name'],
            "to":        app_rec['worker'],
            "subject":   "You received a new rating",
            "body":      (
                f"{session['user']['name']} rated your work on "
                f"'{app_rec['job_skill']}':\n"
                f"{'★' * stars}{'☆' * (5 - stars)} ({stars}/5)\n"
                f"{'Comment: ' + comment if comment else ''}"
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read":      False,
            "thread_id": app_id,
        })

        flash(f"Thank you! You gave {app_rec['worker']} {stars} star(s).")
        return redirect(url_for('dashboard'))

    return render_template(
        'rate_worker.html',
        app_rec=app_rec,
        already_rated=already_rated
    )


# ═══════════════════════════════════════════════
# PROFILES
# ═══════════════════════════════════════════════

@app.route('/worker/<name>')
def worker_profile(name):
    """
    Public profile page for a worker.
    Shows skill, experience, location, rating,
    completed jobs, and reviews.
    Employers can see the worker's phone number
    and send a direct message.
    """
    worker = get_user(name)
    if not worker or worker['role'] != 'worker':
        flash("Worker not found.")
        return redirect(url_for('index'))

    report         = get_job_report(name)
    avg_rating     = get_worker_rating(name)
    rating_count   = get_worker_rating_count(name)
    worker_ratings = [r for r in ratings if r['worker'] == name]

    return render_template(
        'worker_profile.html',
        worker=worker,
        report=report,
        avg_rating=avg_rating,
        rating_count=rating_count,
        worker_ratings=worker_ratings,
        viewer=session.get('user'),
    )


@app.route('/employer/<name>')
def employer_profile(name):
    """
    Public profile page for an employer.
    Shows company name, location, and jobs posted.
    """
    employer = get_user(name)
    if not employer or employer['role'] != 'employer':
        flash("Employer not found.")
        return redirect(url_for('index'))

    employer_jobs = [j for j in jobs if j['employer'] == name]

    return render_template(
        'employer_profile.html',
        employer=employer,
        employer_jobs=employer_jobs,
        viewer=session.get('user'),
    )


# ═══════════════════════════════════════════════
# MESSAGING
# ═══════════════════════════════════════════════

@app.route('/inbox')
def inbox():
    """
    Show all received and sent messages for the
    logged-in user. Received messages sorted newest first.
    """
    if 'user' not in session:
        return redirect(url_for('login'))

    name     = session['user']['name']
    received = sorted(
        [m for m in messages if m['to'] == name],
        key=lambda m: m['timestamp'],
        reverse=True
    )
    sent = sorted(
        [m for m in messages if m['from'] == name],
        key=lambda m: m['timestamp'],
        reverse=True
    )
    return render_template('inbox.html', received=received, sent=sent)


@app.route('/inbox/<int:msg_id>')
def read_message(msg_id):
    """
    Open and read a single message.
    Marks it as read. Shows thread if linked.
    """
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

    # Load thread messages
    thread = []
    if msg.get('thread_id') is not None:
        thread = [
            m for m in messages
            if m.get('thread_id') == msg['thread_id']
            and m['id'] != msg['id']
        ]

    return render_template('view_message.html', msg=msg, thread=thread)


@app.route('/message/send', methods=['GET', 'POST'])
def send_message():
    """
    Compose and send a message to another user.
    Pre-fills recipient, subject, and thread_id
    when replying or messaging from a profile.
    """
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        to        = request.form.get('to', '').strip()
        subject   = request.form.get('subject', '').strip()
        body      = request.form.get('body', '').strip()
        thread_id = request.form.get('thread_id', '').strip()

        if not get_user(to):
            flash("Recipient not found.")
            return redirect(url_for('send_message'))

        if not body:
            flash("Message cannot be empty.")
            return redirect(url_for('send_message'))

        messages.append({
            "id":        len(messages),
            "from":      session['user']['name'],
            "to":        to,
            "subject":   subject or "No subject",
            "body":      body,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read":      False,
            "thread_id": int(thread_id) if thread_id.isdigit() else None,
        })

        flash("Message sent.")
        return redirect(url_for('inbox'))

    return render_template(
        'send_message.html',
        prefill_to      = request.args.get('to', ''),
        prefill_subject = request.args.get('subject', ''),
        prefill_thread  = request.args.get('thread_id', ''),
    )


# ═══════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """
    User can update location, bio, theme.
    Workers can also update their experience level.
    """
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        live = get_user(session['user']['name'])
        if live:
            live['location']   = request.form.get('location', live['location'])
            live['bio']        = request.form.get('bio', '')
            live['theme']      = request.form.get('theme', 'light')
            if live['role'] == 'worker':
                live['experience'] = request.form.get('experience',
                                                       live.get('experience', ''))

            session['user'].update({
                'location':   live['location'],
                'bio':        live['bio'],
                'theme':      live['theme'],
                'experience': live.get('experience'),
            })
            session.modified = True
        flash("Settings updated.")

    return render_template(
        'settings.html',
        user=session['user'],
        locations=ZAMBIA_LOCATIONS,
        experience_levels=EXPERIENCE_LEVELS,
    )


# ═══════════════════════════════════════════════
# WORKER REPORT
# ═══════════════════════════════════════════════

@app.route('/my_report')
def my_report():
    """
    Worker's personal report page.
    Shows total jobs, breakdown by skill,
    average rating, and all reviews received.
    """
    if 'user' not in session or session['user']['role'] != 'worker':
        return redirect(url_for('login'))

    name         = session['user']['name']
    report       = get_job_report(name)
    avg_rating   = get_worker_rating(name)
    rating_count = get_worker_rating_count(name)
    my_ratings   = [r for r in ratings if r['worker'] == name]

    return render_template(
        'my_report.html',
        user=session['user'],
        report=report,
        avg_rating=avg_rating,
        rating_count=rating_count,
        my_ratings=my_ratings,
    )


# ═══════════════════════════════════════════════
# JSON API  (for future mobile app / frontend)
# ═══════════════════════════════════════════════

@app.route('/api/workers')
def api_workers():
    """Return all workers with ratings as JSON."""
    result = []
    for u in users:
        if u['role'] == 'worker':
            result.append({
                "name":         u['name'],
                "skill":        u.get('skill'),
                "experience":   u.get('experience'),
                "location":     u.get('location'),
                "avg_rating":   get_worker_rating(u['name']),
                "rating_count": get_worker_rating_count(u['name']),
                "jobs_done":    get_job_report(u['name'])['total'],
            })
    result.sort(key=lambda w: (w['avg_rating'] or 0), reverse=True)
    return jsonify(result)


@app.route('/api/jobs')
def api_jobs():
    """Return all open jobs as JSON."""
    open_jobs = [j for j in jobs if j['status'] == 'open']
    return jsonify(open_jobs)


# ═══════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
