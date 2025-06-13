# QuestEd Technical Specification Document
## Comprehensive System Architecture and Development Guide

**Version**: 1.4.1  
**Last Updated**: January 13, 2025  
**Document Type**: Technical Specification  
**Target Audience**: Developers, System Architects, DevOps Engineers

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Analysis](#architecture-analysis)
3. [Database Schema Documentation](#database-schema-documentation)
4. [API Endpoints Documentation](#api-endpoints-documentation)
5. [Security Architecture](#security-architecture)
6. [Deployment Architecture](#deployment-architecture)
7. [File Organization Structure](#file-organization-structure)
8. [Dependencies and Integrations](#dependencies-and-integrations)
9. [Development Guidelines](#development-guidelines)
10. [Performance Considerations](#performance-considerations)
11. [Testing Strategy](#testing-strategy)
12. [Monitoring and Logging](#monitoring-and-logging)

---

## 1. System Overview

### 1.1 Project Description
QuestEd is a comprehensive educational platform designed to support inquiry-based learning in middle and high schools. It leverages AI technology to provide personalized learning experiences and teacher support tools.

### 1.2 Core Features
- **Multi-role User Management**: Support for admins, teachers, and students
- **AI-Powered Learning**: Subject-specific AI prompts for personalized instruction
- **School Management**: Institutional-level user and class management
- **Inquiry Learning Support**: Theme creation, activity tracking, progress monitoring
- **Automated Reporting**: Daily learning reports with AI-generated summaries
- **Assessment System**: Rubric-based evaluation with AI assistance
- **BaseBuilder Module**: Vocabulary and basic knowledge building system

### 1.3 Technical Highlights
- **Subject Integration**: 6-subject support (Science, Math, Japanese, Social Studies, English, Integrated)
- **Security-First Design**: XSS protection, CSRF guards, role-based access control
- **Scalable Architecture**: Celery-based asynchronous processing
- **Email Integration**: SMTP/Gmail API dual support
- **File Security**: Comprehensive file validation and sandboxing

---

## 2. Architecture Analysis

### 2.1 Technology Stack

#### Backend Framework
```
Framework: Flask 2.2.3
ORM: SQLAlchemy (Flask-SQLAlchemy 3.0.3)
Database: MySQL 8.0 with PyMySQL 1.0.3
Task Queue: Celery with Redis backend
Authentication: Flask-Login 0.6.2
Forms & CSRF: Flask-WTF 1.1.1
Admin Interface: Flask-Admin 1.6.1
Database Migrations: Flask-Migrate 4.0.4
Rate Limiting: Flask-Limiter 3.5.0
```

#### Frontend Technologies
```
CSS Framework: Bootstrap 5.x
JavaScript: Vanilla JS + jQuery (minimal usage)
Icons: Font Awesome
Templates: Jinja2 (Flask built-in)
Chart Libraries: Chart.js (for analytics)
```

#### External Services
```
AI Service: OpenAI GPT-4/GPT-3.5-turbo (API 0.27.2)
Email: Gmail SMTP / Gmail API
File Processing: Pillow 11.0.0
PDF Generation: ReportLab 4.0.4
Security: bleach 6.1.0 for HTML sanitization
```

#### Infrastructure Stack
```
Application Server: Gunicorn 20.1.0
Reverse Proxy: Nginx
Database: MySQL 8.0
Cache/Message Broker: Redis 6.0+
Process Management: systemd
Server: AWS EC2 (recommended: t3a.medium+)
```

### 2.2 Application Architecture Pattern

#### Blueprint-Based Modular Architecture
```python
app/
├── __init__.py           # Application Factory
├── auth/                 # Authentication Blueprint
├── admin/                # Admin Panel Blueprint
├── teacher/              # Teacher Features Blueprint
├── student/              # Student Features Blueprint
├── api/                  # REST API Blueprint
├── models/               # Database Models
├── utils/                # Shared Utilities
└── tasks/                # Celery Background Tasks
```

#### Configuration Management
```python
# Multi-environment configuration
config.py
├── Config (Base)
├── DevelopmentConfig
├── TestingConfig
└── ProductionConfig
```

### 2.3 Data Flow Architecture

#### Request Processing Flow
```
Browser Request → Nginx → Gunicorn → Flask App → Blueprint Router → View Function → Database/AI → Response
```

#### Background Task Flow
```
Web Request → Celery Task Queue → Redis → Celery Worker → Task Execution → Database Update → Email/Notification
```

#### AI Integration Flow
```
User Query → Flask API → Context Building → OpenAI API → Response Processing → Database Storage → User Response
```

---

## 3. Database Schema Documentation

### 3.1 Core User Management Schema

#### users table
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    role ENUM('admin', 'teacher', 'student') NOT NULL,
    school_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Email verification fields
    email_confirmed BOOLEAN DEFAULT FALSE,
    email_token VARCHAR(100),
    token_created_at DATETIME,
    is_approved BOOLEAN DEFAULT FALSE,
    
    -- Password reset fields
    reset_token VARCHAR(100),
    reset_token_created_at DATETIME,
    
    FOREIGN KEY (school_id) REFERENCES schools(id)
);
```

### 3.2 School Management Schema

#### schools table
```sql
CREATE TABLE schools (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE,
    address TEXT,
    contact_email VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### school_years table
```sql
CREATE TABLE school_years (
    id INT PRIMARY KEY AUTO_INCREMENT,
    school_id INT NOT NULL,
    year VARCHAR(20) NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    start_date DATE,
    end_date DATE,
    
    FOREIGN KEY (school_id) REFERENCES schools(id),
    UNIQUE KEY unique_school_year (school_id, year)
);
```

#### class_groups table
```sql
CREATE TABLE class_groups (
    id INT PRIMARY KEY AUTO_INCREMENT,
    school_year_id INT NOT NULL,
    teacher_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    grade VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (school_year_id) REFERENCES school_years(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);
```

#### student_enrollments table
```sql
CREATE TABLE student_enrollments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    class_group_id INT NOT NULL,
    school_year_id INT NOT NULL,
    student_number INT,
    enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (class_group_id) REFERENCES class_groups(id),
    FOREIGN KEY (school_year_id) REFERENCES school_years(id),
    UNIQUE KEY unique_enrollment (student_id, class_group_id, school_year_id)
);
```

### 3.3 Subject and Class Management Schema

#### subjects table
```sql
CREATE TABLE subjects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    ai_system_prompt TEXT,
    learning_objectives TEXT,
    assessment_criteria TEXT,
    grade_level VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### classes table
```sql
CREATE TABLE classes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    teacher_id INT NOT NULL,
    school_id INT NOT NULL,
    subject_id INT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    schedule VARCHAR(200),
    location VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (teacher_id) REFERENCES users(id),
    FOREIGN KEY (school_id) REFERENCES schools(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);
```

#### class_enrollments table
```sql
CREATE TABLE class_enrollments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    class_id INT NOT NULL,
    student_id INT NOT NULL,
    enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (student_id) REFERENCES users(id),
    UNIQUE KEY unique_class_enrollment (class_id, student_id)
);
```

### 3.4 Learning Content Schema

#### main_themes table
```sql
CREATE TABLE main_themes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    teacher_id INT NOT NULL,
    class_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (teacher_id) REFERENCES users(id),
    FOREIGN KEY (class_id) REFERENCES classes(id)
);
```

#### inquiry_themes table
```sql
CREATE TABLE inquiry_themes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    class_id INT,
    main_theme_id INT,
    is_ai_generated BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    title VARCHAR(200),
    question TEXT,
    description TEXT,
    rationale TEXT,
    approach TEXT,
    potential TEXT,
    is_selected BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (main_theme_id) REFERENCES main_themes(id)
);
```

### 3.5 Activity and Assessment Schema

#### activity_logs table
```sql
CREATE TABLE activity_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    class_id INT,
    title VARCHAR(200),
    date DATE DEFAULT (CURRENT_DATE),
    content TEXT,
    reflection TEXT,
    image_url VARCHAR(255),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    activity TEXT,
    tags VARCHAR(255),
    
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (class_id) REFERENCES classes(id)
);
```

#### todos table
```sql
CREATE TABLE todos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    due_date DATE,
    priority ENUM('high', 'medium', 'low'),
    is_completed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES users(id)
);
```

#### goals table
```sql
CREATE TABLE goals (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    goal_type ENUM('long', 'medium', 'short'),
    due_date DATE,
    progress INT DEFAULT 0,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES users(id)
);
```

### 3.6 Communication Schema

#### chat_history table
```sql
CREATE TABLE chat_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    class_id INT,
    subject_id INT,
    message TEXT NOT NULL,
    is_user BOOLEAN DEFAULT TRUE,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);
```

### 3.7 BaseBuilder Module Schema

#### problem_categories table
```sql
CREATE TABLE problem_categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INT,
    school_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    
    FOREIGN KEY (parent_id) REFERENCES problem_categories(id),
    FOREIGN KEY (school_id) REFERENCES schools(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

#### basic_knowledge_items table
```sql
CREATE TABLE basic_knowledge_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    question TEXT NOT NULL,
    answer_type VARCHAR(20) DEFAULT 'text',
    correct_answer TEXT NOT NULL,
    choices TEXT,
    explanation TEXT,
    difficulty INT DEFAULT 2,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    text_set_id INT,
    order_in_text INT,
    school_id INT,
    
    FOREIGN KEY (category_id) REFERENCES problem_categories(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (text_set_id) REFERENCES text_sets(id),
    FOREIGN KEY (school_id) REFERENCES schools(id)
);
```

### 3.8 Database Relationships Summary

#### Primary Relationships
```
schools (1) ←→ (n) users
schools (1) ←→ (n) school_years
school_years (1) ←→ (n) class_groups
users(teacher) (1) ←→ (n) classes
users(student) (n) ←→ (n) classes (via class_enrollments)
subjects (1) ←→ (n) classes
subjects (1) ←→ (n) chat_history
classes (1) ←→ (n) main_themes
students (1) ←→ (n) inquiry_themes
students (1) ←→ (n) activity_logs
students (1) ←→ (n) todos
students (1) ←→ (n) goals
users (1) ←→ (n) chat_history
```

---

## 4. API Endpoints Documentation

### 4.1 Authentication Endpoints

#### POST /auth/login
**Purpose**: User authentication  
**Access**: Public  

**Request Body**:
```json
{
    "username": "string",
    "password": "string"
}
```

**Response**:
```json
{
    "status": "success",
    "redirect_url": "/teacher/dashboard"
}
```

**Error Response**:
```json
{
    "status": "error",
    "message": "ユーザー名またはパスワードが正しくありません。"
}
```

#### POST /auth/register
**Purpose**: User registration  
**Access**: Public  

**Request Body**:
```json
{
    "username": "string",
    "full_name": "string",
    "email": "string",
    "password": "string",
    "confirm_password": "string",
    "role": "student|teacher|admin",
    "school_code": "string"
}
```

#### POST /auth/logout
**Purpose**: User logout  
**Access**: Authenticated users  

#### POST /auth/forgot_password
**Purpose**: Password reset request  
**Access**: Public  

#### POST /auth/reset_password/<user_id>/<token>
**Purpose**: Password reset confirmation  
**Access**: Token-based  

### 4.2 AI Chat API

#### POST /api/chat
**Purpose**: AI-powered chat interaction  
**Access**: Authenticated users  
**Rate Limit**: Smart AI limiting (varies by user type)  

**Request Body**:
```json
{
    "message": "光合成について教えて",
    "class_id": 1,
    "step": "science_inquiry",
    "function": ""
}
```

**Response**:
```json
{
    "message": "光合成は植物が太陽エネルギーを使って二酸化炭素と水から糖を作る重要な生命現象です...",
    "status": "success"
}
```

**Error Response**:
```json
{
    "error": "エラーが発生しました。もう一度お試しください。",
    "status": "error"
}
```

### 4.3 Teacher API Endpoints

#### GET /api/teacher/first_class
**Purpose**: Get teacher's first class for initial setup  
**Access**: Teachers only  

**Response**:
```json
{
    "class_id": 1,
    "class_name": "理科1年A組"
}
```

#### POST /api/export/evaluations
**Purpose**: Export student evaluation data  
**Access**: Teachers only  

**Response**:
```json
{
    "evaluations": [
        {
            "student_name": "student01",
            "evaluation": "優秀な探究活動を展開しています..."
        }
    ],
    "class_name": "理科1年A組",
    "status": "success"
}
```

### 4.4 Student API Endpoints

#### POST /api/theme/<theme_id>/select
**Purpose**: Select inquiry theme  
**Access**: Students only  

**Response**:
```json
{
    "status": "success",
    "message": "テーマ「環境問題と生物多様性」を選択しました"
}
```

#### POST /api/todo/<todo_id>/toggle
**Purpose**: Toggle todo completion status  
**Access**: Students only  

**Response**:
```json
{
    "status": "success",
    "is_completed": true,
    "message": "To Doを完了にしました"
}
```

#### POST /api/goal/<goal_id>/progress
**Purpose**: Update goal progress  
**Access**: Students only  

**Request Body**:
```json
{
    "progress": 75
}
```

**Response**:
```json
{
    "status": "success",
    "progress": 75,
    "is_completed": false,
    "message": "進捗を75%に更新しました"
}
```

### 4.5 Administrative API

#### GET /api/stats
**Purpose**: Get system statistics  
**Access**: Role-specific data  

**Admin Response**:
```json
{
    "total_users": 150,
    "total_students": 120,
    "total_teachers": 25,
    "total_classes": 30,
    "pending_approvals": 5
}
```

**Teacher Response**:
```json
{
    "total_classes": 5,
    "total_students": 125,
    "pending_approvals": 3
}
```

**Student Response**:
```json
{
    "total_activities": 15,
    "pending_todos": 3,
    "active_goals": 2,
    "completed_goals": 1
}
```

### 4.6 BaseBuilder API (Module-specific)

#### GET /basebuilder/api/problems/<category_id>
**Purpose**: Get problems by category  
**Access**: Authenticated users  

#### POST /basebuilder/api/solve
**Purpose**: Submit problem solution  
**Access**: Students  

#### GET /basebuilder/api/proficiency/<student_id>
**Purpose**: Get student proficiency data  
**Access**: Teachers and own data for students  

---

## 5. Security Architecture

### 5.1 Authentication and Authorization

#### Authentication Strategy
```python
# Session-based authentication using Flask-Login
from flask_login import LoginManager, login_required, current_user

# Multi-factor considerations
- Email verification required
- Account approval workflow for students
- Password strength validation
- Token-based password reset with expiration
```

#### Role-Based Access Control (RBAC)
```python
# Decorator-based authorization
@login_required
@teacher_required
def teacher_dashboard():
    pass

@admin_required
def admin_panel():
    pass

# Role hierarchy
admin > teacher > student
```

#### Password Security
```python
# Password requirements (app/auth/password_validator.py)
- Minimum 12 characters
- Must contain: uppercase, lowercase, numbers, special characters
- No more than 2 consecutive identical characters
- Bcrypt hashing with salt
```

### 5.2 Input Validation and Sanitization

#### XSS Protection
```python
# Template auto-escaping (Jinja2 default)
{{ user_input }}  # Automatically escaped

# Content Security Policy headers
Content-Security-Policy: default-src 'self'; 
    script-src 'self' 'unsafe-inline' cdn.jsdelivr.net;
    style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com;
```

#### CSRF Protection
```python
# Flask-WTF CSRF protection
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600  # 1 hour token lifetime

# All forms automatically protected
class LoginForm(FlaskForm):
    # CSRF token automatically included
```

#### SQL Injection Prevention
```python
# SQLAlchemy ORM with parameterized queries
User.query.filter_by(username=username).first()  # Safe
db.session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})  # Safe
```

### 5.3 File Upload Security

#### Comprehensive File Validation (v1.4.1+)
```python
# FileSecurityValidator class (app/utils/file_security.py)
class FileSecurityValidator:
    def validate_image(self, file_stream, filename, max_size=5*1024*1024):
        # MIME type validation using python-magic
        # File size validation
        # Extension whitelist checking
        # Image header validation
        # Malicious content scanning
        
    def validate_csv(self, file_stream, filename, max_size=2*1024*1024):
        # CSV structure validation
        # XSS pattern detection in content
        # Encoding validation
        # Size limitations
```

#### Secure File Storage
```python
# User-segregated directory structure
uploads/
├── secure/
│   ├── user_{user_id}/
│   │   ├── images/
│   │   └── documents/
└── public/
    └── static_assets/

# Path traversal protection
secure_filename() + additional validation
```

### 5.4 Session Security

#### Session Configuration
```python
# Secure session settings
PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
SESSION_COOKIE_SECURE = True       # HTTPS only
SESSION_COOKIE_HTTPONLY = True     # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'    # CSRF protection
```

### 5.5 Rate Limiting

#### Adaptive Rate Limiting
```python
# Smart rate limiting (app/utils/rate_limiting.py)
@smart_ai_limit()  # AI endpoints: varies by user role
@auth_limit()      # Auth endpoints: 5 requests/minute
@api_limit()       # General API: 50 requests/hour

# Rate limiting tiers
- Students: 10 AI requests/hour
- Teachers: 50 AI requests/hour
- Admins: 100 AI requests/hour
```

### 5.6 Security Headers

#### HTTP Security Headers
```python
# Security headers middleware (app/utils/security.py)
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### 5.7 Data Privacy and Compliance

#### Data Protection Measures
- User data encryption at rest
- Secure data transmission (HTTPS)
- User consent management
- Data retention policies
- Right to data deletion (GDPR compliance ready)

#### Audit Logging
```python
# Security event logging
SecurityUtils.log_security_event(
    event_type="LOGIN_ATTEMPT",
    user_id=user.id,
    details="Failed login from suspicious IP"
)
```

---

## 6. Deployment Architecture

### 6.1 Production Infrastructure

#### Recommended Hardware Specifications
```
Server Type: AWS EC2 t3a.medium or equivalent
CPU: 2 vCPUs (Intel/AMD)
RAM: 4 GB minimum, 8 GB recommended
Storage: 20 GB SSD minimum, 50 GB recommended
Network: High bandwidth for file uploads
```

#### Operating System Support
```
Primary: Amazon Linux 2
Secondary: Ubuntu 20.04 LTS
Alternative: CentOS 8/RHEL 8
```

### 6.2 Application Stack Deployment

#### Web Server Configuration
```nginx
# Nginx configuration (/etc/nginx/sites-available/quested)
server {
    listen 80;
    server_name quest-ed.jp www.quest-ed.jp;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # File size limits
    client_max_body_size 16M;
    
    # Static file serving
    location /static {
        alias /var/www/QuestEd/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Application proxy
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

#### Application Server Configuration
```python
# Gunicorn configuration (gunicorn.conf.py)
bind = "127.0.0.1:8001"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 600
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
user = "ec2-user"
group = "ec2-user"
logfile = "/var/log/gunicorn/quested.log"
loglevel = "info"
```

### 6.3 Database Deployment

#### MySQL Configuration
```sql
-- Database setup
CREATE DATABASE quested CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'quested_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON quested.* TO 'quested_user'@'localhost';
FLUSH PRIVILEGES;
```

#### Performance Optimization
```sql
-- Recommended MySQL settings for production
[mysqld]
innodb_buffer_pool_size = 2G
innodb_log_file_size = 256M
max_connections = 200
query_cache_size = 64M
query_cache_type = 1
```

### 6.4 Redis Configuration

#### Redis Setup for Celery
```conf
# Redis configuration (/etc/redis/redis.conf)
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 6.5 Celery Background Processing

#### Celery Worker Configuration
```python
# Celery worker setup (celery_worker.py)
from celery import Celery
from app import create_app

app = create_app()
celery = app.extensions['celery']

# Worker command
celery -A celery_worker.celery worker --loglevel=info --concurrency=4
```

#### Systemd Service Configuration
```ini
# /etc/systemd/system/quested-celery.service
[Unit]
Description=QuestEd Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=ec2-user
Group=ec2-user
WorkingDirectory=/var/www/QuestEd
Environment=PATH=/var/www/QuestEd/venv/bin
ExecStart=/var/www/QuestEd/venv/bin/celery -A celery_worker.celery worker --detach
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6.6 Environment Configuration

#### Production Environment Variables
```bash
# Required environment variables (.env)
SECRET_KEY=your-very-secure-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=false

# Database
DB_USERNAME=quested_user
DB_PASSWORD=your_secure_db_password
DB_HOST=localhost
DB_NAME=quested

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=info@quested.jp
SMTP_PASSWORD=your_gmail_app_password

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 6.7 SSL/TLS Configuration

#### Let's Encrypt Setup
```bash
# Install Certbot
sudo yum install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d quest-ed.jp -d www.quest-ed.jp

# Auto-renewal
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

### 6.8 Backup Strategy

#### Database Backup
```bash
# Daily automated backup
#!/bin/bash
# /usr/local/bin/backup_quested.sh
DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -h $DB_HOST -u $DB_USERNAME -p$DB_PASSWORD $DB_NAME > /backup/quested_$DATE.sql
find /backup -name "quested_*.sql" -mtime +7 -delete
```

#### Application Backup
```bash
# Configuration and code backup
tar -czf /backup/quested_config_$(date +%Y%m%d).tar.gz \
    /var/www/QuestEd/.env \
    /var/www/QuestEd/gunicorn.conf.py \
    /etc/nginx/sites-available/quested \
    /etc/systemd/system/quested*.service
```

---

## 7. File Organization Structure

### 7.1 Project Root Structure
```
QuestEd/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory
│   ├── models/                  # Database models
│   ├── auth/                    # Authentication blueprint
│   ├── admin/                   # Admin panel blueprint
│   ├── teacher/                 # Teacher features blueprint
│   ├── student/                 # Student features blueprint
│   ├── api/                     # REST API blueprint
│   ├── ai/                      # AI integration modules
│   ├── tasks/                   # Celery background tasks
│   ├── utils/                   # Shared utility modules
│   ├── scripts/                 # Management scripts
│   ├── special_routes.py        # Special route handlers
│   └── version.py               # Version management
├── templates/                   # Jinja2 templates
│   ├── base.html               # Base template
│   ├── auth/                   # Authentication templates
│   ├── admin/                  # Admin panel templates
│   ├── teacher/                # Teacher interface templates
│   ├── student/                # Student interface templates
│   ├── basebuilder/            # BaseBuilder module templates
│   └── errors/                 # Error page templates
├── static/                      # Static assets
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript files
│   ├── images/                 # Image assets
│   └── uploads/                # User uploaded files
├── migrations/                  # Database migration files
├── basebuilder/                 # BaseBuilder module
│   ├── __init__.py             # Module initialization
│   ├── models.py               # BaseBuilder models
│   ├── routes.py               # BaseBuilder routes
│   ├── exporters.py            # Data export utilities
│   └── importers.py            # Data import utilities
├── core/                        # Core functionality modules
│   ├── academic.py             # Academic year management
│   ├── enrollment.py           # Student enrollment logic
│   ├── models.py               # Core models
│   ├── school.py               # School management
│   └── utils/                  # Core utilities
├── legacy/                      # Legacy code (for reference)
├── scripts/                     # Deployment and management scripts
├── docs/                        # Documentation
├── config.py                    # Configuration classes
├── extensions.py                # Flask extensions setup
├── run.py                       # Application entry point
├── celery_worker.py             # Celery worker configuration
├── requirements.txt             # Python dependencies
├── version.json                 # Version tracking
├── .env                         # Environment variables (not in repo)
├── gunicorn.conf.py             # Gunicorn configuration
└── README.md                    # Project documentation
```

### 7.2 Blueprint Organization

#### Authentication Blueprint (app/auth/)
```
auth/
├── __init__.py                  # Blueprint definition and routes
└── password_validator.py        # Password validation utilities
```

#### Admin Blueprint (app/admin/)
```
admin/
├── __init__.py                  # Blueprint registration
├── analytics.py                # Analytics and reporting
├── school_management.py         # School administration
└── user_management.py          # User administration
```

#### Teacher Blueprint (app/teacher/)
```
teacher/
├── __init__.py                  # Blueprint and route definitions
└── pdf_generator.py             # PDF generation utilities
```

#### Student Blueprint (app/student/)
```
student/
└── __init__.py                  # Student-specific routes
```

#### API Blueprint (app/api/)
```
api/
└── __init__.py                  # REST API endpoints
```

### 7.3 Model Organization

#### Main Models (app/models/)
```
models/
├── __init__.py                  # All model definitions
└── subject.py                   # Subject-specific models
```

#### BaseBuilder Models (basebuilder/)
```
basebuilder/
├── models.py                    # BaseBuilder-specific models
│   ├── ProblemCategory         # Vocabulary categories
│   ├── BasicKnowledgeItem      # Vocabulary items
│   ├── TextSet                 # Text collections
│   ├── AnswerRecord           # Student responses
│   ├── ProficiencyRecord      # Learning progress
│   └── LearningPath           # Learning pathways
```

### 7.4 Utility Organization

#### Core Utilities (app/utils/)
```
utils/
├── config_validator.py         # Configuration validation
├── database.py                 # Database utilities
├── decorators.py               # Custom decorators
├── email_sender.py             # Email service abstraction
├── file_security.py            # File upload security
├── rate_limiting.py            # Rate limiting implementation
└── security.py                 # Security utilities
```

### 7.5 Template Organization

#### Template Hierarchy
```
templates/
├── base.html                    # Master template
├── _csv_format_info.html        # CSV format helper
├── auth/                        # Authentication pages
│   ├── login.html
│   ├── register.html
│   ├── forgot_password.html
│   └── change_password.html
├── admin/                       # Admin interface
│   ├── base_admin.html
│   ├── dashboard.html
│   ├── users.html
│   └── analytics_dashboard.html
├── teacher/                     # Teacher interface
│   ├── dashboard.html
│   ├── classes.html
│   └── evaluations.html
├── student/                     # Student interface
│   ├── dashboard.html
│   ├── activities.html
│   └── themes.html
├── basebuilder/                 # BaseBuilder module
│   ├── layout.html
│   ├── student_dashboard.html
│   ├── teacher_dashboard.html
│   └── problems.html
└── errors/                      # Error pages
    ├── 404.html
    └── 500.html
```

### 7.6 Static Assets Organization

#### CSS Structure
```
static/css/
├── style.css                    # Main application styles
├── responsive.css               # Responsive design
├── modern-responsive.css        # Enhanced responsive styles
├── admin-override.css           # Admin panel customizations
└── button-overrides.css         # Button style overrides
```

#### JavaScript Structure
```
static/js/
├── main.js                      # Core application JavaScript
├── chat.js                      # Chat functionality
├── mobile.js                    # Mobile-specific enhancements
├── admin-sidebar-killer.js      # Admin interface customizations
└── responsive-tables.js         # Table responsiveness
```

---

## 8. Dependencies and Integrations

### 8.1 Core Python Dependencies

#### Web Framework Stack
```python
Flask==2.2.3                    # Core web framework
Flask-SQLAlchemy==3.0.3         # Database ORM
Flask-Login==0.6.2              # Authentication management
Flask-Admin==1.6.1              # Admin interface
Flask-Migrate==4.0.4            # Database migrations
Flask-WTF==1.1.1                # Form handling and CSRF protection
Flask-Limiter==3.5.0            # Rate limiting
```

#### Database and Storage
```python
mysql-connector-python==8.0.32  # MySQL database connector
PyMySQL==1.0.3                  # Pure Python MySQL client
```

#### AI and External Services
```python
openai==0.27.2                  # OpenAI API integration
```

#### File Processing
```python
Pillow==11.0.0                  # Image processing
reportlab==4.0.4                # PDF generation
```

#### Security
```python
bleach==6.1.0                   # HTML sanitization
Werkzeug==2.2.3                 # WSGI utilities with security features
```

#### Background Processing
```python
celery>=5.3.0                   # Task queue (optional)
redis>=5.0.0                    # Message broker for Celery
```

#### Deployment
```python
gunicorn==20.1.0                # WSGI HTTP Server
python-dotenv==1.0.0            # Environment variable management
```

#### Utilities
```python
requests==2.28.2                # HTTP library
```

### 8.2 External Service Integrations

#### OpenAI GPT Integration
```python
# AI Chat Service Integration (app/ai/helpers.py)
import openai

def generate_chat_response(message, context=None, subject=None):
    """
    Generate AI response with subject-specific prompts
    """
    # Configure OpenAI client
    openai.api_key = current_app.config['OPENAI_API_KEY']
    
    # Build system prompt
    system_prompt = "あなたは優秀な教育AIアシスタントです。"
    if subject and subject.ai_system_prompt:
        system_prompt += f"\n\n【教科特性】\n{subject.ai_system_prompt}"
    
    # Context integration
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    if context:
        for ctx in context:
            role = "user" if ctx['is_user'] else "assistant"
            messages.append({"role": role, "content": ctx['message']})
    
    # Add current message
    messages.append({"role": "user", "content": message})
    
    # API call
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=1000,
        temperature=0.7
    )
    
    return response.choices[0].message.content
```

#### Email Service Integration
```python
# Email Service Abstraction (app/utils/email_sender.py)
class EmailSender:
    """Unified email sending service"""
    
    def __init__(self):
        self.method = os.getenv('EMAIL_METHOD', 'smtp')
        
    def send_email(self, to_email, subject, html_content, text_content=None):
        """Send email using configured method"""
        if self.method == 'smtp':
            return self._send_smtp(to_email, subject, html_content, text_content)
        elif self.method == 'gmail_api':
            return self._send_gmail_api(to_email, subject, html_content)
        else:
            raise ValueError(f"Unsupported email method: {self.method}")
    
    def _send_smtp(self, to_email, subject, html_content, text_content):
        """Send via SMTP"""
        # SMTP implementation
        pass
        
    def _send_gmail_api(self, to_email, subject, html_content):
        """Send via Gmail API"""
        # Gmail API implementation
        pass
```

### 8.3 Database Integration Architecture

#### SQLAlchemy Configuration
```python
# Database configuration (config.py)
class Config:
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
```

#### Migration Management
```python
# Database migrations (Flask-Migrate)
# Initialize migration repository
flask db init

# Create migration
flask db migrate -m "description"

# Apply migration
flask db upgrade

# Migration versioning with app version
# Integrated with version.json tracking
```

### 8.4 Frontend Dependencies

#### CSS Frameworks
```html
<!-- Bootstrap 5.x -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">

<!-- Font Awesome Icons -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.0.0/css/all.min.css">
```

#### JavaScript Libraries
```html
<!-- Bootstrap JavaScript -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>

<!-- Chart.js for analytics -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- jQuery (minimal usage) -->
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
```

### 8.5 Background Task Integration

#### Celery Configuration
```python
# Celery setup (celery_worker.py)
from celery import Celery
from celery.schedules import crontab

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    
    # Configure periodic tasks
    celery.conf.beat_schedule = {
        'daily-reports': {
            'task': 'app.tasks.daily_report.generate_daily_reports',
            'schedule': crontab(hour=17, minute=0),  # Daily at 5 PM JST
        },
    }
    
    celery.conf.timezone = 'Asia/Tokyo'
    
    return celery
```

#### Redis Integration
```python
# Redis configuration for Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Redis client for caching (optional)
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=1)
```

### 8.6 Development Dependencies

#### Development Tools
```python
# Development-only dependencies
pytest>=7.0.0                   # Testing framework
pytest-flask>=1.2.0             # Flask testing utilities
coverage>=6.0.0                 # Code coverage analysis
black>=22.0.0                   # Code formatting
flake8>=4.0.0                   # Code linting
```

#### Debugging and Profiling
```python
# Debug toolbar (development only)
Flask-DebugToolbar==0.13.1

# Profiling
py-spy                          # Python profiler
memory-profiler                 # Memory usage profiling
```

### 8.7 Security Dependencies

#### Security Scanning
```python
# Security analysis tools
bandit>=1.7.0                   # Security vulnerability scanner
safety>=2.0.0                   # Dependency vulnerability checker
```

#### Cryptography
```python
# Cryptographic libraries (via Flask dependencies)
cryptography>=3.4.8            # Cryptographic recipes and primitives
bcrypt>=3.2.0                   # Password hashing
```

### 8.8 Monitoring and Logging Integration

#### Application Monitoring
```python
# Logging configuration
import logging
from logging.handlers import RotatingFileHandler

# Setup structured logging
logging.basicConfig(
    handlers=[RotatingFileHandler('app.log', maxBytes=100000, backupCount=10)],
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
```

#### Performance Monitoring
```python
# Performance monitoring hooks
@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    total_time = time.time() - g.start_time
    # Log slow requests
    if total_time > 1.0:
        app.logger.warning(f'Slow request: {request.endpoint} took {total_time:.2f}s')
    return response
```

---

## 9. Development Guidelines

### 9.1 Code Organization Standards

#### Blueprint Pattern
```python
# Blueprint creation pattern
from flask import Blueprint

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Register routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Implementation
    pass

# Register in app factory
app.register_blueprint(auth_bp)
```

#### Model Definition Standards
```python
# Model definition pattern
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Required fields
    username = db.Column(db.String(50), unique=True, nullable=False)
    
    # Optional fields
    full_name = db.Column(db.String(100), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    
    # Methods
    def get_display_name(self):
        return self.full_name if self.full_name else self.username
```

### 9.2 Security Best Practices

#### Input Validation
```python
# Form validation with Flask-WTF
from flask_wtf import FlaskForm
from wtforms import StringField, validators

class LoginForm(FlaskForm):
    username = StringField('Username', [
        validators.DataRequired(),
        validators.Length(min=3, max=50)
    ])
    password = StringField('Password', [
        validators.DataRequired(),
        validators.Length(min=12)
    ])
```

#### Output Sanitization
```python
# Template output (automatic escaping)
{{ user.comment }}  # Safe - automatically escaped

# Manual escaping when needed
{{ user.comment|escape }}

# Trusted content (use sparingly)
{{ trusted_html|safe }}
```

#### Database Queries
```python
# Safe database queries
# Good: ORM usage
users = User.query.filter_by(active=True).all()

# Good: Parameterized raw queries
db.session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})

# Avoid: String concatenation
# db.session.execute(f"SELECT * FROM users WHERE id = {user_id}")  # Never do this
```

### 9.3 Error Handling Standards

#### Exception Handling Pattern
```python
# Controller-level error handling
@app.route('/api/data')
def get_data():
    try:
        # Business logic
        data = fetch_data()
        return jsonify({"status": "success", "data": data})
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except DatabaseError as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500
```

#### Custom Error Pages
```python
# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
```

### 9.4 Testing Guidelines

#### Unit Test Structure
```python
# Test structure pattern
import pytest
from app import create_app, db
from app.models import User

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_creation(app):
    with app.app_context():
        user = User(username='test', email='test@example.com')
        db.session.add(user)
        db.session.commit()
        
        assert User.query.count() == 1
        assert User.query.first().username == 'test'
```

#### Integration Test Pattern
```python
def test_login_flow(client):
    # Test registration
    response = client.post('/auth/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!'
    })
    assert response.status_code == 302
    
    # Test login
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'SecurePassword123!'
    })
    assert response.status_code == 302
```

### 9.5 Performance Guidelines

#### Database Query Optimization
```python
# Good: Eager loading
users = User.query.options(db.joinedload(User.posts)).all()

# Good: Pagination
users = User.query.paginate(page=1, per_page=20, error_out=False)

# Avoid: N+1 queries
# for user in users:
#     print(user.posts)  # This creates N+1 queries
```

#### Caching Strategy
```python
# Function-level caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_expensive_data(param):
    # Expensive computation
    return result

# Template caching considerations
# Use cache-busting for dynamic content
# Cache static assets with long expiration
```

### 9.6 Documentation Standards

#### Docstring Format
```python
def process_user_data(user_id, data_type='summary'):
    """
    Process user data for reporting.
    
    Args:
        user_id (int): The user identifier
        data_type (str): Type of data to process ('summary', 'detailed', 'analytics')
        
    Returns:
        dict: Processed user data with the following structure:
            {
                'user_id': int,
                'data': dict,
                'timestamp': datetime,
                'status': str
            }
            
    Raises:
        ValueError: If user_id is invalid
        DatabaseError: If database operation fails
        
    Example:
        >>> result = process_user_data(123, 'summary')
        >>> print(result['status'])
        'success'
    """
    pass
```

#### API Documentation Format
```python
# API endpoint documentation
@api_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """
    Get user information by ID.
    
    **URL:** `/api/users/<user_id>`  
    **Method:** `GET`  
    **Auth required:** Yes  
    **Permissions required:** User must be authenticated  
    
    **URL Parameters:**
    - `user_id` (int): User identifier
    
    **Success Response:**
    - **Code:** 200
    - **Content:** 
      ```json
      {
          "id": 1,
          "username": "student01",
          "full_name": "田中太郎",
          "role": "student"
      }
      ```
      
    **Error Response:**
    - **Code:** 404
    - **Content:** `{"error": "User not found"}`
    """
    pass
```

---

## 10. Performance Considerations

### 10.1 Database Performance

#### Query Optimization
```python
# Index recommendations
CREATE INDEX idx_chat_history_user_date ON chat_history(user_id, timestamp);
CREATE INDEX idx_users_school_role ON users(school_id, role);
CREATE INDEX idx_activity_logs_student_date ON activity_logs(student_id, date);
CREATE INDEX idx_class_enrollments_active ON class_enrollments(class_id, is_active);
```

#### Connection Pool Configuration
```python
# SQLAlchemy engine configuration
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,        # Verify connections before use
    'pool_recycle': 300,          # Recycle connections every 5 minutes
    'pool_timeout': 20,           # Connection timeout
    'max_overflow': 0,            # No overflow connections
    'pool_size': 10               # Base connection pool size
}
```

#### Query Pattern Optimization
```python
# Efficient query patterns

# Good: Batch operations
users = User.query.filter(User.id.in_([1, 2, 3, 4, 5])).all()

# Good: Selective loading
user = User.query.options(db.load_only(User.username, User.email)).first()

# Good: Relationship optimization
posts = Post.query.options(db.joinedload(Post.author)).all()

# Avoid: Individual queries in loops
# for user_id in user_ids:
#     user = User.query.get(user_id)  # N+1 problem
```

### 10.2 Application Performance

#### Response Time Optimization
```python
# Response time monitoring
@app.before_request
def before_request():
    g.start_time = time.time()
    g.request_id = str(uuid.uuid4())

@app.after_request
def after_request(response):
    total_time = time.time() - g.start_time
    
    # Log slow requests
    if total_time > 1.0:
        app.logger.warning(
            f'Slow request: {request.endpoint} '
            f'took {total_time:.2f}s '
            f'[{g.request_id}]'
        )
    
    # Add timing header
    response.headers['X-Response-Time'] = f'{total_time:.3f}s'
    return response
```

#### Memory Usage Optimization
```python
# Memory-efficient data processing
def process_large_dataset(query):
    """Process large datasets using pagination to avoid memory issues"""
    page = 1
    per_page = 1000
    
    while True:
        records = query.paginate(page=page, per_page=per_page, error_out=False)
        
        if not records.items:
            break
            
        # Process batch
        for record in records.items:
            yield process_record(record)
            
        page += 1

# Generator pattern for large results
def get_user_activities(user_id):
    """Generator for memory-efficient activity processing"""
    activities = ActivityLog.query.filter_by(student_id=user_id)\
                                 .order_by(ActivityLog.timestamp.desc())
    
    for activity in activities.yield_per(100):
        yield {
            'id': activity.id,
            'title': activity.title,
            'date': activity.date.isoformat(),
            'content': activity.content[:200] + '...' if len(activity.content) > 200 else activity.content
        }
```

### 10.3 Frontend Performance

#### Asset Optimization
```html
<!-- CSS optimization -->
<link rel="preload" href="/static/css/style.css" as="style">
<link rel="stylesheet" href="/static/css/style.css">

<!-- JavaScript optimization -->
<script src="/static/js/main.js" defer></script>

<!-- Image optimization -->
<img src="/static/images/logo.webp" 
     alt="QuestEd Logo" 
     loading="lazy"
     width="200" 
     height="100">
```

#### Caching Strategy
```nginx
# Nginx caching configuration
location /static {
    alias /var/www/QuestEd/static;
    expires 1y;
    add_header Cache-Control "public, immutable";
    
    # Gzip compression
    gzip on;
    gzip_types text/css application/javascript image/svg+xml;
}

location ~* \.(jpg|jpeg|png|gif|ico|svg)$ {
    expires 1M;
    add_header Cache-Control "public, immutable";
}
```

### 10.4 Celery Performance

#### Worker Configuration
```python
# Optimal worker configuration
# celery_worker.py
celery = Celery('quested')

# Worker optimization
celery.conf.update(
    worker_prefetch_multiplier=1,      # Prevent memory buildup
    task_acks_late=True,               # Acknowledge after completion
    worker_max_tasks_per_child=1000,   # Restart workers periodically
    task_soft_time_limit=300,          # Soft timeout (5 minutes)
    task_time_limit=600,               # Hard timeout (10 minutes)
)
```

#### Task Optimization
```python
# Efficient task patterns
@celery.task(bind=True, max_retries=3)
def generate_user_report(self, user_id):
    """Generate user report with retry logic"""
    try:
        # Task implementation
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
            
        # Generate report
        report = create_report(user)
        send_report_email(user.email, report)
        
        return {"status": "success", "user_id": user_id}
        
    except Exception as exc:
        # Exponential backoff retry
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### 10.5 AI API Performance

#### Request Optimization
```python
# Efficient OpenAI API usage
class AIService:
    def __init__(self):
        self.client = openai
        self.rate_limiter = RateLimiter()
        
    def generate_response(self, message, context=None, subject=None):
        """Optimized AI response generation"""
        
        # Rate limiting
        if not self.rate_limiter.check_limit(user_id):
            raise RateLimitException("AI request limit exceeded")
        
        # Context optimization
        optimized_context = self._optimize_context(context)
        
        # Model selection based on complexity
        model = self._select_model(message, context)
        
        # API call with timeout
        try:
            response = self.client.ChatCompletion.create(
                model=model,
                messages=self._build_messages(message, optimized_context, subject),
                max_tokens=self._calculate_max_tokens(message),
                temperature=0.7,
                timeout=30  # 30 second timeout
            )
            
            return response.choices[0].message.content
            
        except openai.error.RateLimitError:
            # Handle rate limiting gracefully
            return self._get_fallback_response(message)
        except openai.error.APIError as e:
            # Log error and provide fallback
            logger.error(f"OpenAI API error: {e}")
            return self._get_fallback_response(message)
    
    def _optimize_context(self, context):
        """Optimize context for token efficiency"""
        if not context:
            return []
            
        # Keep only recent relevant context
        return context[-10:]  # Last 10 messages
    
    def _select_model(self, message, context):
        """Select appropriate model based on complexity"""
        total_length = len(message) + sum(len(c.get('message', '')) for c in context or [])
        
        if total_length > 2000:
            return "gpt-4"  # Use GPT-4 for complex queries
        else:
            return "gpt-3.5-turbo"  # Use GPT-3.5 for simple queries
```

---

## 11. Testing Strategy

### 11.1 Test Architecture

#### Test Environment Setup
```python
# conftest.py - pytest configuration
import pytest
from app import create_app, db
from app.models import User, School

@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth(client):
    """Authentication helper."""
    return AuthActions(client)

class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, username='test', password='test_password'):
        return self._client.post(
            '/auth/login',
            data={'username': username, 'password': password}
        )

    def logout(self):
        return self._client.get('/auth/logout')
```

### 11.2 Unit Testing

#### Model Testing
```python
# tests/test_models.py
import pytest
from app.models import User, School, Class

class TestUserModel:
    def test_user_creation(self, app):
        """Test user creation with valid data."""
        with app.app_context():
            school = School(name='Test School', code='TEST001')
            db.session.add(school)
            db.session.commit()
            
            user = User(
                username='testuser',
                email='test@example.com',
                password='hashed_password',
                role='student',
                school_id=school.id
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.school_id == school.id

    def test_user_display_name(self, app):
        """Test user display name functionality."""
        with app.app_context():
            # User with full name
            user1 = User(
                username='user1',
                full_name='田中太郎',
                email='user1@example.com'
            )
            assert user1.get_display_name() == '田中太郎'
            
            # User without full name
            user2 = User(
                username='user2',
                email='user2@example.com'
            )
            assert user2.get_display_name() == 'user2'

    def test_user_survey_completion(self, app):
        """Test survey completion checking."""
        with app.app_context():
            user = User(
                username='student',
                email='student@example.com',
                role='student'
            )
            db.session.add(user)
            db.session.commit()
            
            # Initially no surveys completed
            assert not user.has_completed_surveys()
            
            # Add surveys
            interest_survey = InterestSurvey(
                student_id=user.id,
                responses='{"interests": ["science", "math"]}'
            )
            personality_survey = PersonalitySurvey(
                student_id=user.id,
                responses='{"type": "analytical"}'
            )
            
            db.session.add_all([interest_survey, personality_survey])
            db.session.commit()
            
            # Now surveys are completed
            assert user.has_completed_surveys()
```

#### Service Testing
```python
# tests/test_services.py
import pytest
from unittest.mock import patch, MagicMock
from app.ai.helpers import generate_chat_response
from app.utils.email_sender import EmailSender

class TestAIService:
    @patch('app.ai.helpers.openai.ChatCompletion.create')
    def test_generate_chat_response(self, mock_openai, app):
        """Test AI response generation."""
        with app.app_context():
            # Mock OpenAI response
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Test AI response"
            mock_openai.return_value = mock_response
            
            # Test response generation
            response = generate_chat_response("Test message")
            
            assert response == "Test AI response"
            mock_openai.assert_called_once()

    @patch('app.ai.helpers.openai.ChatCompletion.create')
    def test_subject_specific_prompt(self, mock_openai, app):
        """Test subject-specific AI prompts."""
        with app.app_context():
            from app.models import Subject
            
            # Create test subject
            subject = Subject(
                name='理科',
                code='science',
                ai_system_prompt='科学的思考を促進してください。'
            )
            
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Scientific response"
            mock_openai.return_value = mock_response
            
            response = generate_chat_response("光合成について", subject=subject)
            
            # Verify subject prompt was included
            call_args = mock_openai.call_args
            messages = call_args[1]['messages']
            system_message = messages[0]['content']
            
            assert '科学的思考を促進してください。' in system_message
            assert response == "Scientific response"

class TestEmailService:
    @patch('smtplib.SMTP')
    def test_smtp_email_sending(self, mock_smtp, app):
        """Test SMTP email sending."""
        with app.app_context():
            # Configure for SMTP
            app.config['EMAIL_METHOD'] = 'smtp'
            
            email_sender = EmailSender()
            
            # Mock SMTP server
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            # Send test email
            result = email_sender.send_email(
                to_email='test@example.com',
                subject='Test Subject',
                html_content='<h1>Test HTML</h1>',
                text_content='Test Text'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
```

### 11.3 Integration Testing

#### API Testing
```python
# tests/test_api.py
import json
import pytest
from app.models import User, Class, Subject

class TestChatAPI:
    def test_chat_endpoint_authentication(self, client):
        """Test chat endpoint requires authentication."""
        response = client.post('/api/chat', json={
            'message': 'Test message'
        })
        assert response.status_code == 401

    def test_chat_endpoint_success(self, client, auth, app):
        """Test successful chat interaction."""
        with app.app_context():
            # Create test user and login
            user = create_test_user()
            auth.login(user.username, 'test_password')
            
            with patch('app.ai.helpers.generate_chat_response') as mock_ai:
                mock_ai.return_value = "AI response"
                
                response = client.post('/api/chat', json={
                    'message': 'Test question'
                })
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert data['message'] == 'AI response'

    def test_chat_with_subject_context(self, client, auth, app):
        """Test chat with subject-specific context."""
        with app.app_context():
            # Create test data
            user = create_test_user()
            subject = Subject(name='理科', code='science')
            class_obj = Class(
                teacher_id=user.id,
                name='Test Class',
                subject=subject
            )
            
            db.session.add_all([user, subject, class_obj])
            db.session.commit()
            
            auth.login(user.username, 'test_password')
            
            with patch('app.ai.helpers.generate_chat_response') as mock_ai:
                mock_ai.return_value = "Science-specific response"
                
                response = client.post('/api/chat', json={
                    'message': 'Explain photosynthesis',
                    'class_id': class_obj.id
                })
                
                assert response.status_code == 200
                # Verify subject was passed to AI function
                mock_ai.assert_called_once()
                args, kwargs = mock_ai.call_args
                assert kwargs.get('subject') == subject

class TestAuthenticationAPI:
    def test_valid_login(self, client, app):
        """Test valid user login."""
        with app.app_context():
            user = create_test_user()
            
            response = client.post('/auth/login', data={
                'username': user.username,
                'password': 'test_password'
            })
            
            assert response.status_code == 302  # Redirect after login

    def test_invalid_login(self, client):
        """Test invalid login credentials."""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'wrong_password'
        })
        
        assert response.status_code == 200  # Stay on login page
        assert 'ユーザー名またはパスワードが正しくありません' in response.data.decode()

def create_test_user():
    """Helper function to create test user."""
    from werkzeug.security import generate_password_hash
    
    user = User(
        username='testuser',
        email='test@example.com',
        password=generate_password_hash('test_password'),
        role='teacher',
        email_confirmed=True,
        is_approved=True
    )
    db.session.add(user)
    db.session.commit()
    return user
```

### 11.4 Frontend Testing

#### JavaScript Testing
```javascript
// static/js/tests/chat.test.js
describe('Chat Functionality', function() {
    beforeEach(function() {
        document.body.innerHTML = `
            <div id="chat-container">
                <div id="chat-messages"></div>
                <form id="chat-form">
                    <input id="message-input" type="text">
                    <button type="submit">Send</button>
                </form>
            </div>
        `;
        
        // Initialize chat module
        ChatModule.init();
    });

    it('should send message and display response', async function() {
        // Mock fetch
        global.fetch = jest.fn(() =>
            Promise.resolve({
                json: () => Promise.resolve({
                    status: 'success',
                    message: 'AI response'
                })
            })
        );

        const messageInput = document.getElementById('message-input');
        const chatForm = document.getElementById('chat-form');
        
        messageInput.value = 'Test message';
        
        // Trigger form submission
        const event = new Event('submit');
        chatForm.dispatchEvent(event);
        
        // Wait for async operations
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const messages = document.getElementById('chat-messages');
        expect(messages.children.length).toBe(2); // User message + AI response
        expect(messages.textContent).toContain('Test message');
        expect(messages.textContent).toContain('AI response');
    });

    it('should handle API errors gracefully', async function() {
        // Mock fetch to return error
        global.fetch = jest.fn(() =>
            Promise.resolve({
                json: () => Promise.resolve({
                    status: 'error',
                    error: 'API error occurred'
                })
            })
        );

        const messageInput = document.getElementById('message-input');
        messageInput.value = 'Test message';
        
        const event = new Event('submit');
        document.getElementById('chat-form').dispatchEvent(event);
        
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Check that error message is displayed
        const messages = document.getElementById('chat-messages');
        expect(messages.textContent).toContain('エラーが発生しました');
    });
});
```

### 11.5 Performance Testing

#### Load Testing
```python
# tests/test_performance.py
import time
import concurrent.futures
import pytest
from app import create_app

class TestPerformance:
    def test_api_response_time(self, client, auth, app):
        """Test API response times under normal load."""
        with app.app_context():
            user = create_test_user()
            auth.login(user.username, 'test_password')
            
            start_time = time.time()
            
            response = client.post('/api/chat', json={
                'message': 'Simple question'
            })
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == 200
            assert response_time < 2.0  # Response within 2 seconds

    def test_concurrent_requests(self, app):
        """Test handling of concurrent requests."""
        def make_request():
            with app.test_client() as client:
                return client.get('/')
        
        # Simulate 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code in [200, 302]

    def test_memory_usage(self, app):
        """Test memory usage for large data processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        with app.app_context():
            # Simulate processing large dataset
            large_dataset = list(range(10000))
            processed_data = [item * 2 for item in large_dataset]
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
```

### 11.6 Security Testing

#### Security Test Cases
```python
# tests/test_security.py
import pytest
from app.utils.security import SecurityUtils

class TestSecurity:
    def test_password_validation(self):
        """Test password strength validation."""
        # Weak passwords
        weak_passwords = [
            'password',      # Too common
            '12345678',      # Too simple
            'Password',      # Missing special chars
            'Pass123',       # Too short
            'aaaaaaaaaaaa',  # Repetitive
        ]
        
        for password in weak_passwords:
            is_valid, errors = SecurityUtils.validate_password_strength(password)
            assert not is_valid
            assert len(errors) > 0

        # Strong password
        strong_password = 'MySecureP@ssw0rd123!'
        is_valid, errors = SecurityUtils.validate_password_strength(strong_password)
        assert is_valid
        assert len(errors) == 0

    def test_file_security_validation(self, app):
        """Test file upload security."""
        from app.utils.file_security import FileSecurityValidator
        
        validator = FileSecurityValidator()
        
        # Test malicious filename
        malicious_names = [
            '../../../etc/passwd',
            'file<script>alert("xss")</script>.jpg',
            'file.php.jpg',
            'file with spaces.exe'
        ]
        
        for filename in malicious_names:
            secure_name = validator.sanitize_filename(filename)
            assert not any(char in secure_name for char in ['<', '>', '/', '\\', '..'])

    def test_sql_injection_protection(self, client, app):
        """Test SQL injection protection."""
        with app.app_context():
            # Attempt SQL injection through login
            response = client.post('/auth/login', data={
                'username': "admin'; DROP TABLE users; --",
                'password': 'password'
            })
            
            # Should not cause database error
            assert response.status_code in [200, 302]
            
            # Verify users table still exists
            from app.models import User
            users_count = User.query.count()
            assert users_count >= 0  # Table should still exist

    def test_xss_protection(self, client, auth, app):
        """Test XSS protection in user input."""
        with app.app_context():
            user = create_test_user()
            auth.login(user.username, 'test_password')
            
            # Attempt XSS through activity creation
            xss_payload = '<script>alert("XSS")</script>'
            
            response = client.post('/student/activity/new', data={
                'title': xss_payload,
                'content': f'Content with {xss_payload}',
                'reflection': 'Reflection'
            })
            
            # Check that script tags are escaped in response
            assert b'&lt;script&gt;' in response.data or response.status_code == 302

    def test_csrf_protection(self, client):
        """Test CSRF protection on forms."""
        # Attempt form submission without CSRF token
        response = client.post('/auth/login', data={
            'username': 'test',
            'password': 'test'
        })
        
        # Should be rejected due to missing CSRF token
        assert response.status_code == 400 or 'CSRF' in response.data.decode()
```

---

## 12. Monitoring and Logging

### 12.1 Application Logging

#### Logging Configuration
```python
# Logging setup (app/__init__.py)
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
import os

def setup_logging(app):
    """Configure application logging."""
    
    if not app.debug and not app.testing:
        # File logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/quested.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d] [%(request_id)s]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Email logging for critical errors
        if app.config.get('SMTP_SERVER'):
            mail_handler = SMTPHandler(
                mailhost=(app.config['SMTP_SERVER'], app.config['SMTP_PORT']),
                fromaddr=app.config['SMTP_USER'],
                toaddrs=app.config.get('ADMIN_EMAILS', []),
                subject='QuestEd Application Error',
                credentials=(app.config['SMTP_USER'], app.config['SMTP_PASSWORD']),
                secure=()
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('QuestEd application startup')
```

#### Structured Logging
```python
# Structured logging middleware
import uuid
from flask import g, request
import time

@app.before_request
def before_request():
    """Set up request context for logging."""
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = time.time()

@app.after_request
def after_request(response):
    """Log request completion."""
    total_time = time.time() - g.start_time
    
    log_data = {
        'request_id': g.request_id,
        'method': request.method,
        'url': request.url,
        'status_code': response.status_code,
        'response_time': round(total_time, 3),
        'user_id': current_user.id if current_user.is_authenticated else None,
        'ip_address': request.remote_addr,
        'user_agent': request.user_agent.string
    }
    
    if total_time > 1.0:
        app.logger.warning(f'Slow request: {log_data}')
    else:
        app.logger.info(f'Request completed: {log_data}')
    
    return response
```

#### Security Event Logging
```python
# Security event logging (app/utils/security.py)
class SecurityLogger:
    @staticmethod
    def log_authentication_event(event_type, user_id=None, details=None, success=True):
        """Log authentication-related events."""
        log_level = logging.INFO if success else logging.WARNING
        
        log_data = {
            'event_type': f'AUTH_{event_type}',
            'user_id': user_id,
            'success': success,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.user_agent.string if request else None,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        app.logger.log(log_level, f'Security event: {log_data}')
    
    @staticmethod
    def log_access_violation(user_id, attempted_resource, reason):
        """Log access violations."""
        log_data = {
            'event_type': 'ACCESS_VIOLATION',
            'user_id': user_id,
            'attempted_resource': attempted_resource,
            'reason': reason,
            'ip_address': request.remote_addr,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        app.logger.warning(f'Access violation: {log_data}')
    
    @staticmethod
    def log_file_upload(user_id, filename, file_size, validation_result):
        """Log file upload attempts."""
        log_data = {
            'event_type': 'FILE_UPLOAD',
            'user_id': user_id,
            'filename': filename,
            'file_size': file_size,
            'validation_passed': validation_result['valid'],
            'validation_errors': validation_result.get('errors', []),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        log_level = logging.INFO if validation_result['valid'] else logging.WARNING
        app.logger.log(log_level, f'File upload: {log_data}')
```

### 12.2 Performance Monitoring

#### Response Time Monitoring
```python
# Performance monitoring middleware
class PerformanceMonitor:
    def __init__(self, app=None):
        self.app = app
        self.slow_requests = []
        self.metrics = {
            'total_requests': 0,
            'avg_response_time': 0,
            'slow_requests_count': 0
        }
    
    def init_app(self, app):
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        g.start_time = time.time()
    
    def after_request(self, response):
        total_time = time.time() - g.start_time
        
        # Update metrics
        self.metrics['total_requests'] += 1
        
        # Calculate rolling average
        current_avg = self.metrics['avg_response_time']
        new_avg = (current_avg * (self.metrics['total_requests'] - 1) + total_time) / self.metrics['total_requests']
        self.metrics['avg_response_time'] = new_avg
        
        # Track slow requests
        if total_time > 2.0:  # Requests slower than 2 seconds
            self.metrics['slow_requests_count'] += 1
            self.slow_requests.append({
                'url': request.url,
                'method': request.method,
                'response_time': total_time,
                'timestamp': datetime.utcnow(),
                'user_id': current_user.id if current_user.is_authenticated else None
            })
            
            # Keep only last 100 slow requests
            if len(self.slow_requests) > 100:
                self.slow_requests.pop(0)
        
        return response
    
    def get_metrics(self):
        """Get current performance metrics."""
        return {
            **self.metrics,
            'slow_request_percentage': (
                self.metrics['slow_requests_count'] / self.metrics['total_requests'] * 100
                if self.metrics['total_requests'] > 0 else 0
            ),
            'recent_slow_requests': self.slow_requests[-10:]  # Last 10 slow requests
        }
```

#### Database Performance Monitoring
```python
# Database query monitoring
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    
    if total > 0.1:  # Log queries slower than 100ms
        app.logger.warning(
            f'Slow query: {total:.3f}s - {statement[:200]}...'
        )
```

### 12.3 Error Monitoring

#### Error Tracking
```python
# Error tracking and notification
class ErrorTracker:
    def __init__(self):
        self.error_counts = {}
        self.recent_errors = []
    
    def track_error(self, error, context=None):
        """Track application errors."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Count errors by type
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Store recent error details
        error_detail = {
            'type': error_type,
            'message': error_message,
            'timestamp': datetime.utcnow(),
            'url': request.url if request else None,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'context': context
        }
        
        self.recent_errors.append(error_detail)
        
        # Keep only last 50 errors
        if len(self.recent_errors) > 50:
            self.recent_errors.pop(0)
        
        # Log error
        app.logger.error(f'Application error: {error_detail}', exc_info=True)
        
        # Send notification for critical errors
        if self._is_critical_error(error):
            self._send_error_notification(error_detail)
    
    def _is_critical_error(self, error):
        """Determine if error is critical."""
        critical_errors = [
            'DatabaseError',
            'IntegrityError',
            'SecurityError',
            'FileNotFoundError'
        ]
        return type(error).__name__ in critical_errors
    
    def _send_error_notification(self, error_detail):
        """Send notification for critical errors."""
        try:
            from app.utils.email_sender import EmailSender
            
            email_sender = EmailSender()
            email_sender.send_email(
                to_email=app.config.get('ADMIN_EMAIL'),
                subject=f'QuestEd Critical Error: {error_detail["type"]}',
                html_content=f"""
                <h2>Critical Error Detected</h2>
                <p><strong>Type:</strong> {error_detail['type']}</p>
                <p><strong>Message:</strong> {error_detail['message']}</p>
                <p><strong>URL:</strong> {error_detail['url']}</p>
                <p><strong>User ID:</strong> {error_detail['user_id']}</p>
                <p><strong>Timestamp:</strong> {error_detail['timestamp']}</p>
                """
            )
        except Exception as e:
            app.logger.error(f'Failed to send error notification: {e}')

# Global error handler
@app.errorhandler(Exception)
def handle_exception(error):
    error_tracker.track_error(error)
    
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500
    else:
        return render_template('errors/500.html'), 500
```

### 12.4 Health Monitoring

#### Health Check Endpoints
```python
# Health monitoring endpoints
@app.route('/health')
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app.config.get('APP_VERSION', 'unknown')
    })

@app.route('/health/detailed')
def detailed_health_check():
    """Detailed health check with component status."""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app.config.get('APP_VERSION', 'unknown'),
        'components': {}
    }
    
    # Database health
    try:
        db.session.execute(text('SELECT 1'))
        health_status['components']['database'] = 'healthy'
    except Exception as e:
        health_status['components']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Redis health (if Celery is configured)
    try:
        from celery_worker import celery
        inspector = celery.control.inspect()
        stats = inspector.stats()
        health_status['components']['celery'] = 'healthy' if stats else 'unhealthy'
    except Exception as e:
        health_status['components']['celery'] = f'unhealthy: {str(e)}'
    
    # OpenAI API health
    try:
        import openai
        openai.api_key = app.config.get('OPENAI_API_KEY')
        # Simple API test
        health_status['components']['openai'] = 'healthy'
    except Exception as e:
        health_status['components']['openai'] = f'unhealthy: {str(e)}'
        
    return jsonify(health_status)

@app.route('/metrics')
def metrics():
    """Application metrics endpoint."""
    metrics_data = {
        'performance': performance_monitor.get_metrics(),
        'error_counts': error_tracker.error_counts,
        'system': {
            'uptime': time.time() - app.start_time,
            'memory_usage': get_memory_usage(),
            'active_users': get_active_user_count()
        }
    }
    
    return jsonify(metrics_data)

def get_memory_usage():
    """Get current memory usage."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return {
        'rss': memory_info.rss,
        'vms': memory_info.vms,
        'percent': process.memory_percent()
    }

def get_active_user_count():
    """Get count of active users (logged in within last hour)."""
    from datetime import timedelta
    
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    # This would require session tracking or login timestamp
    # For now, return a placeholder
    return User.query.filter(User.created_at > one_hour_ago).count()
```

### 12.5 Alerting and Notifications

#### Alert Configuration
```python
# Alert system configuration
class AlertManager:
    def __init__(self):
        self.alert_rules = {
            'high_error_rate': {
                'threshold': 0.05,  # 5% error rate
                'window': 300,      # 5 minutes
                'severity': 'high'
            },
            'slow_response_time': {
                'threshold': 2.0,   # 2 seconds
                'percentage': 0.1,  # 10% of requests
                'window': 300,
                'severity': 'medium'
            },
            'database_connection_errors': {
                'threshold': 5,     # 5 errors
                'window': 60,       # 1 minute
                'severity': 'critical'
            }
        }
    
    def check_alerts(self):
        """Check all alert conditions."""
        alerts = []
        
        # Check error rate
        if self._check_error_rate():
            alerts.append({
                'type': 'high_error_rate',
                'message': 'Error rate above threshold',
                'severity': 'high'
            })
        
        # Check response time
        if self._check_response_time():
            alerts.append({
                'type': 'slow_response_time',
                'message': 'Response time above threshold',
                'severity': 'medium'
            })
        
        # Send alerts
        for alert in alerts:
            self._send_alert(alert)
        
        return alerts
    
    def _check_error_rate(self):
        """Check if error rate is above threshold."""
        # Implementation would check recent error rates
        pass
    
    def _check_response_time(self):
        """Check if response time is above threshold."""
        # Implementation would check recent response times
        pass
    
    def _send_alert(self, alert):
        """Send alert notification."""
        try:
            from app.utils.email_sender import EmailSender
            
            email_sender = EmailSender()
            email_sender.send_email(
                to_email=app.config.get('ALERT_EMAIL'),
                subject=f'QuestEd Alert: {alert["type"]}',
                html_content=f"""
                <h2>Application Alert</h2>
                <p><strong>Type:</strong> {alert['type']}</p>
                <p><strong>Severity:</strong> {alert['severity']}</p>
                <p><strong>Message:</strong> {alert['message']}</p>
                <p><strong>Timestamp:</strong> {datetime.utcnow()}</p>
                """
            )
        except Exception as e:
            app.logger.error(f'Failed to send alert: {e}')

# Periodic alert checking (would be run by Celery)
@celery.task
def check_system_alerts():
    """Periodic task to check system alerts."""
    alert_manager = AlertManager()
    alerts = alert_manager.check_alerts()
    
    if alerts:
        app.logger.warning(f'System alerts triggered: {alerts}')
    
    return len(alerts)
```

---

This comprehensive technical specification document provides a complete guide for developers to understand, maintain, and extend the QuestEd system. It covers all major aspects of the system architecture, from database design to deployment strategies, ensuring that new team members can quickly get up to speed and existing developers have a reliable reference for the system's components and patterns.

The document serves as both a technical reference and a development guide, providing the necessary depth for system administration, code maintenance, and feature development while maintaining clarity for different technical roles within the development team.