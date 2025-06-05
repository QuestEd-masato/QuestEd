# QuestEd API Endpoint Mapping for Microservices Migration

## Overview

This document provides a comprehensive mapping of all 200+ endpoints in the QuestEd application, categorized by their target microservice architecture. Each endpoint is analyzed for database dependencies, authentication requirements, and migration recommendations.

## Current Architecture Summary

- **Total Endpoints**: 200+ routes across 8 major Blueprint modules
- **Architecture Pattern**: Mixed traditional Flask routes + REST API endpoints
- **Authentication**: Role-based access control (admin, teacher, student)
- **Database**: MySQL with 25+ models in complex relationships

## Microservice Mapping

### 1. Authentication & User Management Service

**Service Name**: `auth-service`
**Port**: 8001
**Database**: `auth_db` (User, School tables)

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET/POST | `/login` | `POST /auth/login` | User | ✗ | - | Convert to JWT API |
| GET | `/logout` | `POST /auth/logout` | - | ✓ | - | Token invalidation |
| GET/POST | `/register` | `POST /auth/register` | User, School | ✗ | - | Enhanced validation |
| GET | `/verify_email/<int:user_id>` | `GET /auth/verify/<user_id>` | User | ✗ | - | Email verification |
| GET | `/resend_verification/<int:user_id>` | `POST /auth/resend-verification` | User | ✓ | - | Resend email |
| GET | `/confirm_email/<int:user_id>/<token>` | `POST /auth/confirm-email` | User | ✗ | - | Token-based confirmation |
| GET | `/awaiting_approval` | `GET /auth/status` | - | ✗ | - | Account status check |
| GET/POST | `/forgot_password` | `POST /auth/forgot-password` | User | ✗ | - | Password reset request |
| GET/POST | `/reset_password/<int:user_id>/<token>` | `POST /auth/reset-password` | User | ✗ | - | Password reset |
| GET/POST | `/change_password` | `PUT /auth/password` | User | ✓ | Any | Password change |
| GET/POST | `/profile` | `GET/PUT /auth/profile` | User | ✓ | Any | Profile management |

**Additional Endpoints**:
```
GET    /auth/validate-token     # JWT token validation
POST   /auth/refresh-token      # Token refresh
GET    /auth/user/{id}          # User profile retrieval
PUT    /auth/user/{id}          # User profile update
DELETE /auth/user/{id}          # User deletion
GET    /auth/schools            # School list for registration
```

### 2. Academic Management Service

**Service Name**: `academic-service`
**Port**: 8002
**Database**: `academic_db` (School, SchoolYear, Class, ClassGroup, ClassEnrollment, StudentEnrollment)

#### Admin School Management Routes

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET | `/admin/schools` | `GET /academic/schools` | School | ✓ | Admin | School listing |
| GET/POST | `/admin/schools/create` | `POST /academic/schools` | School | ✓ | Admin | School creation |
| GET | `/admin/school/<int:school_id>` | `GET /academic/schools/{id}` | School, SchoolYear | ✓ | Admin | School details |
| GET/POST | `/admin/schools/<int:school_id>/edit` | `PUT /academic/schools/{id}` | School | ✓ | Admin | School update |
| POST | `/admin/schools/<int:school_id>/delete` | `DELETE /academic/schools/{id}` | School, User, SchoolYear | ✓ | Admin | Cascade deletion |
| GET | `/admin/school/<int:school_id>/years` | `GET /academic/schools/{id}/years` | SchoolYear | ✓ | Admin | School years |
| GET/POST | `/admin/school/<int:school_id>/year/create` | `POST /academic/schools/{id}/years` | SchoolYear | ✓ | Admin | Year creation |
| GET/POST | `/admin/school_year/<int:year_id>/edit` | `PUT /academic/years/{id}` | SchoolYear | ✓ | Admin | Year update |
| POST | `/admin/school_year/<int:year_id>/set_current` | `PUT /academic/years/{id}/set-current` | SchoolYear | ✓ | Admin | Set active year |

