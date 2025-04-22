{{ ... }}
# DuoNiche Backend

## Overview
DuoNiche Backend is a FastAPI-based service that leverages Large Language Models (LLMs) to generate and assess language-learning exercises. It provides RESTful endpoints for user management, exercise generation, evaluation, and monitoring.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [CI/CD Pipeline](#cicd-pipeline)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features
- **LLM-Powered Generation**: Dynamically create language exercises via OpenAI LLMs (LangChain).
- **Automated Assessment**: Validate user responses with pretrained LLMs.
- **User Management**: Registration, authentication, profile updates.
- **Monitoring**: Prometheus instrumentation for metrics.
- **Error Tracking**: Sentry integration for real-time error reporting.

## Tech Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Database**: PostgreSQL (asyncpg + SQLAlchemy 2.0)
- **Cache**: Redis
- **LLM**: OpenAI via LangChain
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus & prometheus-fastapi-instrumentator
- **Error Tracking**: Sentry SDK

## Project Structure
```text
.
├── app/                  # Main application package
│   ├── api/              # HTTP endpoints (versioned)
│   ├── core/             # Business logic & domain services
│   ├── db/               # Database models, sessions, migrations
│   ├── llm/              # LLM pipelines (generation & assessment)
│   ├── translator/       # Translation utilities
│   ├── utils/            # Shared helper functions
│   ├── config.py         # Application settings
│   ├── main.py           # FastAPI app entrypoint
│   ├── metrics.py        # Prometheus instrumentation
│   ├── logging_config.py # Logging configuration
│   └── sentry_sdk.py     # Sentry error tracking setup
├── alembic/              # Database migration scripts
├── infra/                # Docker Compose & infra configurations
├── tests/                # Test suite
├── .github/              # CI/CD workflows
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## Prerequisites
- Python 3.12+
- Redis (>=5.2.1)
- PostgreSQL (>=14)
- Docker & Docker Compose (for containerized setup)

## Local Development
1. **Clone the repository**
   ```bash
   git clone https://github.com/<username>/duoniche_backend.git
   cd duoniche_backend
   ```
2. **Environment setup**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **Install pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   pre-commit run --all-files
   ```
4. **Configure environment**
   create .env
5. **Start Redis & PostgreSQL**
   ```bash
   # Redis
   redis-server
   # PostgreSQL
   psql -U postgres -c "CREATE DATABASE duo; CREATE USER duo WITH PASSWORD 'duo'; GRANT ALL PRIVILEGES ON DATABASE duo TO duo;"
   ```
6. **Run migrations**
   ```bash
   alembic upgrade head
   ```
7. **Start application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
8. **View docs**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Docker Deployment
Build and run with Docker Compose:
create infra/.env
```bash
cd infra
docker compose -f infra/docker-compose.base.yml -f infra/docker-compose.local.yml up --build -d
```
- Access at http://localhost:8000
- Stop services: `docker compose down`

## Environment Variables
| Variable                     | Description                             | Required / Default |
| ---------------------------- | --------------------------------------- | ------------------ |
| ENV                          | Deployment environment (`dev`/`prod`)   | `dev`              |
| DEBUG                        | Debug mode (`True`/`False`)             | `True`             |
| DATABASE_URL                 | PostgreSQL URL (async)                  | Required           |
| REDIS_URL                    | Redis connection URL                    | Required           |
| OPENAI_API_KEY               | OpenAI API key                          | Required           |
| OPENAI_MAIN_MODEL_NAME       | Model for exercise generation           | Required           |
| OPENAI_ASSESSOR_MODEL_NAME   | Model for assessment                    | Required           |
| SENTRY_DSN                   | Sentry DSN                              | Optional           |
| POSTGRES_HOST / POSTGRES_PORT| Postgres host/port                      | `localhost:5432`   |
| REDIS_HOST / REDIS_PORT      | Redis host/port                         | `localhost:6379`   |

## API Documentation
Interactive docs available at:
- **Swagger**: `/docs`
- **ReDoc**: `/redoc`

## CI/CD Pipeline
- **Trigger**: GitHub Actions on pushes to `main`.
- **Build**: Docker image tagged and pushed to GitHub Container Registry.
- **Deploy**: SSH & Docker Compose deploy to production server.
- **Secrets**: Managed via GitHub Secrets.

## Testing
Run tests:
```bash
pytest --asyncio-mode=auto
```

## Code Quality
- **Linting**: ruff
- **Type Checking**: mypy
- **Formatting**: black (via ruff)
- **Pre-commit Hooks**: pre-commit

## Contributing
1. Fork repository.
2. Create branch: `git checkout -b feature/your-feature`.
3. Commit changes with clear messages.
4. Push and open a PR.
5. Ensure tests and lint checks pass.

## License
MIT License. See [LICENSE](LICENSE) for details.

## Contact
Maintainer: [Maxim Solodilov](mailto:sldmxm@gmail.com)