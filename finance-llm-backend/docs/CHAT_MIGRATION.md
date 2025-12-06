# Chat System Migration: Redis to PostgreSQL

## Overview

This document describes the migration from Redis-based chat sessions to PostgreSQL-based persistent chat storage with full CRUD operations.

## Changes Made

### Backend Changes

#### 1. Database Schema (`core/database/schema.py`)

Added two new tables to store chat data:

**chat_sessions**

- `chat_id` (UUID, Primary Key): Unique identifier for each chat session
- `title` (TEXT): Chat title (derived from first message)
- `created_at` (TIMESTAMP): When the chat was created
- `updated_at` (TIMESTAMP): Last update time (auto-updated on new messages)

**chat_messages**

- `id` (BIGSERIAL, Primary Key): Message ID
- `chat_id` (UUID, Foreign Key): References chat_sessions
- `role` (TEXT): Either 'user' or 'assistant'
- `content` (TEXT): Message content
- `sources` (JSONB): Source documents used for assistant responses
- `created_at` (TIMESTAMP): Message timestamp

**Indexes:**

- Created indexes on `created_at`, `updated_at`, and `chat_id` for fast queries
- Automatic cascade delete: deleting a chat session removes all its messages

**Triggers:**

- Auto-update `chat_sessions.updated_at` when new messages are added

#### 2. PostgreSQL Memory Module (`core/memory/postgres_memory.py`)

Created new `PostgresChatMemory` class to replace Redis functionality:

**Methods:**

- `create_chat_session(title)`: Create new chat session
- `get_all_chat_sessions()`: Get all chats ordered by most recent
- `get_chat_session(chat_id)`: Get specific chat with all messages
- `add_message(chat_id, role, content, sources)`: Add message to chat
- `update_chat_title(chat_id, title)`: Update chat title
- `delete_chat_session(chat_id)`: Delete specific chat
- `delete_all_chat_sessions()`: Delete all chats
- `get_chat_history(chat_id, limit)`: Get messages in LLM format

#### 3. Chat Routes (`routes/chat_routes.py`)

Completely refactored to use PostgreSQL:

**New/Updated Endpoints:**

`POST /chat`

- Creates new chat if no `chat_id` provided
- Adds user message and assistant response to database
- Returns `chat_id` in response
- Request body: `{ "query": "...", "chat_id": "..." (optional) }`

`GET /chats`

- Get all chat sessions with metadata
- Returns: `{ "chats": [...], "count": N }`

`GET /chats/<chat_id>`

- Get specific chat with all messages
- Returns full chat session with message history

`DELETE /chats/<chat_id>`

- Delete single chat session
- Cascades to delete all messages

`DELETE /chats`

- Delete all chat sessions
- Returns count of deleted sessions

`PUT /chats/<chat_id>/title`

- Update chat title
- Request body: `{ "title": "..." }`

#### 4. Configuration (`config.py`)

- Removed all Redis-related configuration variables:
  - `REDIS_HOST`
  - `REDIS_PORT`
  - `REDIS_DB`
  - `REDIS_PASSWORD`
  - `REDIS_SESSION_TTL`
  - `REDIS_MAX_HISTORY`

#### 5. Requirements (`requirements.txt`)

- Removed `redis==5.0.1`
- Removed `types-redis==4.6.0.20240106`

### Frontend Changes

#### 1. AIAssistantUI Component (`components/AIAssistantUI.jsx`)

**Added State:**

- `loading`: Track loading state
- Removed mock data initialization

**New Functions:**

- `fetchAllChats()`: Load all chats from backend on mount
- `fetchChatMessages(chatId)`: Load messages for specific chat
- `deleteChat(chatId)`: Delete single chat via API

**Updated Functions:**

- `createNewChat()`: Creates temporary chat locally, backend chat created on first message
- `clearAllData()`: Calls backend API to delete all chats
- `sendMessage()`: Integrated with backend `/chat` endpoint
  - Handles temporary chat ID replacement with real UUID
  - Saves messages to PostgreSQL
  - Includes error handling and optimistic updates

**API Integration:**

- Uses `NEXT_PUBLIC_API_URL` environment variable
- Default: `http://localhost:5000`

#### 2. Sidebar Component (`components/Sidebar.jsx`)

- Added `onDeleteChat` prop
- Passes delete function to `ConversationRow` components

#### 3. Environment Configuration