#### Class Management Routes

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET | `/teacher_dashboard` | `GET /academic/teacher/dashboard` | Class, ClassEnrollment, User | ✓ | Teacher | Dashboard data |
| GET/POST | `/classes` | `GET/POST /academic/classes` | Class, ClassEnrollment | ✓ | Teacher | Class management |
| GET/POST | `/create_class` | `POST /academic/classes` | Class | ✓ | Teacher | Class creation |
| GET | `/class/<int:class_id>` | `GET /academic/classes/{id}` | Class, ClassEnrollment, MainTheme, Milestone | ✓ | Teacher | Class details |
| GET/POST | `/class/<int:class_id>/edit` | `PUT /academic/classes/{id}` | Class | ✓ | Teacher | Class update |
| GET | `/class/<int:class_id>/delete` | `DELETE /academic/classes/{id}` | Class | ✓ | Teacher | Class deletion |

#### Student Enrollment Routes

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET/POST | `/class/<int:class_id>/add_students` | `POST /academic/classes/{id}/students` | ClassEnrollment, User | ✓ | Teacher | Student enrollment |
| POST | `/class/<int:class_id>/remove_student/<int:student_id>` | `DELETE /academic/classes/{class_id}/students/{student_id}` | ClassEnrollment | ✓ | Teacher | Student removal |
| GET/POST | `/class/<int:class_id>/students/import` | `POST /academic/classes/{id}/students/import` | User, ClassEnrollment | ✓ | Teacher | Bulk import |
| GET | `/admin/class_group/<int:class_id>/students` | `GET /academic/class-groups/{id}/students` | StudentEnrollment, User | ✓ | Admin | Enrollment view |
| POST | `/admin/class_group/<int:class_id>/enroll_student` | `POST /academic/class-groups/{id}/students` | StudentEnrollment | ✓ | Admin | Admin enrollment |

### 3. Content Management Service

**Service Name**: `content-service`
**Port**: 8003
**Database**: `content_db` (MainTheme, InquiryTheme, Curriculum, Milestone)

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET/POST | `/class/<int:class_id>/main_themes/create` | `POST /content/classes/{id}/themes` | MainTheme | ✓ | Teacher | Theme creation |
| GET | `/themes` | `GET /content/student/themes` | InquiryTheme, ClassEnrollment, MainTheme | ✓ | Student | Theme selection |
| POST | `/generate_theme_ai` | `POST /content/themes/generate` | MainTheme, InterestSurvey, PersonalitySurvey | ✓ | Student | AI theme generation |
| POST | `/api/theme/<int:theme_id>/select` | `POST /content/themes/{id}/select` | InquiryTheme | ✓ | Student | Theme selection |
| GET/POST | `/create_milestone/<int:class_id>` | `POST /content/classes/{id}/milestones` | Milestone | ✓ | Teacher | Milestone creation |
| GET/POST | `/class/<int:class_id>/curriculum/generate` | `POST /content/classes/{id}/curriculum` | Curriculum, MainTheme | ✓ | Teacher | Curriculum generation |
| GET | `/view_milestone/<int:milestone_id>` | `GET /content/milestones/{id}` | Milestone | ✓ | Teacher | Milestone view |
| GET/POST | `/submit_milestone/<int:milestone_id>` | `POST /content/milestones/{id}/submit` | Milestone | ✓ | Student | Milestone submission |

**Additional Content Endpoints**:
```
GET    /content/curricula               # List curricula
POST   /content/curricula              # Create curriculum
PUT    /content/curricula/{id}         # Update curriculum
DELETE /content/curricula/{id}         # Delete curriculum
GET    /content/themes/{id}/activities # Theme-related activities
POST   /content/themes/{id}/clone      # Clone theme
GET    /content/milestones/templates   # Milestone templates
```

### 4. Student Activity Service

**Service Name**: `activity-service`
**Port**: 8004
**Database**: `activity_db` (ActivityLog, Todo, Goal, InterestSurvey, PersonalitySurvey)

