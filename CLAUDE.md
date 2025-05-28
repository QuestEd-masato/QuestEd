# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuestEd is a Flask-based educational platform with multi-role support (admin, teacher, student), featuring school management, AI-powered curriculum generation, and student tracking capabilities.

## Development Commands

### Running the Application
```bash
# Development mode
python app.py

# Using Flask CLI
export FLASK_APP=app.py
export FLASK_ENV=development
flask run

# Production with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Database Management
```bash
# Initialize migrations
flask db init

# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migrations
flask db downgrade
```

### Environment Setup
Create a `.env` file with:
- `SECRET_KEY` - Flask secret key
- `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME` - MySQL database credentials
- `OPENAI_API_KEY` - OpenAI API key for AI features
- `FLASK_ENV` - development/production
- `FLASK_DEBUG` - true/false

## Architecture Overview

### Application Structure (Refactored to Blueprints)
- **run.py** - Main entry point for running the application
- **app/** - Main application package with Blueprint structure
  - **__init__.py** - Application factory and initialization
  - **models/** - All database models (User, Class, School, etc.)
  - **auth/** - Authentication routes (login, register, password reset)
  - **admin/** - Admin functionality (user/school management)
  - **teacher/** - Teacher features (class management, evaluations)
  - **student/** - Student features (activities, surveys, themes)
  - **ai/** - AI integration (OpenAI API functions)
  - **api/** - REST API endpoints
- **config.py** - Configuration classes for different environments
- **extensions.py** - Shared Flask extension instances (db, migrate, login_manager, admin, csrf)

### Legacy Structure
- **app_old.py** - Original monolithic application (4831 lines) - kept for reference
- **app_factory.py** - Original application factory pattern

### Additional Modules
- **core/** - Academic, enrollment, and school management blueprints
- **basebuilder/** - Learning management system with problems, texts, and proficiency tracking
- **templates/** - Jinja2 templates organized by feature area
- **static/** - CSS, JavaScript, and uploaded files

### Database Models

#### User System
- `User` - Multi-role users (admin, teacher, student) with email verification
- `School` - School entities with unique codes
- `SchoolYear` - Academic year tracking
- `ClassGroup` - Classes within school years
- `StudentEnrollment` - Student-class relationships

#### Educational Content
- `Class` - Teacher-owned classes
- `MainTheme` - Class-level themes
- `InquiryTheme` - Student personal themes
- `Curriculum` - Class curriculums with JSON data
- `Milestone` - Class milestones for student submissions

#### Student Data
- `InterestSurvey` - Student interests (JSON)
- `PersonalitySurvey` - Student personality data (JSON)
- `ActivityLog` - Student activities with optional images
- `Todo` - Student task management
- `Goal` - Student goals with progress tracking
- `StudentEvaluation` - Teacher evaluations

#### BaseBuilder Module
- `ProblemCategory` - Problem categorization
- `BasicKnowledgeItem` - Individual problems
- `TextSet` - Text collections for reading comprehension
- `LearningPath` - Structured learning sequences
- `ProficiencyRecord` - Student mastery tracking

### Key Features

#### Authentication & Authorization
- Email verification required for new users
- Teacher approval for student accounts
- Role-based access control (admin, teacher, student)
- Password reset via email tokens

#### AI Integration
- OpenAI GPT-4 for curriculum generation
- AI-powered theme suggestions
- Student evaluation assistance
- Chat interface for educational support

#### Data Import/Export
- CSV import for users and students
- Curriculum import/export
- Activity log export to PDF
- Evaluation export to CSV

### Common Patterns

#### Route Protection
```python
@login_required  # Requires authentication
if current_user.role != 'teacher':  # Role checking
    flash('この機能は教師のみ利用可能です。')
    return redirect(url_for('index'))
```

#### Database Operations
```python
# Always use try-except for database operations
try:
    db.session.add(new_object)
    db.session.commit()
    flash('Success message')
except Exception as e:
    db.session.rollback()
    flash(f'Error: {str(e)}')
```

#### File Uploads
- Images stored in `static/uploads/`
- Filename sanitization with timestamps
- Allowed extensions: jpg, jpeg, png, gif
- Max file size: 16MB

### Testing
Currently no automated tests. To add tests:
1. Create `tests/` directory
2. Use pytest with Flask test client
3. Test database operations with test database from `TestingConfig`

### Important Notes
- Japanese UI - All user-facing text is in Japanese
- MySQL/PyMySQL for database (not SQLite)
- Flask-Admin for administrative interface
- CSRF protection enabled globally
- All datetime stored in UTC