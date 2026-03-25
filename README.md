# VibeFinder

AI-powered music discovery application that uses Ollama (llama3.1) to recommend songs based on audio identification or mood descriptions.

## Tech Stack

### Frontend
- React with Vite
- Tailwind CSS
- React Query for state management

### Backend
- Python with FastAPI
- PostgreSQL for user data and OAuth tokens
- ChromaDB for vector storage of music preferences
- Ollama (llama3.1) for AI recommendations
- MCP (Model Context Protocol) for YouTube Music integration

## Features

- **Audio Identification**: Record a song snippet and identify it using shazamio
- **AI Recommendations**: Get 10 personalized song recommendations based on identified audio or mood description
- **User Preferences**: Registered users' preferences are stored and learned over time
- **Guest Mode**: Non-registered users can use the app with session-based preferences
- **YouTube Music Integration**: Search songs and play them via MCP

## Use Cases

VibeFinder supports multiple ways to discover music. Here are the main use cases with step-by-step instructions:

### Case 1: Mood-Based Recommendations (Text Input)

**Scenario:** You want music that matches your current mood or activity.

**How it works:**
```
User types "relaxing music for studying" 
    → LLM analyzes the mood/intent
    → Generates search queries: ["lo-fi study beats", "ambient focus music", ...]
    → MCP searches YouTube Music for each query
    → Returns 12 personalized recommendations
```

**Steps:**
1. Go to the home page
2. Either:
   - Click a **Quick Mood** button (Energetic, Relaxed, Melancholic, etc.)
   - Or type a custom description in the text field (e.g., "upbeat music for a road trip")
3. Press Enter or click the send button
4. Wait for AI to process and display recommendations
5. Click any song to play it

**Tips:**
- Be descriptive: "happy indie pop for a summer afternoon" works better than "happy music"
- You can combine moods: "nostalgic but uplifting 80s vibes"
- The AI considers your preferences (likes/dislikes) if you're logged in

---

### Case 2: Audio Identification + Recommendations

**Scenario:** You hear a song and want to find similar music.

**How it works:**
```
User records audio snippet (5-15 seconds)
    → Shazamio identifies the song
    → Song info displayed: "Shape of You - Ed Sheeran"
    → User clicks "Find Similar" or adds mood description
    → LLM generates recommendations based on the identified song
```

**Steps:**
1. Click the **microphone button** 🎤
2. Select **"Identify a Song"** from the menu
3. Play the song near your microphone (5-15 seconds is enough)
4. Click stop when done
5. If identified:
   - Click **"Find Similar Songs"** for direct recommendations
   - Or add a description like "more upbeat versions" and submit
6. Browse and play the recommendations

**Tips:**
- Record the chorus or a distinctive part of the song
- Minimize background noise for better identification
- Works with music from speakers, headphones, or live

---

### Case 3: Unidentified Audio (CLAP Analysis)

**Scenario:** The song wasn't identified, but you still want similar music.

**How it works:**
```
User records audio → Shazamio fails to identify
    → CLAP model analyzes the audio characteristics
    → Extracts: mood tags, genre tags, tempo, energy level
    → User sees: "Detected: energetic, electronic, fast tempo"
    → LLM uses these characteristics for recommendations
```

**Steps:**
1. Record audio as in Case 2
2. If the song isn't recognized, you'll see:
   - Detected mood tags (e.g., "energetic", "dark")
   - Detected genre tags (e.g., "electronic", "rock")
   - Tempo and energy description
3. Click **"Find Similar by Vibe"** to get recommendations based on audio analysis
4. Alternatively, describe what you're looking for in the text field

**Tips:**
- This works great for obscure or unreleased music
- The AI uses the detected characteristics to find similar vibes
- You can still add text to refine results

---

### Case 4: Combined (Audio + Mood Description)

**Scenario:** You identified a song but want variations with a specific twist.

**How it works:**
```
Identified: "Blinding Lights - The Weeknd"
User adds: "but more acoustic and chill"
    → LLM considers both the song AND the mood modifier
    → Recommendations blend similar artists with the requested vibe
```

**Steps:**
1. Identify a song (Case 2)
2. Instead of clicking "Find Similar", type a description
3. Example: "similar vibe but in Spanish" or "more instrumental"
4. Submit to get customized recommendations

**Tips:**
- Great for exploring variations of songs you love
- Try genre shifts: "this but as jazz" or "electronic remix style"