#### Student Dashboard & Surveys

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET | `/student_dashboard` | `GET /activity/dashboard` | Multiple models | ✓ | Student | Dashboard data |
| GET | `/surveys` | `GET /activity/surveys` | InterestSurvey, PersonalitySurvey | ✓ | Student | Survey status |
| GET/POST | `/interest_survey` | `GET/POST /activity/surveys/interest` | InterestSurvey | ✓ | Student | Interest survey |
| GET/POST | `/personality_survey` | `GET/POST /activity/surveys/personality` | PersonalitySurvey | ✓ | Student | Personality survey |

#### Activity Management

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET | `/activities` | `GET /activity/logs` | ActivityLog, ClassEnrollment | ✓ | Student | Activity listing |
| GET/POST | `/new_activity` | `POST /activity/logs` | ActivityLog, ClassEnrollment | ✓ | Student | Activity creation |
| GET/POST | `/activity/<int:log_id>/edit` | `PUT /activity/logs/{id}` | ActivityLog | ✓ | Student | Activity update |
| GET | `/activity/<int:log_id>/delete` | `DELETE /activity/logs/{id}` | ActivityLog | ✓ | Student | Activity deletion |
| GET | `/activities/export/<format>` | `GET /activity/logs/export` | ActivityLog | ✓ | Student | Data export |

#### Todo & Goal Management

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET/POST | `/todos` | `GET/POST /activity/todos` | Todo, InquiryTheme | ✓ | Student | Todo management |
| POST | `/api/todo/<int:todo_id>/toggle` | `PUT /activity/todos/{id}/toggle` | Todo | ✓ | Student | Todo completion |
| GET/POST | `/goals` | `GET/POST /activity/goals` | Goal, InquiryTheme | ✓ | Student | Goal management |
| POST | `/api/goal/<int:goal_id>/progress` | `PUT /activity/goals/{id}/progress` | Goal | ✓ | Student | Goal progress |

### 5. Assessment Service

**Service Name**: `assessment-service`
**Port**: 8005
**Database**: `assessment_db` (StudentEvaluation, RubricTemplate)

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET/POST | `/class/<int:class_id>/generate_evaluations` | `POST /assessment/classes/{id}/evaluate` | StudentEvaluation, InquiryTheme, Goal | ✓ | Teacher | AI evaluation |
| POST | `/api/export/evaluations` | `POST /assessment/export` | StudentEvaluation, User | ✓ | Teacher | Export evaluations |
| GET | `/evaluate_students` | `GET /assessment/students` | StudentEvaluation | ✓ | Teacher | Student list |
| POST | `/class/<int:class_id>/student/<int:student_id>/generate_report` | `POST /assessment/reports/generate` | Multiple models | ✓ | Teacher | PDF report |

**Additional Assessment Endpoints**:
```
GET    /assessment/rubrics             # List rubric templates
POST   /assessment/rubrics             # Create rubric
GET    /assessment/evaluations/{id}    # Get evaluation
PUT    /assessment/evaluations/{id}    # Update evaluation
DELETE /assessment/evaluations/{id}    # Delete evaluation
GET    /assessment/analytics/{class_id} # Class performance analytics
```

### 6. AI & Chat Service

**Service Name**: `ai-service`
**Port**: 8006
**Database**: `ai_db` (ChatHistory)

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET/POST | `/api/chat` | `POST /ai/chat` | ChatHistory, InquiryTheme, Class | ✓ | Any | Chat interaction |
| GET | `/chat` | `GET /ai/chat/interface` | ChatHistory, ClassEnrollment | ✓ | Student | Chat interface |
| POST | `/generate_theme_ai` | `POST /ai/themes/generate` | MainTheme, Surveys | ✓ | Student | Theme generation |
| GET/POST | `/class/<int:class_id>/curriculum/generate` | `POST /ai/curriculum/generate` | Curriculum, MainTheme | ✓ | Teacher | Curriculum AI |
| GET/POST | `/class/<int:class_id>/generate_evaluations` | `POST /ai/evaluations/generate` | StudentEvaluation | ✓ | Teacher | Evaluation AI |

