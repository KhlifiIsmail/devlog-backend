# DevLog Backend API Documentation

## 🔐 Authentication

All API endpoints (except webhooks) require JWT authentication.

### Headers Required for All Requests:
```http
Authorization: Bearer <your_jwt_access_token>
Content-Type: application/json
Accept: application/json
```

### JWT Token Refresh:
```http
POST /api/v1/auth/refresh/
Content-Type: application/json

{
    "refresh": "your_refresh_token_here"
}
```

---

## 🔧 Authentication Endpoints

### 1. GitHub OAuth Callback
```http
POST /api/v1/auth/github/callback/
Content-Type: application/json

{
    "code": "github_oauth_code_from_frontend"
}
```

**Response (200):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
        "id": 1,
        "username": "john_doe",
        "github_username": "john_doe",
        "github_id": 12345678,
        "email": "john@example.com",
        "github_avatar_url": "https://avatars.githubusercontent.com/u/12345678?v=4"
    }
}
```

**Errors:**
- `400`: Invalid code, failed token exchange, or user fetch failure

### 2. Get Current User
```http
GET /api/v1/auth/user/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
    "id": 1,
    "username": "john_doe",
    "github_username": "john_doe",
    "github_id": 12345678,
    "email": "john@example.com",
    "github_avatar_url": "https://avatars.githubusercontent.com/u/12345678?v=4"
}
```

---

## 📁 Repository Endpoints

### 1. List Repositories
```http
GET /api/v1/repositories/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
[
    {
        "id": 1,
        "name": "my-awesome-project",
        "full_name": "john_doe/my-awesome-project",
        "description": "An awesome project description",
        "url": "https://github.com/john_doe/my-awesome-project",
        "language": "Python",
        "is_private": false,
        "is_fork": false,
        "stars_count": 42,
        "forks_count": 5,
        "is_tracking_enabled": true,
        "last_synced_at": "2024-12-03T10:30:00Z",
        "created_at": "2024-11-01T15:20:00Z"
    }
]
```

### 2. Get Repository Detail
```http
GET /api/v1/repositories/{id}/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
    "id": 1,
    "name": "my-awesome-project",
    "full_name": "john_doe/my-awesome-project",
    "description": "An awesome project description",
    "url": "https://github.com/john_doe/my-awesome-project",
    "default_branch": "main",
    "language": "Python",
    "is_private": false,
    "is_fork": false,
    "stars_count": 42,
    "forks_count": 5,
    "is_tracking_enabled": true,
    "webhook_id": 123456789,
    "last_synced_at": "2024-12-03T10:30:00Z",
    "created_at": "2024-11-01T15:20:00Z",
    "updated_at": "2024-12-03T10:30:00Z"
}
```

**Errors:**
- `404`: Repository not found or access denied

### 3. Sync Repositories from GitHub
```http
POST /api/v1/repositories/sync/
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Response (200):**
```json
{
    "message": "Successfully synced 15 repositories",
    "count": 15
}
```

**Errors:**
- `400`: GitHub API error or sync failure

### 4. Toggle Repository Tracking
```http
POST /api/v1/repositories/{id}/toggle-tracking/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "is_tracking_enabled": true
}
```

**Response (200):**
```json
{
    "id": 1,
    "name": "my-awesome-project",
    "full_name": "john_doe/my-awesome-project",
    "is_tracking_enabled": true,
    ...
}
```

**Errors:**
- `400`: Invalid data format
- `404`: Repository not found

---

## 💾 Commit Endpoints

