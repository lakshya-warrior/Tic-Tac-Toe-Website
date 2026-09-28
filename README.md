# Tic-Tac-Toe Arena 🎮

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-enabled-2496ED.svg)](https://www.docker.com/)

A real-time, competitive multiplayer Tic-Tac-Toe web platform featuring biometric facial recognition authentication, live matchmaking lobbies, interactive in-game chat, and automated ELO rating tracking.

---

## ✨ Features

- **Biometric Facial Recognition Authentication:** Seamless, passwordless login powered by client webcam capture and server-side face embeddings comparison.
- **Real-Time Multiplayer & Chat:** WebSocket-driven game state synchronization, instant challenge invitations, and live lobby/game chat.
- **ELO Rating & Leaderboard:** Dynamic chess-style ELO rating computation updated after every match, persisted in SQL with real-time leaderboard rankings.
- **Dual-Database Architecture:**
  - **MySQL (Relational):** Manages structured user metadata, credentials, live online statuses, and ELO ratings.
  - **MongoDB (NoSQL):** Stores high-density binary image data and face profile records.
- **Containerized Environment:** Pre-configured Docker/Podman compose workflows for effortless local deployment.

---

## 🏗️ Architecture & Schemas

### 1. Relational Schema (MySQL)
- **Database:** `arena_db`
- **Table:** `users`

| Column Name  | Data Type    | Constraints                  | Default Value | Description                      |
|--------------|--------------|------------------------------|---------------|----------------------------------|
| `uid`        | VARCHAR(255) | PRIMARY KEY                  | None          | Unique player identification      |
| `name`       | VARCHAR(255) | NOT NULL                     | None          | Display name                     |
| `elo_rating` | INT          |                              | 1200          | Player skill rating              |
| `is_online`  | BOOLEAN      |                              | FALSE         | Real-time connection presence    |

### 2. NoSQL Schema (MongoDB)
- **Database:** `arena_db`
- **Collection:** `profile_images`

```json
{
  "_id": "ObjectId(...)",
  "uid": "String (Matches MySQL Primary Key)",
  "image_data": "BSON Binary Data (Raw Bytes)"
}
```

---

## 📁 Repository Structure

```text
├── app/
│   ├── __init__.py
│   ├── auth.py                  # Facial authentication router
│   ├── database.py              # MySQL connection pool & MongoDB client
│   ├── main.py                  # FastAPI application & WebSocket ConnectionManager
│   └── sql_functions.py         # Database query helpers & ELO calculation
├── frontend/
│   └── index.html               # Facial login & camera capture UI
├── static/
│   ├── style.css                # Dark-mode gaming UI styling
│   ├── script.js                # Game engine, WebSocket events & canvas rendering
│   └── favicon.ico
├── utils/
│   └── facial_recognition_module.py  # Face detection & 128-d vector encoding
├── batch_data.csv               # Sample seed dataset for player profiles
├── docker-compose.yml           # Database container definitions (MySQL & MongoDB)
├── init.sql                     # SQL schema bootstrap script
├── harvest_data.py              # Seed pipeline to populate databases
├── start.sh                     # Automated environment launch script
├── pyproject.toml               # Python project configuration & dependencies
├── .env.example                 # Environment variables template
└── LICENSE                      # MIT License
```

---

## 🚀 Getting Started

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) or [Podman](https://podman.io/)
- Python `>= 3.13`
- [uv](https://github.com/astral-sh/uv) (recommended Python package manager)

### Method 1: Automated Launch (Recommended)

1. Make the start script executable:
   ```bash
   chmod +x start.sh
   ```

2. Run the initialization script:
   ```bash
   ./start.sh
   ```
   *This automatically creates `.env` from `.env.example`, boots containerized databases, initializes schemas, seeds sample player data, and starts the FastAPI server.*

---

### Method 2: Manual Step-by-Step Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/Tic-Tac-Toe-Website.git
   cd Tic-Tac-Toe-Website
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

3. **Start database containers:**
   ```bash
   docker compose up -d
   ```
   *(Or with Podman: `podman-compose up -d`)*

4. **Initialize MySQL schema:**
   ```bash
   cat init.sql | docker compose exec -T mysql-db mysql -u root -parena_root arena_db
   ```

5. **Install dependencies and seed sample data:**
   ```bash
   uv sync
   uv run harvest_data.py
   ```

6. **Start the application server:**
   ```bash
   uv run python -m app.main
   ```

---

## 🌐 Endpoints & Usage

Once started, the application will be accessible at:
- **Web App & Login:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Docs (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative Docs (ReDoc):** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | `GET` | Serves camera authentication login page |
| `/login` | `POST` | Authenticates facial image upload against database vector encodings |
| `/logout/{uid}` | `POST` | Logs out player and resets online status |
| `/game` | `GET` | Main multiplayer arena, lobby, and leaderboard interface |
| `/ws/{client_id}` | `WebSocket` | Real-time WebSocket connection for matchmaking, game moves, and chat |

---

## ⚙️ Environment Configuration

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `MYSQL_HOST` | `127.0.0.1` | MySQL hostname |
| `MYSQL_PORT` | `3307` | MySQL external port |
| `MYSQL_USER` | `root` | MySQL username |
| `MYSQL_PASSWORD` | `arena_root` | MySQL password |
| `MONGO_URI` | `mongodb://127.0.0.1:27017/` | MongoDB connection URI |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details.