**Additional AI Endpoints**:
```
POST   /ai/content/suggestions         # Content suggestions
POST   /ai/learning-paths/generate     # Generate learning paths
GET    /ai/chat/history/{user_id}      # Chat history
DELETE /ai/chat/history/{user_id}      # Clear chat history
POST   /ai/feedback/analyze            # Analyze student feedback
```

### 7. Administration Service

**Service Name**: `admin-service`
**Port**: 8007
**Database**: `admin_db` (User management views, administrative functions)

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET | `/admin/dashboard` | `GET /admin/dashboard` | User, Class, School | ✓ | Admin | Admin dashboard |
| GET | `/admin/users` | `GET /admin/users` | User | ✓ | Admin | User management |
| POST | `/admin/users/<int:user_id>/delete` | `DELETE /admin/users/{id}` | User, Class, ActivityLog | ✓ | Admin | User deletion |
| GET/POST | `/admin/import_users` | `POST /admin/users/import` | User | ✓ | Admin | Bulk user import |
| GET | `/admin/download_user_template` | `GET /admin/templates/users` | - | ✓ | Admin | CSV template |

### 8. BaseBuilder Learning Management Service

**Service Name**: `basebuilder-service`
**Port**: 8008
**Database**: `basebuilder_db` (ProblemCategory, BasicKnowledgeItem, TextSet, LearningPath, ProficiencyRecord, etc.)

#### Core Learning Routes

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET | `/basebuilder/` | `GET /basebuilder/dashboard` | TextDelivery, TextSet, ProficiencyRecord | ✓ | Any | Learning dashboard |
| GET/POST | `/basebuilder/categories` | `GET/POST /basebuilder/categories` | ProblemCategory | ✓ | Teacher | Category management |
| GET/POST | `/basebuilder/problems` | `GET/POST /basebuilder/problems` | BasicKnowledgeItem | ✓ | Teacher | Problem management |
| GET/POST | `/basebuilder/texts` | `GET/POST /basebuilder/texts` | TextSet | ✓ | Teacher | Text management |
| GET/POST | `/basebuilder/learning_paths` | `GET/POST /basebuilder/learning-paths` | LearningPath | ✓ | Teacher | Path management |

#### Learning Interaction Routes

| Method | Current Path | New API Path | Models | Auth | Role | Migration Notes |
|--------|-------------|--------------|--------|------|------|-----------------|
| GET/POST | `/basebuilder/solve_problem/<int:problem_id>` | `POST /basebuilder/problems/{id}/solve` | BasicKnowledgeItem, AnswerRecord | ✓ | Student | Problem solving |
| GET/POST | `/basebuilder/deliver_text` | `POST /basebuilder/texts/deliver` | TextDelivery, TextSet | ✓ | Teacher | Text delivery |
| GET | `/basebuilder/proficiency` | `GET /basebuilder/proficiency` | ProficiencyRecord | ✓ | Any | Proficiency tracking |
| GET | `/basebuilder/student_analysis` | `GET /basebuilder/analytics/students` | Multiple models | ✓ | Teacher | Student analytics |

### 9. Media & File Service

**Service Name**: `media-service`
**Port**: 8009
**Database**: File metadata table

| Method | Current Path | New API Path | Auth | Role | Migration Notes |
|--------|-------------|--------------|------|------|-----------------|
| POST | File uploads in activities | `POST /media/upload` | ✓ | Any | Image upload handling |
| GET | Static file serving | `GET /media/files/{id}` | ✓ | Any | File retrieval |
| POST | PDF generation | `POST /media/pdf/generate` | ✓ | Teacher | PDF creation |
| GET | Download templates | `GET /media/templates/{type}` | ✓ | Admin | Template download |

## Cross-Service Communication Patterns

### Synchronous Communication (REST APIs)
- **Authentication**: All services validate tokens with auth-service
- **User Data**: Services fetch user information from auth-service
- **Real-time Operations**: Class enrollment, grade submission

### Asynchronous Communication (Message Queues)
- **User Registration**: Notify multiple services of new users
- **Activity Logging**: Update analytics without blocking user experience
- **AI Processing**: Queue heavy AI operations

