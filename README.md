# LawFlow

AI-powered legal education platform with interactive tutoring, document analysis, and spaced repetition.

## Quick Start (Development)

See [LawFlow/SETUP.md](LawFlow/SETUP.md) for full local development instructions.

## Hosting & Deployment

### Docker Compose (recommended)

The simplest way to run LawFlow in production is with Docker Compose.

```bash
cd LawFlow

# Create your environment file
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY and FLASK_SECRET_KEY

# Build and start
docker compose up -d

# App is now available at http://localhost
```

This starts two containers:

| Service    | Role                                      |
|------------|-------------------------------------------|
| `backend`  | Flask API served by gunicorn on port 5002 |
| `frontend` | React app served by nginx on port 80      |

Uploaded files and the SQLite database are stored in a Docker volume (`upload-data`).

### Deploy to a Cloud VM

1. Provision an Ubuntu VM (e.g. AWS EC2, DigitalOcean Droplet, Azure VM).
2. Install Docker and Docker Compose.
3. Clone this repo and follow the Docker Compose steps above.
4. Point a domain to the VM and add TLS with a reverse proxy (e.g. Caddy or Traefik).

### Deploy to a PaaS

LawFlow can be deployed to platforms like **Railway**, **Render**, or **Fly.io**:

- Use `LawFlow/api/Dockerfile` for the backend service.
- Use `LawFlow/frontend/Dockerfile` for the frontend service.
- Set the `ANTHROPIC_API_KEY` and `FLASK_SECRET_KEY` environment variables in the platform dashboard.

### Environment Variables

| Variable             | Required | Default                    | Description                   |
|----------------------|----------|----------------------------|-------------------------------|
| `ANTHROPIC_API_KEY`  | Yes      | —                          | Claude API key                |
| `FLASK_SECRET_KEY`   | Yes      | `dev-secret-change-me`     | Secret key for sessions       |
| `FLASK_DEBUG`        | No       | `true`                     | Set to `false` in production  |
| `FLASK_HOST`         | No       | `127.0.0.1`                | Bind address                  |
| `FLASK_PORT`         | No       | `5002`                     | API port                      |
| `CLAUDE_MODEL`       | No       | `claude-sonnet-4-20250514` | Anthropic model to use        |
| `MAX_UPLOAD_MB`      | No       | `100`                      | Max upload file size          |

### CI / CD

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and PR to `main`:

1. **build-backend** – installs Python deps and verifies the app can be imported.
2. **build-frontend** – installs Node deps and runs `npm run build`.
3. **docker** – builds the Docker images and runs a health-check smoke test.
