# DuoNiche Backend

## Overview

DuoNiche Backend is a FastAPI-based service that leverages Large Language Models (LLMs) to generate and assess language-learning exercises. It provides RESTful endpoints for user management, exercise generation and validation, payment processing (Telegram Stars), and notification scheduling.

For a deeper dive into the project's architecture and workflows, please see:

-   [**Detailed Project Overview (EN)**](./docs/project_overview_en.md)
-   [**Подробный обзор проекта (RU)**](./docs/project_overview_ru.md)

The working Telegram bot for learning Bulgarian can be found at: [https://t.me/DuoBG_bot](https://t.me/DuoBG_bot)

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

-   **LLM-Powered Exercise Generation**: Dynamically creates language exercises (fill-in-the-blank, choose the correct sentence, etc.) via OpenAI LLMs (using LangChain).
-   **Automated Assessment**: Validates user responses to exercises using LLMs.
-   **User Management**: Handles user registration, profile updates, and status (active/blocked).
-   **User Progress Tracking**: Manages user sessions, sets, exercise limits, and streaks.
-   **Payment Processing**: Integrates with Telegram Stars for unlocking additional sessions.
-   **Monitoring**: Prometheus instrumentation for application metrics.
-   **Error Tracking**: Sentry integration for real-time error reporting.
-   **Database Migrations**: Uses Alembic for managing database schema changes.
-   **Specific Exercise Generators**: Includes a custom generator for Bulgarian accent exercises by scraping external resources.
-   **Background Audio Generation**: Creates audio for story exercises using Google TTS and stores it in Cloudflare R2.
-   **On-demand Detailed Reports**: Asynchronously generates and delivers detailed weekly user reports using ARQ workers.
-   **Automated Quality Monitoring**: Automatically identifies and flags potentially flawed exercises for review based on user performance.
-   **Multi-language Support**: Designed to support multiple languages for UI and exercise generation (e.g., Bulgarian, Serbian).

## Tech Stack

-   **Language**: Python 3.12+
-   **Framework**: FastAPI
-   **Database**: PostgreSQL (with `asyncpg` and `SQLAlchemy 2.0`)
-   **Migrations**: Alembic
-   **Cache/Queue**: Redis (used for asynchronous task caching and as a broker for Celery and ARQ)
-   **LLM & External Services**: OpenAI API (via `LangChain`), Google TTS, Cloudflare R2
-   **Task Queues**:
    -   `Celery`: For producing notification tasks.
    -   `arq`: For background report generation.
-   **HTTP Client**: `httpx`
-   **Containerization**: Docker & Docker Compose
-   **CI/CD**: GitHub Actions
-   **Monitoring**: Prometheus & `prometheus-fastapi-instrumentator`
-   **Error Tracking**: Sentry SDK
-   **Configuration**: `pydantic-settings`
-   **Web Scraping**: `lxml` (for `ChooseAccentGenerator`)
-   **Language Utilities**: `pycountry`
-   **Dependency Management & Tooling**: `uv`, `ruff`, `mypy`, `pytest`, `pre-commit`

## Project Structure

```text
.
├── .github/              # GitHub Actions (CI/CD)
├── alembic/              # Database migration scripts
├── app/                  # Main application package
│   ├── api/              # HTTP API definition (FastAPI)
│   ├── core/             # Core business logic and domain entities
│   ├── db/               # Database interaction layer
│   ├── infrastructure/   # Infrastructure clients (e.g., Redis)
│   ├── llm/              # LLM interaction logic (generation, validation, translation)
│   ├── services/         # External service clients (TTS, File Storage, etc.)
│   ├── utils/            # Utility functions
│   ├── workers/          # Background worker tasks (Celery, ARQ based)
│   ├── arq_config.py     # ARQ worker configuration
│   ├── celery_producer.py # Celery producer setup
│   ├── config.py         # Application settings
│   ├── main.py           # FastAPI app entrypoint
│   └── ...
├── infra/                # Infrastructure configurations (Docker, Nginx, Prometheus)
├── docs/                 # Detailed project documentation
├── tests/                # Automated tests
├── Dockerfile            # Dockerfile for application image
├── entrypoint.sh         # Docker entrypoint script (runs migrations)
├── pyproject.toml        # Project configuration (dependencies, tools)
└── README.md             # This file
```

-   Python 3.12+
-   Redis
-   PostgreSQL (>=14)
-   Docker & Docker Compose (for containerized setup)
-   `uv` (for Python package management, optional but recommended)

## Local Development

1.  **Clone the repository**
    ```bash
    git clone https://github.com/sldmxm/duoniche_backend.git
    cd duoniche_backend
    ```
2.  **Environment setup** (using `uv` and `venv`)
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt --dev
    ```
3.  **Install pre-commit hooks**
    ```bash
    pre-commit install
    # Optionally run on all files once
    # pre-commit run --all-files
    ```
4.  **Configure environment variables**
    Create a `.env` file in the project root based on `.env.example` (if provided) or the variables listed below.
    Key variables include `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, etc.
5.  **Start Redis & PostgreSQL**
    You can use Docker for this:
    ```bash
    cd infra/dev
    docker compose up -d db redis # Assuming you have a docker-compose for dev
    cd ../..
    ```
    Or run them natively if installed. Ensure PostgreSQL has a database named `duo` (or as configured) and a user `duo` with password `duo` (or as configured) with privileges.
6.  **Run database migrations**
    ```bash
    alembic upgrade head
    ```
7.  **Start application**
    ```bash
    python -m app.main
    ```
    or
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
8.  **View API docs**
    -   Swagger UI: http://localhost:8000/docs
    -   ReDoc: http://localhost:8000/redoc

## Docker Deployment

1.  Ensure Docker and Docker Compose are installed.
2.  Create an `infra/.env` file with production environment variables (see Environment Variables and `infra/docker-compose.prod.yml`).
3.  Navigate to the `infra` directory:
    ```bash
    cd infra
    ```
4.  Build and run the services using the production Docker Compose file:
    ```bash
    # Ensure the duo_shared network exists or remove 'external: true' from network definition if managing locally
    # sudo docker network create duo_shared
    sudo docker compose -f docker-compose.base.yml -f docker-compose.local.yml up --build -d
    ```
    (Use `docker-compose.local.yml` for local Docker testing which builds the image from local Dockerfile).
5.  The application should be accessible (e.g., via Nginx reverse proxy if configured).
6.  To stop services:
    ```bash
    sudo docker compose -f docker-compose.base.yml -f docker-compose.local.yml down
    ```

## Environment Variables

Key environment variables (see `app/config.py` for a comprehensive list):

| Variable                     | Description                                       | Required / Default         |
| :--------------------------- | :------------------------------------------------ | :------------------------- |
| `ENV`                        | Deployment environment (`dev`/`prod`)             | `dev`                      |
| `DEBUG`                      | Debug mode (`True`/`False`)                       | `True`                     |
| `DATABASE_URL`               | PostgreSQL connection URL (asyncpg format)        | **Required**               |
| `REDIS_URL`                  | Redis connection URL                              | **Required**               |
| `OPENAI_API_KEY`             | OpenAI API key                                    | **Required**               |
| `OPENAI_MAIN_MODEL_NAME`     | OpenAI model for exercise generation              | **Required**               |
| `OPENAI_ASSESSOR_MODEL_NAME` | OpenAI model for exercise quality assessment      | **Required**               |
| `OPENAI_TRANSLATOR_MODEL_NAME`| OpenAI model for feedback translation            | **Required**               |
| `SENTRY_DSN`                 | Sentry DSN for error tracking                     | Optional                   |
| `CELERY_BROKER_URL`          | URL for Celery broker (uses `REDIS_URL` if same)  | (Defaults to `REDIS_URL`)  |
| `NOTIFICATION_TASKS_QUEUE_NAME`| Celery queue name for notifications             | `notification_tasks_default`|
| ... (other DB, Redis, service-specific settings) ... |                                                   |                            |

## API Documentation

Interactive API documentation is available when the application is running:

-   **Swagger UI**: `/docs`
-   **ReDoc**: `/redoc`

## CI/CD Pipeline

-   **Trigger**: GitHub Actions workflow (`.github/workflows/deploy.yml`) on pushes to the `main` branch.
-   **Build**: Builds a Docker image, tags it with the commit SHA, and pushes it to GitHub Container Registry (GHCR).
-   **Deploy**:
    -   Creates an `.env` file on the runner using GitHub Secrets.
    -   Copies the `infra` directory (including the `.env` file and Nginx configs) to the production server via SCP.
    -   Connects to the production server via SSH.
    -   Logs in to GHCR on the remote server.
    -   Uses `docker compose` with `docker-compose.base.yml` and `docker-compose.prod.yml` to pull the new image and restart services.
-   **Secrets**: API keys, server credentials, and other sensitive data are managed via GitHub Secrets.

## Testing

Tests are written using `pytest`.

-   To run all tests:
    ```bash
    pytest --asyncio-mode=auto
    ```
-   To run tests excluding LLM integration tests (which might require API keys or be slow):
    ```bash
    pytest --asyncio-mode=auto --ignore=tests/llm
    ```
    (This is the default for pre-commit hooks).
-   Test database configuration is separate (see `settings.test_database_url`).
-   Fixtures for database sessions, HTTP client, and service mocks are defined in `tests/conftest.py`.

## Code Quality

-   **Linting & Formatting**: `ruff` (configured in `pyproject.toml`).
-   **Type Checking**: `mypy` (configured in `pyproject.toml`).
-   **Pre-commit Hooks**: Configured in `.pre-commit-config.yaml` to automatically run `ruff` (format & lint) and `mypy` before commits. Also exports `requirements.txt` using `uv`.

## Contributing

1.  Fork the repository.
2.  Create a feature branch: `git checkout -b feature/your-amazing-feature`.
3.  Make your changes.
4.  Ensure pre-commit hooks pass (or run them manually: `pre-commit run --all-files`).
5.  Write tests for new functionality.
6.  Ensure all tests pass: `pytest --asyncio-mode=auto`.
7.  Commit your changes with clear, descriptive messages.
8.  Push to your fork and open a Pull Request to the main repository.

## License

This project is licensed under the MIT License. See the `LICENSE` file (if present) for details.

## Contact

Maintainer: Maxim Solodilov (sldmxm@gmail.com)