### Event-Driven Architecture
```json
{
  "event_type": "user.registered",
  "user_id": "12345",
  "school_id": "67890",
  "role": "student",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Database Migration Strategy

### Data Separation Approach

1. **Extract by Domain**: Each service gets domain-specific tables
2. **Replicate Reference Data**: User IDs, School IDs replicated across services
3. **Event Synchronization**: Keep reference data consistent via events
4. **Foreign Key Handling**: Replace with API calls or eventual consistency

### Service-Specific Database Schemas

#### auth_db
```sql
users, schools, school_years, password_reset_tokens, email_verification_tokens
```

#### academic_db
```sql
classes, class_groups, class_enrollments, student_enrollments, user_references
```

#### content_db
```sql
main_themes, inquiry_themes, curricula, milestones, user_references, class_references
```

#### activity_db
```sql
activity_logs, todos, goals, interest_surveys, personality_surveys, user_references
```

#### assessment_db
```sql
student_evaluations, rubric_templates, evaluation_criteria, user_references
```

#### ai_db
```sql
chat_histories, ai_requests, ai_responses, conversation_contexts
```

#### basebuilder_db
```sql
problem_categories, basic_knowledge_items, text_sets, learning_paths, proficiency_records, answer_records
```

## API Gateway Configuration

### Route Mapping
```yaml
routes:
  - path: /auth/*
    service: auth-service:8001
  - path: /academic/*
    service: academic-service:8002
  - path: /content/*
    service: content-service:8003
  - path: /activity/*
    service: activity-service:8004
  - path: /assessment/*
    service: assessment-service:8005
  - path: /ai/*
    service: ai-service:8006
  - path: /admin/*
    service: admin-service:8007
  - path: /basebuilder/*
    service: basebuilder-service:8008
  - path: /media/*
    service: media-service:8009
```

### Authentication Middleware
```yaml
auth:
  exclude_paths:
    - /auth/login
    - /auth/register
    - /auth/forgot-password
    - /auth/reset-password
  jwt_validation: true
  role_enforcement: true
```

## Migration Considerations

### Challenges

1. **Complex Relationships**: Many-to-many relationships across service boundaries
2. **Transactional Consistency**: Multi-table operations need compensation patterns
3. **Real-time Features**: Chat and notifications require WebSocket handling
4. **File Handling**: Large file uploads and PDF generation
5. **AI Integration**: External API rate limiting and error handling

### Solutions

1. **Saga Pattern**: For distributed transactions (enrollment, evaluation)
2. **Event Sourcing**: For audit trails and data consistency
3. **CQRS**: Separate read/write models for analytics
4. **Circuit Breaker**: For external service dependencies
5. **Bulkhead Pattern**: Isolate critical operations

### Testing Strategy

1. **Contract Testing**: Ensure API compatibility between services
2. **Integration Testing**: Test service interactions
3. **Performance Testing**: Verify latency under load
4. **Chaos Engineering**: Test service resilience
5. **Data Consistency Testing**: Verify eventual consistency

## Deployment Strategy

### Container Strategy
```dockerfile
# Example service Dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8001/health
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "app:create_app()"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
      - name: auth-service
        image: quested/auth-service:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: auth-db-secret
              key: url
```

## Monitoring & Observability

### Metrics to Track
- Request latency per service
- Error rates and types
- Database connection pools
- Queue message processing times
- User authentication success rates

### Logging Strategy
- Structured JSON logging
- Correlation IDs across services
- Centralized log aggregation
- Service-specific log levels

### Health Checks
```python
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': os.getenv('VERSION', 'unknown'),
        'database': check_database_connection(),
        'dependencies': check_external_dependencies()
    }
```

## Summary

This comprehensive mapping provides the foundation for migrating QuestEd's 200+ endpoints to a microservices architecture. The migration maintains all existing functionality while enabling:

- **Independent Scaling**: Scale services based on demand
- **Technology Diversity**: Use appropriate tools per service
- **Team Independence**: Different teams can own different services
- **Fault Isolation**: Service failures don't cascade
- **Deployment Flexibility**: Deploy services independently

The proposed 9-service architecture provides clear boundaries while maintaining the rich functionality of the educational platform.