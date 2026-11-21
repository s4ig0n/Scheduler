# Scheduler

A web-based scheduling application built with Django for managing courses, office hours, enrollment, and role-based access.

## About the Project

This project was originally developed as a group project by a team of four.

After completing the original project, I created this version as an opportunity to continue developing the application independently. I have substantially redesigned the application's layout, visual style, color scheme, and overall user interface, and I plan to continue improving and expanding its functionality.

The goal of this version is to turn the original course project into a more polished, maintainable, and feature-rich application while building on the concepts and functionality developed during the original project.

## Current Features

- User authentication and role-based access
- Student, TA, instructor, and staff functionality
- Course management
- Office hour scheduling
- Student enrollment
- Course and office hour relationships
- Dashboard views based on user role
- Django-based backend with SQLite database
- Redesigned user interface and application layout

## Technology

- **Python**
- **Django**
- **SQLite**
- **HTML**
- **CSS**
- **JavaScript**
- **Bootstrap**

## Project Structure

```text
Scheduler/
├── DjangoProject/       # Django project configuration
├── SchedulerApp/        # Main application
├── classes/             # Domain classes (courses, users, office hours)
├── templates/           # HTML templates and page layouts
├── static/              # CSS, JavaScript, and other static files
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
└── README.md
```

## Running locally

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # first admin account
python manage.py runserver
```

Then open http://127.0.0.1:8000/. The SQLite database (`db.sqlite3`) is created by `migrate` and is not checked in.

## Credits

The original course version was built by a team of four in a scrum-based process. This repository is my
independent continuation of that project.