---

### Case 5: Voice Input for Mood Description

**Scenario:** You prefer speaking over typing.

**How it works:**
```
User speaks: "I want something energetic for my workout"
    → Speech-to-text converts to text
    → Proceeds as Case 1 (mood-based recommendations)
```

**Steps:**
1. Click the **microphone button** 🎤
2. Select **"Voice Input"** from the menu
3. Speak your mood description clearly
4. Click stop when done
5. Review the transcribed text (edit if needed)
6. Submit for recommendations

**Tips:**
- Speak naturally, as if talking to a friend
- The transcription appears in real-time
- Works best in quiet environments

---

### Case 6: Like/Dislike for Personalization

**Scenario:** You want the AI to learn your preferences over time.

**How it works:**
```
User likes a song → Stored in ChromaDB as preference vector
User dislikes a song → Also stored to avoid similar recommendations
    → Future recommendations consider these preferences
    → LLM receives context: "User likes indie pop, dislikes heavy metal"
```

**Steps:**
1. **Register an account** (preferences aren't saved for guests)
2. When you see recommendations:
   - Click **👍 (thumbs up)** on songs you love
   - Click **👎 (thumbs down)** on songs you don't want to see again
3. Your preferences are immediately saved
4. Future recommendations will be personalized

**Where to see your preferences:**
1. Click your profile icon in the header
2. View your **Liked Songs** and **Disliked Songs** lists
3. You can remove any preference by clicking the ❌ button

**Tips:**
- The more you interact, the better recommendations become
- Likes influence what genres/artists are recommended
- Dislikes help filter out unwanted styles

---

### Case 7: Continue Exploring (More Like This)

**Scenario:** You found great recommendations and want more.

**How it works:**
```
Current recommendations displayed (12 songs)
User clicks "Load More"
    → LLM receives the current songs as context
    → Generates new recommendations that continue the vibe
    → Avoids duplicates from previous batch
```

**Steps:**
1. Get initial recommendations (any case above)
2. Scroll to the bottom of the recommendations
3. Click **"Load More"** or **"Continue Exploring"**
4. New songs are added, maintaining the same vibe

---

### Case 8: Replay from History

**Scenario:** You want to revisit a previous search.

**Steps:**
1. Click your **profile icon** → go to Profile
2. Scroll to **Search History**
3. Click any previous search to reload those recommendations
4. You can then "Load More" to continue from there

---

### Summary Table

| Case | Input | Output | Auth Required |
|------|-------|--------|---------------|
| 1. Mood Text | Text description | 12 songs matching mood | No |
| 2. Audio ID | Song recording | Identified song + 12 similar | No |
| 3. CLAP Analysis | Unidentified audio | 12 songs matching vibe | No |
| 4. Combined | Audio + text | 12 customized recommendations | No |
| 5. Voice Input | Speech | Transcribed text → Case 1 | No |
| 6. Like/Dislike | Button clicks | Personalized future results | **Yes** |
| 7. Load More | Button click | 12 more songs (same vibe) | No |
| 8. History Replay | History click | Previous recommendations | **Yes** |

---

## Project Structure

```
youtbmusic/
├── docker-compose.yml    # Full stack Docker Compose
├── .env.docker           # Docker environment template
│
├── frontend/             # React + Vite frontend
│   ├── Dockerfile        # Multi-stage build (dev/prod)
│   ├── docker-compose.yml# Standalone frontend compose
│   ├── nginx.conf        # Production nginx config
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   ├── hooks/        # Custom hooks
│   │   └── context/      # React context providers
│   └── ...
│
├── backend/              # FastAPI backend
│   ├── Dockerfile        # Python backend image
│   ├── docker-compose.yml# Standalone backend compose
│   ├── alembic/          # Database migrations
│   │   ├── env.py        # Migration environment config
│   │   └── versions/     # Migration scripts
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Core configuration
│   │   ├── db/           # Database models and connections
│   │   ├── services/     # Business logic services
│   │   └── mcp/          # MCP client and server
│   └── ...
│
├── postgresdb/           # Standalone PostgreSQL
│   ├── Dockerfile        # PostgreSQL image with init scripts
│   ├── docker-compose.yml# Standalone postgres compose
│   ├── init/             # Database initialization scripts
│   └── backups/          # Backup storage
│
├── ollama/               # Standalone Ollama AI
│   ├── Dockerfile        # Ollama image
│   ├── docker-compose.yml# Standalone ollama compose
│   └── README.md         # Ollama setup guide
│
└── README.md
```

## Getting Started

### Option 1: Docker (Recommended)

The easiest way to run VibeFinder is with Docker Compose.

#### Prerequisites for Docker

- Docker and Docker Compose installed
- Ollama running on host machine with llama3.1 model

#### Quick Start with Docker

1. Copy the environment file:
   ```bash
   cp .env.docker .env
   # Edit .env if needed (optional)
   ```

2. Start all backend services:
   ```bash
   docker compose up -d
   ```

3. (Optional) Start frontend in Docker:
   ```bash
   # Development with hot reload
   docker compose --profile frontend-dev up -d
   
   # Or production with nginx
   docker compose --profile frontend-prod up -d
   ```

4. Access the application:
   - Frontend: http://localhost:5173 (run `npm run dev` locally or use Docker)
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Langfuse: http://localhost:3000

#### Docker Commands

```bash
# Start all backend services (postgres, chromadb, ollama, langfuse, backend)
docker compose up -d

# Start with frontend (development)
docker compose --profile frontend-dev up -d

# Start with frontend (production)
docker compose --profile frontend-prod up -d

# Start specific services only
docker compose up -d postgres chromadb backend

# Stop all services
docker compose down

# View logs
docker compose logs -f
docker compose logs -f backend  # specific service

# Rebuild containers after code changes
docker compose up -d --build

# Recreate containers (picks up new .env values)
docker compose up -d --force-recreate
```

#### Running Services Separately

```bash
# Just databases
docker compose up -d postgres chromadb

# Just Ollama (useful if you want to manage it separately)
docker compose up -d ollama
docker exec vibefinder-ollama ollama pull llama3.1

# Backend without Ollama in Docker (use host Ollama)
# First, set in .env: OLLAMA_BASE_URL=http://host.docker.internal:11434
docker compose up -d postgres chromadb langfuse-db langfuse backend
```

#### Docker Services

| Service | Port | Description |
|---------|------|-------------|
| postgres | 5432 | PostgreSQL database (app data) |
| chromadb | 8001 | ChromaDB vector database (preferences) |
| langfuse-db | - | PostgreSQL for Langfuse (internal) |
| langfuse | 3000 | LLM observability dashboard |
| ollama | 11434 | Ollama AI (LLM) |
| backend | 8000 | FastAPI backend |
| frontend-dev | 5173 | Vite dev server (profile: frontend-dev) |
| frontend-prod | 80 | Nginx production (profile: frontend-prod) |

#### Ollama Configuration

By default, the backend connects to Ollama running in Docker. To use Ollama on your host machine instead:

1. Set in `.env`:
   ```bash
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```

2. Start services without Docker Ollama:
   ```bash
   docker compose up -d postgres chromadb langfuse-db langfuse backend
   ```

3. Make sure Ollama is running on your host:
   ```bash
   ollama serve
   ollama pull llama3.1
   ```

### Option 2: Manual Setup

#### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Ollama with llama3.1 model installed

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment file and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. Generate security keys (see [Security Keys](#security-keys) section below)

6. Run database migrations:
   ```bash
   alembic upgrade head
   ```

7. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

### Ollama Setup

1. Install Ollama: https://ollama.ai/

2. Pull the llama3.1 model:
   ```bash
   ollama pull llama3.1
   ```

3. Ensure Ollama is running:
   ```bash
   ollama serve
   ```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## User Types

### Registered Users
- Full preference tracking via ChromaDB
- Persistent OAuth tokens for YouTube Music
- History of recommendations saved to PostgreSQL
- AI learns from likes/dislikes over time

### Guest Users
- Session-based (24-hour) access
- No persistent storage in ChromaDB
- Temporary YouTube Music authentication
- Recommendations based only on current session input

## MCP (Model Context Protocol) Integration

VibeFinder uses a **custom MCP server** to integrate YouTube Music functionality with the AI recommendation engine. This allows the LLM to search for songs, get details, and manage playlists programmatically.

### What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is an open standard by Anthropic that enables AI models to interact with external tools and data sources. Think of it as a standardized way for LLMs to "use tools".

```
User Input → LLM (Ollama) → MCP Client → MCP Server → YouTube Music API
                                ↓
                         Tool Results → LLM → Recommendations
```

### Our Custom YouTube Music MCP Server

I built a custom MCP server from scratch that wraps the `ytmusicapi` library. It's located at:

```
backend/app/mcp/youtube_music_server.py
```

**Why custom?** There's no official YouTube Music MCP server available. I created one specifically for VibeFinder's needs.

### Available MCP Tools

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `search_songs` | Search for songs on YouTube Music | No |
| `get_song_details` | Get detailed info about a specific song | No |
| `get_song_recommendations` | Get recommendations based on a video ID | No |
| `get_user_playlists` | Get the authenticated user's playlists | Yes |
| `add_to_playlist` | Add a song to a playlist | Yes |
| `create_playlist` | Create a new playlist | Yes |

### Tool Schemas

#### search_songs
```json
{
  "query": "string (required) - Search query",
  "limit": "integer (default: 10) - Max results",
  "auth_headers": "string (optional) - Auth headers JSON"
}
```

#### get_song_details
```json
{
  "video_id": "string (required) - YouTube video ID",
  "auth_headers": "string (optional)"
}
```

#### get_song_recommendations
```json
{
  "video_id": "string (required) - Base video for recommendations",
  "limit": "integer (default: 10)",
  "auth_headers": "string (optional)"
}
```

#### get_user_playlists
```json
{
  "auth_headers": "string (required) - Auth headers JSON or file path"
}
```

#### add_to_playlist
```json
{
  "video_id": "string (required)",
  "playlist_id": "string (required)",
  "auth_headers": "string (required)"
}
```

#### create_playlist
```json
{
  "title": "string (required)",
  "description": "string (default: '')",
  "privacy_status": "string (PUBLIC|PRIVATE|UNLISTED, default: PRIVATE)",
  "auth_headers": "string (required)"
}
```

### How VibeFinder Uses MCP

1. **User requests recommendations** (via mood or audio)
2. **LLM generates search queries** based on user preferences (from ChromaDB)
3. **MCP Client calls `search_songs`** for each query
4. **Results are enriched** with Last.fm metadata
5. **Final recommendations** are returned to the user

```python
# Example flow in recommendation_service.py
search_queries = await self.ollama.extract_search_queries(user_text)
# ["happy indie pop", "upbeat summer vibes", ...]

for query in search_queries:
    results = await self.mcp_client.search_songs(query)
    # Returns: [{ video_id, title, artist, album, duration, thumbnail_url }, ...]
```

### Running the MCP Server Standalone

The MCP server can run as a standalone process for testing:

```bash
cd backend
python -m app.mcp.youtube_music_server
```

It communicates via stdio (standard input/output) following the MCP specification.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      VibeFinder Backend                      │
│                                                              │
│  ┌──────────────┐    ┌─────────────┐    ┌────────────────┐  │
│  │   Ollama     │───▶│ MCP Client  │───▶│  MCP Server    │  │
│  │   (LLM)      │    │             │    │  (YouTube      │  │
│  └──────────────┘    └─────────────┘    │   Music)       │  │
│         │                               └───────┬────────┘  │
│         ▼                                       │           │
│  ┌──────────────┐                              │           │
│  │  ChromaDB    │                              ▼           │
│  │ (Preferences)│                     ┌────────────────┐   │
│  └──────────────┘                     │   ytmusicapi   │   │
│                                       │    (Library)   │   │
│                                       └───────┬────────┘   │
│                                               │            │
└───────────────────────────────────────────────┼────────────┘
                                                ▼
                                    ┌────────────────────┐
                                    │  YouTube Music API │
                                    │    (Unofficial)    │
                                    └────────────────────┘
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `mcp` | Official MCP SDK from Anthropic |
| `ytmusicapi` | Unofficial YouTube Music API wrapper |


## What to improve

Possible next steps and integrations (TODO / roadmap):

1. **Link with YouTube Music account** — Full OAuth flow and persistent account linking so recommendations and library actions run as the authenticated user.
2. **MCP playlist workflows** — Use MCP to add recommended songs to **new or existing** playlists on that linked YouTube Music account.
3. **Synced likes / dislikes** — When a user likes or dislikes in VibeFinder, mirror that as likes/dislikes (or library signals) on YouTube Music where the API allows it.
4. **Langfuse prompt management** — Centralize and version LLM prompts in Langfuse (fetch, evaluate, and iterate on prompts used for recommendations instead of only hard-coded strings).

## License

MIT