Created `.env.example`:

```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## Migration Steps

### 1. Backend Setup

```bash
cd finance-llm-backend

# Install dependencies (Redis no longer needed)
pip install -r requirements.txt

# Initialize database with new chat tables
python init_database.py

# Or recreate schema from scratch
python init_database.py --recreate
```

### 2. Frontend Setup

```bash
cd finance-llm-frontend

# Create .env file
cp .env.example .env

# Edit .env and set API URL if different from default
# NEXT_PUBLIC_API_URL=http://your-backend-url:5000

# Install dependencies
pnpm install

# Run development server
pnpm dev
```

### 3. Start Backend

```bash
cd finance-llm-backend
python app.py
```

## API Examples

### Create New Chat (Implicit)

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key financial metrics?"
  }'
```

Response:

```json
{
  "chat_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "Based on the documents...",
  "sources": [...],
  "metadata": {...}
}
```

### Get All Chats

```bash
curl http://localhost:5000/chats
```

Response:

```json
{
  "chats": [
    {
      "chat_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "What are the key financial metrics?",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z",
      "message_count": 4,
      "last_message_at": "2024-01-15T10:35:00Z"
    }
  ],
  "count": 1
}
```

### Get Single Chat

```bash
curl http://localhost:5000/chats/550e8400-e29b-41d4-a716-446655440000
```

Response:

```json
{
  "chat_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "What are the key financial metrics?",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "What are the key financial metrics?",
      "sources": null,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "Based on the documents...",
      "sources": [...],
      "created_at": "2024-01-15T10:30:05Z"
    }
  ]
}
```

### Delete Single Chat

```bash
curl -X DELETE http://localhost:5000/chats/550e8400-e29b-41d4-a716-446655440000
```

### Delete All Chats

```bash
curl -X DELETE http://localhost:5000/chats
```

### Continue Existing Chat

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me more about revenue",
    "chat_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

## Benefits of PostgreSQL Migration

1. **Persistence**: Chats survive server restarts
2. **Scalability**: No memory limitations like Redis
3. **Query Power**: Can filter, search, and analyze chat history
4. **Data Integrity**: ACID compliance, foreign keys, cascading deletes
5. **Integration**: Chat data in same database as document embeddings
6. **Simplicity**: One less service to manage (no Redis)
7. **History**: Full conversation context preserved indefinitely

## Database Queries

### Get Recent Chats

```sql
SELECT * FROM chat_sessions
ORDER BY updated_at DESC
LIMIT 10;
```

### Count Messages per Chat

```sql
SELECT cs.chat_id, cs.title, COUNT(cm.id) as message_count
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.chat_id = cm.chat_id
GROUP BY cs.chat_id, cs.title
ORDER BY cs.updated_at DESC;
```

### Search Chat Content

```sql
SELECT DISTINCT cs.chat_id, cs.title
FROM chat_sessions cs
JOIN chat_messages cm ON cs.chat_id = cm.chat_id
WHERE cm.content ILIKE '%revenue%'
ORDER BY cs.updated_at DESC;
```

### Get User Questions

```sql
SELECT content, created_at
FROM chat_messages
WHERE role = 'user'
ORDER BY created_at DESC
LIMIT 20;
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL connection
psql -h <host> -U <user> -d <database>

# Verify tables exist
\dt
```

### Missing Tables

```bash
# Recreate schema
cd finance-llm-backend
python init_database.py --recreate
```

### Frontend API Connection

- Check `NEXT_PUBLIC_API_URL` in `.env`
- Ensure backend is running on correct port
- Check CORS settings in `app.py`
- Open browser console for error messages

## Future Enhancements

1. **Search**: Full-text search across chat history
2. **Tags**: Categorize chats by topic
3. **Sharing**: Share chat sessions via URL
4. **Export**: Download chat history as PDF/text
5. **Analytics**: Usage statistics and insights
6. **Folders**: Organize chats into folders
7. **Pinning**: Pin important chats to top

## Rollback (If Needed)

If you need to rollback to Redis:

1. Restore `redis` in `requirements.txt`
2. Restore Redis configuration in `config.py`
3. Restore old `routes/chat_routes.py` from git history
4. Restore old `components/AIAssistantUI.jsx`

```bash
git diff HEAD~1 finance-llm-backend/routes/chat_routes.py > rollback.patch
git apply --reverse rollback.patch
```
