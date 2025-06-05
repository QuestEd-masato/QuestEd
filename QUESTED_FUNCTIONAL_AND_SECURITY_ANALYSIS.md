# QuestEd Platform - Functional Analysis and Security Assessment

## Table of Contents
1. [Project Overview](#project-overview)
2. [Functional Analysis](#functional-analysis)
3. [Security Assessment](#security-assessment)
4. [Recommended Improvements](#recommended-improvements)

---

## Project Overview

QuestEd is a Flask-based educational platform designed for Japanese high schools, supporting inquiry-based learning (探究学習) with multi-role support (admin, teacher, student) and integrated AI features.

### Technology Stack
- **Backend**: Flask 2.x (Blueprint architecture)
- **Database**: MySQL (PyMySQL)
- **ORM**: SQLAlchemy (Flask-Migrate)
- **Authentication**: Flask-Login
- **Admin**: Flask-Admin
- **Frontend**: Jinja2 templates, JavaScript, CSS
- **AI Integration**: OpenAI API (GPT-4, GPT-3.5-turbo)
- **Other**: Email (SMTP), PDF generation, CSV processing

---

## Functional Analysis

### 1. User Roles and Permissions

#### Administrator (Admin)
- User management (create, delete, view all)
- School management (issue school codes)
- School year and class group management
- System-wide statistics and monitoring
- Access to Flask-Admin interface

#### Teacher
- Class creation and management
- Student account approval for their school
- Create main themes (大テーマ)
- AI-powered curriculum generation
- Student evaluation with AI assistance
- Milestone creation and progress tracking
- Batch student import via CSV
- Export evaluations and activities to PDF/CSV
- Learning path management in BaseBuilder module

#### Student
- Complete interest and personality surveys
- Select personal inquiry themes
- Log activities with image uploads
- Manage todos and goals
- Submit milestone assignments
- Access AI learning support chat
- Participate in BaseBuilder training system

### 2. Core Features

#### Authentication & Registration System
- Email-based registration with verification
- School code requirement for registration
- Teacher approval required for students
- Password reset functionality
- Multi-factor authentication flow:
  1. Email verification
  2. Teacher approval (students only)
  3. Login access granted

#### School Management System
- **Schools**: Unique entities with codes
- **School Years**: Academic year tracking (e.g., 2023-2024)
- **Class Groups**: Classes within school years
- **Student Enrollment**: Year-based student-class relationships

#### Inquiry Learning System
1. **Main Themes**: Teacher-created class-wide themes
2. **Personal Themes**: AI-generated based on student surveys
3. **Activity Logging**: Students document learning journey
4. **Milestones**: Periodic assessment points
5. **Evaluation System**: AI-assisted teacher evaluations

#### AI Integration Features
- **Theme Generation**: Creates 3 personalized themes per student
- **Curriculum Generation**: Complete curriculum with schedules
- **Student Evaluation**: AI-assisted based on activities and progress
- **Chat Assistant**: Educational support chatbot
- **Activity Summaries**: AI-generated summaries of student work

#### BaseBuilder Module
Comprehensive learning management system for basic skills:
- Problem categories and knowledge items
- Text-based comprehension exercises
- Learning path management
- Proficiency tracking and analytics
- Word-level mastery tracking
- Teacher-student progress monitoring

### 3. Data Models

#### Core User System
- `User`: Multi-role users with school association
- `School`: Educational institutions with unique codes
- `SchoolYear`: Academic year management
- `ClassGroup`: Classes within school years
- `StudentEnrollment`: Student-class relationships

#### Educational Content
- `Class`: Teacher-owned classes
- `MainTheme`: Class-level inquiry themes
- `InquiryTheme`: Student personal themes (AI-generated)
- `Curriculum`: AI-generated curriculum with JSON data
- `Milestone`: Student submission deadlines
- `RubricTemplate`: Evaluation criteria templates

#### Student Data
- `InterestSurvey`: Interest data (JSON)
- `PersonalitySurvey`: Personality traits (JSON)
- `ActivityLog`: Daily learning activities with images
- `Todo`: Task management
- `Goal`: Goal tracking (0-100%)
- `StudentEvaluation`: Teacher evaluations with AI support

#### Collaboration
- `Group`: Student groups within classes
- `GroupMembership`: Group participant tracking
- `ChatHistory`: AI chat conversation logs

### 4. External Integrations

#### OpenAI API
- GPT-4 for theme and curriculum generation
- GPT-3.5-turbo for chat and evaluations
- Custom prompts for educational context
- Error handling with fallback responses

#### Email Service
- SMTP integration via Gmail
- Email verification for new accounts
- Password reset functionality
- Approval notification system

#### File Storage
- Image uploads for activity logs
- PDF generation for reports
- CSV import/export functionality
- Maximum file size: 16MB

---

## Security Assessment

### Vulnerability Summary by Severity

#### 🔴 Critical (2)
1. **No File Type Validation for Uploads**
   - Location: `/app/student/__init__.py` (lines 452-470)
   - No content validation for uploaded files
   - Malicious files (PHP, executables) can be uploaded

2. **XSS Vulnerability in nl2br Filter**
   - Location: `/app/__init__.py` (lines 104-112)
   - Use of `Markup()` introduces XSS risk

#### 🟠 High (7)
1. **Weak Password Policy**
   - Minimum 8 characters, no complexity requirements
   - Vulnerable to brute force attacks

2. **User-Generated Content XSS Risk**
   - Multiple templates use `nl2br` filter
   - Stored XSS attacks possible

3. **Secret Key Management**
   - No validation when loading from environment
   - Weak keys compromise session security

4. **Uploaded Files in Static Directory**
   - Files in `static/uploads/` directly accessible
   - Could be executed if web server misconfigured

5. **OpenAI API Key Exposure Risk**
   - No API key validation
   - Could be exposed if misconfigured

6. **Debug Mode in Production Risk**
   - Debug mode can be enabled via environment
   - Stack traces and sensitive info exposed

7. **CSV Import Injection**
   - No sanitization of CSV data
   - Formula injection attacks possible

#### 🟡 Medium (6)
1. **Password Reset Token Validity**
   - 1 hour is too long (recommend 15-30 minutes)

2. **No Session Timeout Configuration**
   - Sessions may persist indefinitely

3. **No API Rate Limiting**
   - API abuse, DoS attack risk

4. **CSRF Tokens Never Expire**
   - `WTF_CSRF_TIME_LIMIT = None`
   - Tokens can be reused indefinitely

5. **No Dependency Vulnerability Scanning**
   - Risk of known vulnerabilities in dependencies

6. **Weak Random Password Generation**
   - Uses Python's `random` module (not cryptographically secure)

#### 🟢 Low (4)
1. **No Account Lockout**
   - Unlimited login attempts possible

2. **SQL Injection Protection** (Properly implemented)
   - SQLAlchemy ORM usage

3. **CSRF Protection** (Properly implemented)
   - Enabled with Flask-WTF

4. **Information Disclosure in Errors**
   - Error messages reveal system information

### Security Issue Details

#### 1. File Upload Security
```python
# Vulnerable code example
if 'image' in request.files:
    file = request.files['image']
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        # No file type validation!
        file.save(filepath)
```

**Recommended Fix**:
- Validate file headers
- Restrict allowed extensions
- Validate file content
- Move upload directory outside web root

#### 2. XSS Protection
```python
# Current implementation (potential risk)
@app.template_filter('nl2br')
def nl2br(value):
    if not value:
        return value
    import markupsafe
    escaped = markupsafe.escape(value)
    return markupsafe.Markup(str(escaped).replace('\n', '<br>\n'))
```

**Recommended Fix**:
- Review all template usages
- Implement Content Security Policy (CSP)
- Ensure proper output encoding

#### 3. Authentication & Session Management
**Recommended Fix**:
- Strengthen password policy (12+ chars, upper/lower, numbers, special)
- Set session timeout (30 minutes)
- Implement account lockout after failed attempts
- Consider two-factor authentication

---

## Recommended Improvements

### Immediate Actions (High Priority)

1. **File Upload Security**
   - Implement file type validation
   - Move upload directory
   - Enforce strict file size limits

2. **XSS Protection**
   - Review nl2br filter
   - Implement CSP headers
   - Thoroughly sanitize user input

3. **Password Security**
   - Implement strong password policy
   - Use `secrets` module for secure random generation

4. **Session Management**
   - Configure session timeout
   - Secure secret key management

### Medium-term Improvements

1. **API Security**
   - Implement rate limiting (Flask-Limiter)
   - Strengthen API authentication
   - Per-endpoint access control

2. **Auditing and Logging**
   - Security event logging
   - Anomaly detection system
   - Regular security audits

3. **Dependency Management**
   - Automated vulnerability scanning (pip-audit, safety)
   - Regular dependency updates
   - Rapid security patch application

### Long-term Improvements

1. **Architecture Enhancement**
   - Consider microservices
   - API-first architecture migration
   - Containerization and orchestration

2. **Compliance and Privacy**
   - Enhanced data encryption
   - GDPR and privacy law compliance
   - Privacy by design implementation

3. **Disaster Recovery**
   - Automated backup system
   - Disaster recovery planning
   - Regular recovery testing

### Security Best Practices

1. **Development Process**
   - Secure coding guidelines
   - Security checks in code reviews
   - Automated security testing

2. **Operations**
   - Principle of least privilege
   - Regular security updates
   - Incident response plan

3. **Education and Training**
   - Developer security training
   - User security awareness
   - Regular security drills

---

## Conclusion

QuestEd is a feature-rich platform that meets educational needs, but has several important security issues. File upload and XSS vulnerabilities require immediate attention.

By implementing the recommended improvements, QuestEd can continue to provide value to students and teachers as a more secure and reliable educational platform.

Through continuous security improvements and feature enhancements based on educational feedback, QuestEd has the potential to evolve as an important tool supporting inquiry-based learning in Japan.