### 1. List Commits
```http
GET /api/v1/commits/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
[
    {
        "id": 1,
        "sha": "abc123def456789",
        "message": "Add new feature for user authentication",
        "author_name": "John Doe",
        "author_email": "john@example.com",
        "committed_at": "2024-12-03T14:30:00Z",
        "additions": 120,
        "deletions": 45,
        "changed_files": 8,
        "branch": "main",
        "repository": {
            "id": 1,
            "name": "my-awesome-project",
            "full_name": "john_doe/my-awesome-project"
        },
        "session": {
            "id": 5,
            "started_at": "2024-12-03T14:00:00Z"
        },
        "files_data": [
            {
                "filename": "auth/models.py",
                "additions": 25,
                "deletions": 5,
                "status": "modified"
            }
        ]
    }
]
```

### 2. Get Commit Detail
```http
GET /api/v1/commits/{id}/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
    "id": 1,
    "sha": "abc123def456789",
    "message": "Add new feature for user authentication",
    "author_name": "John Doe",
    "author_email": "john@example.com",
    "committed_at": "2024-12-03T14:30:00Z",
    "additions": 120,
    "deletions": 45,
    "changed_files": 8,
    "branch": "main",
    "repository": {
        "id": 1,
        "name": "my-awesome-project",
        "full_name": "john_doe/my-awesome-project",
        "url": "https://github.com/john_doe/my-awesome-project"
    },
    "session": {
        "id": 5,
        "started_at": "2024-12-03T14:00:00Z",
        "duration_minutes": 120
    },
    "files_data": [
        {
            "filename": "auth/models.py",
            "additions": 25,
            "deletions": 5,
            "status": "modified",
            "language": "Python"
        }
    ],
    "created_at": "2024-12-03T14:35:00Z"
}
```

**Errors:**
- `404`: Commit not found or access denied

---

## 🎯 Session Endpoints

### 1. List Coding Sessions
```http
GET /api/v1/sessions/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
[
    {
        "id": 5,
        "started_at": "2024-12-03T14:00:00Z",
        "ended_at": "2024-12-03T16:00:00Z",
        "duration_minutes": 120,
        "total_commits": 8,
        "total_additions": 245,
        "total_deletions": 89,
        "files_changed": 15,
        "primary_language": "Python",
        "languages_used": ["Python", "JavaScript", "CSS"],
        "repository": {
            "id": 1,
            "name": "my-awesome-project",
            "full_name": "john_doe/my-awesome-project"
        },
        "ai_summary": "This session focused on backend API development...",
        "ai_generated_at": "2024-12-03T16:30:00Z",
        "created_at": "2024-12-03T16:05:00Z"
    }
]
```

### 2. Get Session Detail
```http
GET /api/v1/sessions/{id}/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
    "id": 5,
    "started_at": "2024-12-03T14:00:00Z",
    "ended_at": "2024-12-03T16:00:00Z",
    "duration_minutes": 120,
    "total_commits": 8,
    "total_additions": 245,
    "total_deletions": 89,
    "files_changed": 15,
    "primary_language": "Python",
    "languages_used": ["Python", "JavaScript", "CSS"],
    "repository": {
        "id": 1,
        "name": "my-awesome-project",
        "full_name": "john_doe/my-awesome-project",
        "url": "https://github.com/john_doe/my-awesome-project"
    },
    "commits": [
        {
            "id": 1,
            "sha": "abc123def",
            "message": "Add authentication",
            "committed_at": "2024-12-03T14:30:00Z",
            "additions": 50,
            "deletions": 10
        }
    ],
    "ai_summary": "This session focused on backend API development...",
    "ai_generated_at": "2024-12-03T16:30:00Z",
    "created_at": "2024-12-03T16:05:00Z",
    "updated_at": "2024-12-03T16:30:00Z"
}
```

**Errors:**
- `404`: Session not found or access denied

