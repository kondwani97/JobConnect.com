# JobConnect Flask Application

JobConnect is a web application that connects workers with job opportunities based on their skills. This application allows users to register, post jobs, and find jobs that match their skills.

## Project Structure

```
jobconnect-flask
├── app.py
├── requirements.txt
├── templates
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── post_job.html
│   └── find_jobs.html
├── static
│   └── style.css
└── README.md
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd jobconnect-flask
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. **Install the required dependencies:**
   ```
   pip install -r requirements.txt
   ```

## Usage

1. **Run the application:**
   ```
   python app.py
   ```

2. **Access the application:**
   Open your web browser.

## Features

- User registration with name, skill, and location.
- Job posting by employers with required skills and job descriptions.
- Job searching for users based on their skills.

