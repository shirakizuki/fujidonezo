# Donezo

A modern task management web application built with Django 5.2.1 and styled with Tailwind CSS.

## Project Overview

Donezo is a user-friendly web application designed to help users manage their tasks and stay organized. Built with Django and featuring a clean, modern UI powered by Tailwind CSS, this application provides a seamless user experience with secure authentication and responsive design.

## Features

- **User Authentication System**:
  - User registration with email verification
  - Secure login and logout functionality
  - Password strength validation
  - Password recovery option

- **Task Management**:
  - Create, read, update, and delete tasks
  - Organize tasks by due date (Today, Upcoming)
  - Mark tasks as completed
  - Archive and restore tasks
  - Task labels for better organization

- **Modern UI**:
  - Clean and intuitive interface
  - Fully responsive design that works on all devices
  - Mobile-first approach
  - Custom styling with Tailwind CSS
  - Password strength meter for better security

## Technologies Used

- **Backend**:
  - Python 3.13.2
  - Django 5.2.1
  - SQLite database (development)
  
- **Frontend**:
  - Tailwind CSS 3.x (via django-tailwind 4.0.1)
  - JavaScript (for password strength validation)
  - Responsive design principles
  
- **Development Tools**:
  - Django Browser Reload for hot-reloading during development
  - Modern CSS processing with PostCSS

## Setup and Installation

### Prerequisites

- Python 3.13.2 or higher
- pip (Python package installer)
- Node.js and npm (for Tailwind CSS processing)

### Installation Steps

1. Clone the repository
   ```bash
   git clone <repository-url>
   cd donezo
   ```

2. Create a virtual environment
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment
   - Windows:
     ```bash
     .\.venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. Install Python dependencies
   ```bash
   pip install -r requirements.txt
   ```

5. Install Node.js dependencies for Tailwind CSS
   ```bash
   cd app/theme/static_src
   npm install
   cd ../../../
   ```

6. Run migrations
   ```bash
   cd app
   python manage.py migrate
   ```

7. Start the Tailwind CSS watcher (in a separate terminal)
   ```bash
   cd app
   python manage.py tailwind start
   ```

8. Start the development server
   ```bash
   cd app
   python manage.py runserver
   ```

9. Access the application at http://127.0.0.1:8000/

## Project Structure

```
donezo/
   ├── LICENSE            # Project license
   ├── README.md          # Project documentation
   ├── requirements.txt   # Python dependencies
   └── app/               # Main application directory
         ├── manage.py      # Django's command-line utility for administrative tasks
         ├── db.sqlite3     # SQLite database file
         ├── app/           # Project configuration
         │   ├── __init__.py
         │   ├── asgi.py    # ASGI config for deployment
         │   ├── settings.py # Project settings
         │   ├── urls.py    # Main URL routing
         │   └── wsgi.py    # WSGI config for deployment
         └── theme/         # Main application module
            ├── __init__.py
            ├── admin.py   # Admin site configuration
            ├── apps.py    # App configuration
            ├── forms.py   # Form definitions
            ├── models.py  # Data models
            ├── urls.py    # URL routing for the theme app
            ├── view.py    # View controllers
            ├── migrations/ # Database migrations
            ├── static/    # Static assets (CSS, JS, images)
            │   ├── css/   # CSS files
            │   ├── images/ # Image files
            │   └── js/    # JavaScript files
            ├── static_src/ # Tailwind CSS source files
            │   ├── package.json
            │   ├── postcss.config.js
            │   └── src/   # Source styles
            └── templates/  # HTML templates
               ├── base.html  # Base template
               ├── auth/      # Authentication templates
               ├── emails/    # Email templates
               └── home/      # Home page templates
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms of the license included in the repository.