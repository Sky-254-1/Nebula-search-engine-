00;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}<div align="center">

# 🌌 Nebula Search

**Private · Offline-Capable · AI-Powered · Hybrid Search Engine**

[![License: MIT](https://img.shields.io/badge/License-MIT-7c5cfc.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)
[![PWA](https://img.shields.io/badge/PWA-Enabled-5A0FC8.svg?logo=pwa&logoColor=white)](#)

<br/>

A modern search platform that combines web search, offline document search, semantic search, AI-powered answers, and encrypted P2P sharing — all with a privacy-first approach and zero tracking.

[Getting Started](#installation) · [Features](#features) · [API Docs](#api-documentation) · [Docker](#docker) · [Contributing](#contributing)

</div>

---

## Architecture

```mermaid
graph LR
    subgraph "Frontend"
        A["HTML / CSS / JS"]
        B["IndexedDB"]
        C["Service Worker / PWA"]
    end

    subgraph "Backend"
        D["FastAPI"]
        E["PostgreSQL"]
        F["Redis"]
        G["JWT Auth"]
    end

    subgraph "AI"
        H["OpenAI-Compatible API"]
    end

    subgraph "Deployment"
        I["Docker"]
        J["Nginx"]
        K["HTTPS"]
    end

    A --> D
    A --> B
    A --> C
    D --> E
    D --> F
    D --> G
    D --> H
    I --> D
    J --> I
    K --> J
```

| Layer        | Stack                                       |
| ------------ | ------------------------------------------- |
| **Frontend** | HTML, CSS, JavaScript, IndexedDB, PWA       |
| **Backend**  | FastAPI, PostgreSQL, Redis, JWT              |
| **AI**       | OpenAI-compatible API                       |
| **Deploy**   | Docker, Nginx, HTTPS                        |

---

## Features

### 🔍 Search

| Feature           | Description                                                        |
| ----------------- | ------------------------------------------------------------------ |
| **Web Search**    | Query the web via Wikipedia, Brave Search, or SerpAPI backends     |
| **Semantic Search** | Offline vector similarity using Transformers.js (`all-MiniLM-L6-v2`) |
| **Offline Search** | TF-IDF + semantic ranking across locally uploaded documents        |
| **RSS Search**    | Aggregate and search across RSS/Atom feeds                         |
| **Saved Pages**   | Save web pages to a local offline library and search within them   |

### 🧠 AI

| Feature              | Description                                              |
| -------------------- | -------------------------------------------------------- |
| **AI Answers**       | Instant answers via OpenAI API or DuckDuckGo fallback    |
| **Search Summaries** | AI-generated summaries from top search results           |
| **Query Synthesis**  | Combine multiple result snippets into a coherent overview |

### 🔒 Privacy

| Feature             | Description                                        |
| ------------------- | -------------------------------------------------- |
| **Private Mode**    | Disable all history recording with one toggle      |
| **Offline Indexing** | Documents are indexed and searched entirely locally |
| **No Tracking**     | Zero analytics, zero telemetry, zero cookies       |
| **Local Caching**   | Results and assets cached in IndexedDB and Service Worker |

### 🔐 Authentication

| Feature                | Description                                    |
| ---------------------- | ---------------------------------------------- |
| **Signup / Login**     | Email + password registration                  |
| **JWT Tokens**         | Stateless authentication with 24h expiry       |
| **Session Management** | Persistent login state stored in IndexedDB     |

### 📦 More

| Feature              | Description                                                  |
| -------------------- | ------------------------------------------------------------ |
| **Bookmarks**        | Save and manage favorite search results                      |
| **Search History**   | Full history with export/import (JSON), sidebar view         |
| **File Upload**      | Upload `.txt`, `.html`, `.md`, `.csv` for offline search     |
| **P2P Sharing**      | Encrypted peer-to-peer sharing via PeerJS + AES-GCM          |
| **Voice Search**     | Speech-to-text input via Web Speech API                       |
| **Dark / Light Mode** | Animated theme toggle with starfield background              |
| **Keyboard Shortcuts** | `/` focus, `Ctrl+K` palette, `Ctrl+H` history, `Ctrl+Enter` search |

---

## Project Structure

```
nebula/
├── frontend/
│   ├── index.html                 # Main entry point
│   ├── manifest.json              # PWA manifest
│   ├── sw.js                      # Service worker (offline caching)
│   ├── css/
│   │   └── style.css              # Themed, animated styles
│   └── js/
│       ├── app.js                 # Initialization & routing
│       ├── db.js                  # IndexedDB helpers
│       ├── search.js              # Search orchestrator
│       ├── search-web.js          # Web search backends
│       ├── search-offline.js      # TF-IDF + semantic offline search
│       ├── ai.js                  # AI answer & synthesis
│       ├── history.js             # Search history management
│       ├── bookmarks.js           # Bookmark CRUD
│       ├── library.js             # Offline saved-page library
│       ├── documents.js           # File upload & indexing
│       ├── rss.js                 # RSS feed management
│       ├── share.js               # Encrypted P2P sharing
│       ├── voice.js               # Voice search
│       ├── suggestions.js         # Autocomplete dropdown
│       ├── spelling.js            # "Did you mean" corrections
│       ├── synthesize.js          # Multi-result synthesis
│       ├── surprise.js            # Random article discovery
│       ├── settings.js            # Settings modal
│       ├── auth.js                # Signup / login / logout
│       ├── theme.js               # Dark ↔ light theme
│       ├── starfield.js           # Animated canvas background
│       ├── shortcuts.js           # Keyboard shortcuts
│       └── utils.js               # Shared helpers
│
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point, CORS, routers
│   │   ├── config.py              # Settings from environment
│   │   ├── database.py            # PostgreSQL connection (async)
│   │   ├── models/                # SQLAlchemy / Pydantic models
│   │   ├── routes/                # API route modules
│   │   │   ├── auth.py            # /api/v1/auth/*
│   │   │   ├── search.py          # /api/v1/search/*
│   │   │   └── ai.py              # /api/v1/ai/*
│   │   ├── services/              # Business logic
│   │   │   ├── search/            # Search provider integrations
│   │   │   ├── auth/              # Password hashing, JWT
│   │   │   ├── ai/                # AI completion service
│   │   │   └── storage/           # File & cache management
│   │   ├── middleware/            # Rate limiting, logging
│   │   └── utils/                 # Shared utilities
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── docker-compose.yml
├── LICENSE
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or SQLite for development)
- Redis (optional, for caching & rate limiting)
- Node.js is **not** required — the frontend is vanilla JS

### 1. Clone

```bash
git clone https://github.com/Sky-254-1/Nebula-search-engine-.git
cd Nebula-search-engine-/backend
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values (see [Environment Variables](#environment-variables)).

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

| Endpoint    | URL                          |
| ----------- | ---------------------------- |
| **API**     | http://localhost:8000        |
| **Docs**    | http://localhost:8000/docs   |
| **ReDoc**   | http://localhost:8000/redoc  |

### 5. Open the frontend

Open `frontend/index.html` in your browser, or serve it with any static file server:

```bash
cd ../frontend
python -m http.server 3000
```

Then visit http://localhost:3000.

---

## Docker

Build and run the entire stack (backend + PostgreSQL + Redis) with one command:

```bash
docker compose up --build
```

This starts:

| Service        | Port  |
| -------------- | ----- |
| **Backend API** | 8000 |
| **PostgreSQL**  | 5432 |
| **Redis**       | 6379 |

To run in detached mode:

```bash
docker compose up --build -d
```

To stop:

```bash
docker compose down
```

---

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://nebula:nebula@localhost:5432/nebula

# Authentication
JWT_SECRET=your-secret-key-change-this-in-production

# AI (optional — enables AI answers)
OPENAI_API_KEY=sk-...

# Redis (optional — enables caching & rate limiting)
REDIS_URL=redis://localhost:6379/0

# Environment
APP_ENV=development
```

| Variable         | Required | Description                                  |
| ---------------- | -------- | -------------------------------------------- |
| `DATABASE_URL`   | Yes      | PostgreSQL connection string                 |
| `JWT_SECRET`     | Yes      | Secret key for signing JWT tokens            |
| `OPENAI_API_KEY` | No       | OpenAI API key for AI-powered answers        |
| `REDIS_URL`      | No       | Redis URL for caching and rate limiting      |
| `APP_ENV`        | No       | `development` or `production` (default: dev) |

---

## API Documentation

Once the server is running, interactive API docs are available at:

- **Swagger UI** — http://localhost:8000/docs
- **ReDoc** — http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint                  | Description              | Auth     |
| ------ | ------------------------- | ------------------------ | -------- |
| POST   | `/api/v1/auth/signup`     | Register a new user      | No       |
| POST   | `/api/v1/auth/login`      | Login, receive JWT token | No       |
| GET    | `/api/v1/search/web`      | Web search               | Required |
| POST   | `/api/v1/ai/ask`          | AI-powered answer        | Required |

---

## Keyboard Shortcuts

| Shortcut       | Action                   |
| -------------- | ------------------------ |
| `/`            | Focus search bar         |
| `Ctrl + Enter` | Execute search           |
| `Ctrl + K`     | Command palette          |
| `Ctrl + H`     | Toggle history sidebar   |
| `Ctrl + B`     | Open bookmarks           |
| `Ctrl + S`     | Open share modal         |
| `Escape`       | Close modal / dropdown   |

---

## Production Deployment

For production environments, ensure the following:

- **HTTPS** — Terminate TLS at Nginx or your load balancer
- **Reverse Proxy** — Use Nginx to proxy requests to Uvicorn
- **HTTPOnly Cookies** — Store JWT in secure, HTTPOnly cookies (not localStorage)
- **Rate Limiting** — Enable Redis-backed rate limiting middleware
- **Monitoring** — Add health checks, structured logging, and alerting
- **Secrets** — Use a secrets manager; never commit `.env` to version control
- **CORS** — Restrict `allow_origins` to your frontend domain

Example Nginx config:

```nginx
server {
    listen 443 ssl;
    server_name search.yourdomain.com;

    ssl_certificate     /etc/ssl/certs/nebula.pem;
    ssl_certificate_key /etc/ssl/private/nebula.key;

    location / {
        root /var/www/nebula/frontend;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:80
```

---

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the [MIT License](LICENSE).

```
MIT License · Copyright (c) 2026 Sky-254-1
```