### 3. Group Ungrouped Commits
```http
POST /api/v1/sessions/group/
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Response (200):**
```json
{
    "message": "Successfully created 3 sessions",
    "count": 3
}
```

**Errors:**
- `400`: Failed to group commits

---

## 🤖 AI Features

### 1. Generate Session Narrative
```http
POST /api/v1/sessions/{session_id}/generate-narrative/
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Response (200):**
```json
{
    "narrative": "This session focused on backend API development, implementing authentication middleware and database optimization. The work involved 5 commits across authentication and database modules, with significant changes to user authentication logic (+245 lines) and query optimization (-89 lines). The development pattern suggests systematic refactoring of existing authentication flows while maintaining backward compatibility.",
    "generated_at": "2024-12-03T22:30:15.123456Z",
    "model_used": "provider-5/gpt-4o-mini",
    "session_id": 123,
    "cached": false,
    "commit_count": 5,
    "session_duration": 45
}
```

**Errors:**
- `404`: Session not found or access denied
- `400`: Invalid session data (no commits found)
- `503`: AI service temporarily unavailable

### 2. Find Similar Sessions
```http
GET /api/v1/sessions/{session_id}/similar/?limit=5&user_only=true
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `limit` (optional, default=5, max=20): Number of similar sessions to return
- `user_only` (optional, default=true): Limit results to same user's sessions

**Response (200):**
```json
{
    "similar_sessions": [
        {
            "session_id": 156,
            "similarity_score": 0.87,
            "repository": "username/my-project",
            "duration_minutes": 38,
            "total_commits": 4,
            "primary_language": "Python",
            "started_at": "2024-11-28T14:20:00Z",
            "files_changed": 12
        },
        {
            "session_id": 143,
            "similarity_score": 0.73,
            "repository": "username/my-project",
            "duration_minutes": 52,
            "total_commits": 7,
            "primary_language": "Python",
            "started_at": "2024-11-25T09:15:00Z",
            "files_changed": 8
        }
    ],
    "session_id": 123,
    "count": 2,
    "user_only": true
}
```

**Errors:**
- `404`: Session not found or access denied
- `400`: Failed to find similar sessions

---

## 🔥 Activity Feed Endpoints

### 1. Get Activity Feed
```http
GET /api/v1/activity/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
    "recent_commits": [
        {
            "id": 15,
            "sha": "def456abc789",
            "message": "Fix bug in authentication flow",
            "author_name": "John Doe",
            "committed_at": "2024-12-03T15:45:00Z",
            "additions": 8,
            "deletions": 3,
            "repository": {
                "name": "my-project",
                "full_name": "john_doe/my-project"
            }
        }
    ],
    "recent_sessions": [
        {
            "id": 8,
            "started_at": "2024-12-03T14:00:00Z",
            "duration_minutes": 90,
            "total_commits": 4,
            "primary_language": "Python",
            "repository": {
                "name": "my-project",
                "full_name": "john_doe/my-project"
            }
        }
    ],
    "activity_summary": {
        "total_commits_today": 12,
        "total_time_today": 180,
        "active_repositories": 3,
        "current_streak": 7
    }
}
```

### 2. Real-time Activity Stream (SSE)
```http
GET /api/v1/realtime/activity/
Authorization: Bearer <jwt_token>
Accept: text/event-stream
Cache-Control: no-cache
```

**Response Headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**Event Stream Format:**
```
data: {"type": "connected", "message": "Activity stream connected"}

data: {"type": "new_commit", "data": {...commit_object...}}

data: {"type": "new_session", "data": {...session_object...}}

data: {"type": "heartbeat", "timestamp": "2024-12-03T15:30:00Z"}

