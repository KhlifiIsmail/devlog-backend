# DevLog Backend

AI-powered development journal API built with Django REST Framework.

## What This Is

Django backend that receives GitHub webhooks, processes commits, groups them into coding sessions, and generates AI narratives using LangChain + GPT-4/Groq.

## Tech Stack

- **Framework**: Django 5.0 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis + Celery
- **AI**: LangChain, OpenAI GPT-4, Groq Llama 3, sentence-transformers
- **Vector DB**: ChromaDB
- **Auth**: JWT (djangorestframework-simplejwt)
- **Deployment**: Docker + Docker Compose

## Quick Start

```bash
# Clone
git clone <repo-url>
cd devlog-backend

# Setup environment
cp .env.example .env
# Edit .env with your keys

# Start with Docker
docker-compose up -d --build

# Run migrations
docker-compose exec django python manage.py migrate
docker-compose exec django python manage.py createsuperuser

# Access
# API: http://localhost:8000
# Admin: http://localhost:8000/admin
# Docs: http://localhost:8000/api/docs/
```

## Environment Variables

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=devlog
DB_USER=devlog
DB_PASSWORD=your-password
DB_HOST=postgres
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# GitHub
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# AI
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk-...  # Optional

# ChromaDB
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
```

## Project Structure

```
devlog-backend/
├── devlog/                 # Project settings
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── core/
│   ├── accounts/          # User & auth
│   │   ├── models.py      # Custom User model
│   │   ├── views.py       # GitHub OAuth
│   │   ├── serializers.py
│   │   └── services.py    # GitHub API calls
│   ├── models/            # Core models
│   │   ├── session.py     # CodingSession
│   │   ├── commit.py      # Commit
│   │   ├── repository.py  # GitHubRepository
│   │   └── insight.py     # AIInsight, Pattern
│   ├── services/          # Business logic
│   │   ├── ai/
│   │   │   ├── narrative.py    # AI narratives
│   │   │   ├── insights.py     # AI insights
│   │   │   └── embeddings.py   # Vector embeddings
│   │   ├── session_grouper.py  # Session logic
│   │   └── vector_store.py     # ChromaDB
│   ├── tasks/             # Celery tasks
│   │   ├── webhook.py     # Process webhooks
│   │   ├── ai.py          # AI generation
│   │   └── analytics.py   # Pattern detection
│   └── views/             # API endpoints
├── docker/
│   ├── Dockerfile.django
│   └── nginx.conf
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Key Models

### User

```python
class User(AbstractUser):
    github_id = BigIntegerField(unique=True)
    github_username = CharField(max_length=100)
    github_access_token = CharField(max_length=255)
    # ... other fields
```

### CodingSession

```python
class CodingSession(models.Model):
    user = ForeignKey(User)
    repository = ForeignKey(GitHubRepository)
    started_at = DateTimeField()
    ended_at = DateTimeField()
    duration_minutes = IntegerField()
    total_commits = IntegerField()
    ai_summary = TextField(null=True)  # AI-generated
    # ... other fields
```

### Commit

```python
class Commit(models.Model):
    repository = ForeignKey(GitHubRepository)
    session = ForeignKey(CodingSession, null=True)
    sha = CharField(max_length=40, unique=True)
    message = TextField()
    additions = IntegerField()
    deletions = IntegerField()
    files_data = JSONField()  # Changed files
    # ... other fields
```

## API Endpoints

### Auth

```
POST   /api/v1/auth/github/callback/  # OAuth callback
POST   /api/v1/auth/refresh/           # Refresh JWT
GET    /api/v1/auth/user/              # Current user
```

### Sessions

```
GET    /api/v1/sessions/               # List sessions
GET    /api/v1/sessions/{id}/          # Session detail
```

### Commits

```
GET    /api/v1/commits/                # List commits
```

### Repositories

```
GET    /api/v1/repositories/                        # List repos
POST   /api/v1/repositories/{id}/toggle-tracking/   # Enable/disable
```

### Insights

```
GET    /api/v1/insights/                  # List insights
POST   /api/v1/insights/generate-weekly/  # Generate weekly
```

### Webhooks (No Auth)

```
POST   /api/v1/webhooks/github/          # Receive GitHub events
```

**API Docs**: http://localhost:8000/api/docs/

## How It Works

### 1. GitHub Webhook Flow

```
GitHub Push → Webhook → Django View → Celery Task → Process Commits
```

**Webhook signature verification**:

```python
# core/utils/github_webhook.py
def verify_webhook_signature(payload_body, signature_header):
    hash_object = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)
```

### 2. Session Grouping

```python
# core/services/session_grouper.py
SESSION_TIMEOUT_MINUTES = 30

# Algorithm:
# - Commits within 30 min → same session
# - Gap > 30 min → new session
```

### 3. AI Processing Pipeline

```
Commit Data → Prepare Context → Generate Embedding → LLM Call → Cache → Save
```

**Narrative generation**:

```python
# core/services/ai/narrative.py
class NarrativeService:
    def generate_session_narrative(self, session):
        # 1. Extract commit messages, files, stats
        context = self._prepare_session_context(session)

        # 2. Check cache
        cache_key = f"narrative_{session.id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # 3. Call LLM
        prompt = ChatPromptTemplate.from_template("...")
        result = (prompt | self.llm).invoke(context)

        # 4. Cache for 30 days
        cache.set(cache_key, result.content, 3600 * 24 * 30)

        return result.content
```

