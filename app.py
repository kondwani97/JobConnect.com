from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

users = []
jobs = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        skill = request.form['skill']
        location = request.form['location']
        users.append({'name': name, 'skill': skill, 'location': location})
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if request.method == 'POST':
        employer = request.form['employer']
        job_skill = request.form['job_skill']
        job_desc = request.form['job_desc']
        jobs.append({'employer': employer, 'skill': job_skill, 'desc': job_desc})
        return redirect(url_for('index'))
    return render_template('post_job.html')

@app.route('/find_jobs', methods=['GET', 'POST'])
def find_jobs():
    if request.method == 'POST':
        name = request.form['name']
        skill = request.form['skill']
        matching_jobs = [job for job in jobs if job['skill'].lower() == skill.lower()]
        return render_template('find_jobs.html', name=name, skill=skill, jobs=matching_jobs)
    return render_template('find_jobs.html', jobs=[])

if __name__ == '__main__':
    app.run(debug=True)