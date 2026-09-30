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
├── templates/           # HTML templates and page layouts
├── static/              # CSS, JavaScript, and other static files
├── db.sqlite3           # Development database
├── manage.py            # Django management script
└── README.md