### 4. Celery Tasks

**Webhook processing** (high priority):

```python
@shared_task
def process_push_event(payload):
    # Create commits
    # Group into sessions
    # Trigger AI generation
```

**AI generation** (low priority):

```python
@shared_task(bind=True, max_retries=3)
def generate_session_summary(self, session_id):
    # Generate narrative
    # Generate embedding
    # Store in ChromaDB
    # Save to database
```

**Pattern detection** (scheduled daily at 2 AM):

```python
@shared_task
def detect_user_patterns():
    # Analyze last 30 days
    # Detect productivity peaks, language trends, burnout
    # Generate insights
```

## Celery Configuration

```python
# devlog/celery.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Scheduled tasks (Celery Beat)
CELERY_BEAT_SCHEDULE = {
    'generate-weekly-summaries': {
        'task': 'core.tasks.analytics.generate_weekly_summaries',
        'schedule': crontab(hour=0, minute=0, day_of_week='monday'),
    },
    'detect-patterns': {
        'task': 'core.tasks.analytics.detect_user_patterns',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

## AI/ML Details

### LLM Strategy

- **Session narratives**: Groq Llama 3 (free, fast)
- **Weekly summaries**: GPT-3.5-turbo (cheap)
- **Complex insights**: GPT-4 (expensive but best quality)

### Caching Strategy

```python
# Session narratives: 30 days (rarely change)
cache.set(f'narrative_{session_id}', narrative, 3600 * 24 * 30)

# Weekly summaries: 7 days (fixed time window)
cache.set(f'weekly_{user_id}_{week}', summary, 3600 * 24 * 7)

# Embeddings: Indefinite (immutable)
cache.set(f'embed_{session_id}', embedding, None)
```

### Vector Storage (ChromaDB)

```python
# Store session embedding
vector_store.store_session_embedding(
    session_id=session.id,
    embedding=embedding,
    metadata={
        'user_id': session.user_id,
        'primary_language': session.primary_language,
    }
)

# Search similar sessions
results = vector_store.search_similar_sessions(
    query_embedding=embedding,
    user_id=user_id,
    top_k=5
)
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov-report=html

# Run specific test
pytest core/tests/test_services.py::TestSessionGrouper

# Run integration tests
pytest core/tests/test_integration.py -v
```

## Deployment

### Development

```bash
python manage.py runserver
celery -A devlog worker -l info
celery -A devlog beat -l info
```

### Production (Docker)

```bash
docker-compose up -d --build
docker-compose exec django python manage.py migrate
docker-compose exec django python manage.py collectstatic --noinput
```

### Services in Docker Compose

- `postgres` - PostgreSQL database
- `redis` - Cache + Celery broker
- `django` - Django API (Gunicorn)
- `celery_worker` - Background tasks
- `celery_beat` - Scheduled tasks
- `chromadb` - Vector storage
- `nginx` - Reverse proxy

## Common Tasks

### Setup GitHub Webhooks

```bash
python manage.py setup_webhooks
```

### Generate Test Data

```bash
python manage.py generate_test_data
```

### Manually Trigger AI Generation

```bash
python manage.py shell
>>> from core.tasks.ai import generate_session_summary
>>> generate_session_summary.delay(session_id=1)
```

### Check Celery Queue

```bash
docker-compose exec redis redis-cli
> LLEN celery
```

## Troubleshooting

### Webhook not working

```bash
# Check logs
docker-compose logs django | grep webhook

# Verify signature
echo $GITHUB_WEBHOOK_SECRET

# Test manually
curl -X POST http://localhost:8000/api/v1/webhooks/github/ \
  -H "X-GitHub-Event: push" \
  -d @test_payload.json
```

### AI not generating

```bash
# Check Celery worker
docker-compose logs celery_worker

# Verify API key
python manage.py shell
>>> from django.conf import settings
>>> settings.OPENAI_API_KEY
```

### ChromaDB connection failed

```bash
docker-compose ps chromadb
docker-compose restart chromadb
```

## Performance Tips

1. **Database indexing** (already configured):

```python
class CodingSession(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['user', '-started_at']),
        ]
```

2. **Query optimization**:

```python
# Use select_related for FKs
sessions = CodingSession.objects.select_related('repository').all()

# Use prefetch_related for reverse FKs
sessions = CodingSession.objects.prefetch_related('commits').all()
```

3. **Celery priorities**:

```python
@shared_task(priority=9)  # High priority
def process_push_event(payload):
    pass

@shared_task(priority=1)  # Low priority
def generate_session_summary(session_id):
    pass
```

## Security Notes

- GitHub webhook signature verification (HMAC SHA-256)
- JWT authentication for API
- CORS configured for frontend domain
- All secrets in environment variables
- HTTPS-only in production (Nginx + Let's Encrypt)
- No raw SQL queries (Django ORM only)

## Cost Optimization

- Use Groq (free) for simple tasks
- Aggressive caching (30 day TTL for narratives)
- Batch processing when possible
- Token count optimization in prompts

## License

MIT

## Author

Ismail Khlifi