data: {"type": "error", "message": "Error description"}
```

**Client Implementation Example (JavaScript):**
```javascript
const eventSource = new EventSource('/api/v1/realtime/activity/', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);

    switch(data.type) {
        case 'connected':
            console.log('Connected to activity stream');
            break;
        case 'new_commit':
            handleNewCommit(data.data);
            break;
        case 'new_session':
            handleNewSession(data.data);
            break;
        case 'heartbeat':
            console.log('Heartbeat received');
            break;
        case 'error':
            console.error('Stream error:', data.message);
            break;
    }
};
```

---

## 📊 Insights Endpoints

### 1. List Insights
```http
GET /api/v1/insights/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
    "insights": [
        {
            "id": 1,
            "title": "Productivity Overview",
            "description": "You've coded for 1200 minutes across 25 sessions in the last 30 days",
            "type": "productivity",
            "generated_at": "2024-12-03T16:00:00Z",
            "data": {
                "total_time_minutes": 1200,
                "total_sessions": 25,
                "average_session_time": 48.0,
                "total_commits": 156
            }
        },
        {
            "id": 2,
            "title": "Top Programming Language",
            "description": "You spent the most time coding in Python (780 minutes)",
            "type": "language",
            "generated_at": "2024-12-03T16:00:00Z",
            "data": {
                "top_language": "Python",
                "time_spent": 780,
                "all_languages": {
                    "Python": 780,
                    "JavaScript": 320,
                    "CSS": 100
                }
            }
        },
        {
            "id": 3,
            "title": "Most Active Repository",
            "description": "You had the most coding sessions in backend-api (15 sessions)",
            "type": "repository",
            "generated_at": "2024-12-03T16:00:00Z",
            "data": {
                "most_active_repo": "backend-api",
                "session_count": 15,
                "all_repos": {
                    "backend-api": 15,
                    "frontend-app": 8,
                    "mobile-app": 2
                }
            }
        }
    ]
}
```

### 2. Generate Weekly Summary
```http
POST /api/v1/insights/generate-weekly/
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Response (200):**
```json
{
    "summary": "This week you completed 12 coding sessions across 3 repositories, making 45 commits in 480 minutes of coding time.",
    "week_start": "2024-12-02T00:00:00Z",
    "week_end": "2024-12-09T00:00:00Z",
    "stats": {
        "total_sessions": 12,
        "total_commits": 45,
        "total_time": 480,
        "repositories": 3
    },
    "generated_at": "2024-12-03T16:30:00Z"
}
```

### 3. Get Weekly Insights
```http
GET /api/v1/insights/weekly/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
    "current_week": {
        "sessions": 12,
        "commits": 45,
        "time": 480,
        "repositories": 3,
        "week_start": "2024-12-02T00:00:00Z",
        "week_end": "2024-12-09T00:00:00Z"
    },
    "previous_week": {
        "sessions": 8,
        "commits": 32,
        "time": 320,
        "repositories": 2,
        "week_start": "2024-11-25T00:00:00Z",
        "week_end": "2024-12-02T00:00:00Z"
    },
    "trends": {
        "sessions_change_percent": 50.0,
        "commits_change_percent": 40.6,
        "time_change_percent": 50.0
    }
}
```

---

## 🔍 Patterns Endpoints

### 1. Get Coding Patterns
```http
GET /api/v1/patterns/
Authorization: Bearer <jwt_token>
```

**Response (200):**
```json
{
    "patterns": [
        {
            "type": "time_preference",
            "title": "Peak Coding Time: Evening",
            "description": "You code most frequently at 19:00, with 15 sessions started during this hour",
            "data": {
                "peak_hour": 19,
                "peak_count": 15,
                "time_period": "evening",
                "hour_distribution": {
                    "9": 3,
                    "14": 8,
                    "19": 15,
                    "22": 5
                }
            }
        },
        {
            "type": "language_preference",
            "title": "Favorite Language: Python",
            "description": "You spend 65.0% of your coding time using Python (780 minutes total)",
            "data": {
                "favorite_language": "Python",
                "time_spent": 780,
                "percentage": 65.0,
                "language_distribution": {
                    "Python": 780,
                    "JavaScript": 320,
                    "CSS": 100
                }
            }
        },
        {
            "type": "session_length",
            "title": "Session Style: Balanced",
            "description": "You tend to have balanced coding sessions, typically lasting 30-120 minutes",
            "data": {
                "pattern": "balanced",
                "average_duration": 48.0,
                "short_sessions": 8,
                "medium_sessions": 15,
                "long_sessions": 2,
                "total_sessions": 25
            }
        },
        {
            "type": "commit_frequency",
            "title": "Average Commits: 6.2 per day",
            "description": "Your most productive day was 2024-12-01 with 18 commits",
            "data": {
                "average_commits_per_day": 6.2,
                "max_commits_in_day": 18,
                "most_productive_day": "2024-12-01",
                "total_commit_days": 25,
                "total_commits": 156
            }
        }
    ]
}
```

