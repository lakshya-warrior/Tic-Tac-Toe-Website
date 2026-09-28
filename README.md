## Database Architecture

We used a dual-database architecture to manage both structured data and unstructured binary data. 

### 1. Relational Schema (MySQL)
**Database:** `arena_db`
**Table:** `users`

| Column Name  | Data Type    | Constraints                  | Default Value |
|--------------|--------------|------------------------------|---------------|
| `uid`        | VARCHAR(255) | PRIMARY KEY                  | None          |
| `name`       | VARCHAR(255) | NOT NULL                     | None          |
| `elo_rating` | INT          |                              | 1200          |
| `is_online`  | BOOLEAN      |                              | FALSE         |

**Initialization SQL: (in init.sql)**
```sql
CREATE DATABASE IF NOT EXISTS arena_db;
USE arena_db;

CREATE TABLE IF NOT EXISTS users (
    uid VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    elo_rating INT DEFAULT 1200,
    is_online BOOLEAN DEFAULT FALSE
);
```

### NoSQL Schema (MongoDB)
**Database:** `arena_db` 
**Collection:** `profile_images`

MongoDB is used in this app to store the raw binary data of images

**Document Structure:**
```json
{
  "_id": "ObjectId(...)",
  "uid": "String (Matches MySQL Primary Key)",
  "image_data": "BSON Binary Data (Raw Bytes)"
}
```

---

## 2. Initializing Databases..

The project uses containerized databases to ensure consistency across environments. You must have **Docker** or **Podman**, and **uv** installed on your system.

### Method 1: Automated Setup

1. Ensure the script is executable:
   ```bash
   chmod +x start.sh
   ```
2. Run the initialization script:
   ```bash
   ./start.sh
   ```

### Method 2: Manual Setup
If you prefer to initialize the environment manually step-by-step, execute the following commands from the project root directory.

1. Boot the database containers:
   ```bash
   podman-compose up -d
   ```
   *(If using Docker, replace `podman-compose` with `docker compose`)*.

2. Wait for mysql to fully load, then inject relational schema.
   ```bash
   cat init.sql | docker compose exec -T mysql-db mysql -u root -parena_root arena_db
   ```
   *(Or if using podman-compose: `cat init.sql | podman-compose exec -T mysql-db mysql -u root -parena_root arena_db`)*.

3. Sync Python dependencies and run the data harvester to populate both databases:
   ```bash
   uv sync
   uv run harvest_data.py
   ```

---

## 3. Starting the Web Server & WebSocket Services

To start the server, execute the following command from the project root directory:

```bash
uv run python -m app.main
```

Once running, the services will be available at:
* **HTTP API:** `http://127.0.0.1:8000`
* **API Documentation:** `http://127.0.0.1:8000/docs`

---

## Resources & Documentation
* [Pandas CSV reading](https://www.geeksforgeeks.org/pandas/reading-csv-files-in-python/)
* [W3Schools SQL Tutorial](https://www.w3schools.com/sql/)
* [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
* [FastAPI Testing WebSockets](https://fastapi.tiangolo.com/advanced/testing-websockets/)
* [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/)