---

## 🔗 Webhook Endpoint (No Authentication)

### GitHub Webhook
```http
POST /api/v1/webhooks/github/
Content-Type: application/json
X-GitHub-Event: push
X-Hub-Signature-256: sha256=<hmac_signature>

{
    "ref": "refs/heads/main",
    "repository": {
        "id": 123456789,
        "name": "my-repo",
        "full_name": "user/my-repo"
    },
    "commits": [
        {
            "id": "abc123def456",
            "message": "Add new feature",
            "author": {
                "name": "John Doe",
                "email": "john@example.com"
            },
            "timestamp": "2024-12-03T15:30:00Z",
            "added": ["file1.py"],
            "removed": [],
            "modified": ["file2.py"]
        }
    ]
}
```

**Response (200):**
```json
{
    "message": "Webhook processed successfully",
    "commits_processed": 1,
    "sessions_created": 0
}
```

**Errors:**
- `400`: Invalid signature, unsupported event, or processing error
- `401`: Invalid webhook signature

---

## 🚨 Common Error Responses

### Authentication Errors
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### Permission Errors
```json
{
    "detail": "You do not have permission to perform this action."
}
```

### Validation Errors
```json
{
    "field_name": ["This field is required."],
    "another_field": ["Ensure this field has no more than 100 characters."]
}
```

### Not Found Errors
```json
{
    "error": "Session not found or access denied"
}
```

### Server Errors
```json
{
    "error": "AI service temporarily unavailable"
}
```

---

## 📝 Request/Response Best Practices

### 1. Always Include Required Headers
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
Accept: application/json
```

### 2. Handle Token Expiration
```javascript
// Check for 401 responses and refresh token
if (response.status === 401) {
    await refreshAuthToken();
    // Retry original request
}
```

### 3. Proper Error Handling
```javascript
try {
    const response = await fetch('/api/v1/sessions/', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });

    if (!response.ok) {
        if (response.status === 404) {
            throw new Error('Resource not found');
        } else if (response.status === 403) {
            throw new Error('Access denied');
        } else if (response.status >= 500) {
            throw new Error('Server error - please try again later');
        }

        const errorData = await response.json();
        throw new Error(errorData.error || 'Request failed');
    }

    const data = await response.json();
    return data;
} catch (error) {
    console.error('API Error:', error);
    // Handle error appropriately
}
```

### 4. Rate Limiting Considerations
- AI endpoints may have longer response times (5-30 seconds)
- SSE connections should implement reconnection logic
- Implement client-side debouncing for frequent requests

### 5. Pagination (Future Enhancement)
Most list endpoints will support pagination:
```http
GET /api/v1/sessions/?page=2&page_size=20
```

Response format:
```json
{
    "count": 100,
    "next": "http://api/v1/sessions/?page=3",
    "previous": "http://api/v1/sessions/?page=1",
    "results": [...]
}
```

---

## 🔧 Environment Variables Required

Ensure these are set in your `.env` file:
```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/devlog

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# AI (A4F)
A4F_API_KEY=ddc-a4f-6ed650b20cb04ccbbfb204a51c343e88
A4F_BASE_URL=https://api.a4f.co/v1
A4F_MODEL=provider-5/gpt-4o-mini

# ChromaDB
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
```

This documentation covers **ALL** endpoints with exact request/response formats to ensure zero 400/406 errors! 🎯