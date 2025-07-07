# Codebase Overview for DuoNiche Backend

## 1. Project's General Purpose

DuoNiche Backend is a service built on the FastAPI framework. Its primary role is to provide the logic for a language-learning Telegram bot. The service utilizes Large Language Models (LLMs) to generate educational exercises and automatically verify user answers. It also manages user progress, handles payments (via Telegram Stars), and schedules notifications.

## 2. Project Structure

The project has the following main directory structure:
```text
.
├── .github/              # GitHub Actions configurations (CI/CD)
│ └── workflows/
│       └── deploy.yml    # Production deployment workflow
├── alembic/              # Database migration scripts (SQLAlchemy Alembic)
│   ├── versions/         # Specific migration version files
│   ├── env.py            # Migration execution environment
│   └── ...
├── app/                  # Main application package
│   ├── api/              # HTTP API definition (FastAPI)
│   │   ├── schemas/      # Pydantic schemas for API requests/responses
│   │   └── v1/           # API versioning (v1)
│   │       ├── endpoints/ # Handlers for specific endpoints
│   │       └── api.py     # Router for API v1
│   ├── core/             # Core business logic and domain entities
│   │   ├── entities/     # Pydantic models for domain entities
│   │   ├── interfaces/   # Abstract base classes (interfaces)
│   │   ├── repositories/ # Abstract base classes (interfaces) for repositories
│   │   ├── services/     # Business logic services
│   │   └── value_objects/ # Value Objects
│   ├── db/               # Database interaction
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── repositories/ # SQLAlchemy repository implementations
│   │   └── db.py         # DB engine and session setup
│   ├── infrastructure/   # External infrastructure dependencies (Redis)
│   │   └── redis_client.py
│   ├── llm/              # Logic for interacting with LLMs
│   │   ├── assessors/    # Assessors for exercise quality
│   │   ├── generators/   # LLM-based exercise generators
│   │   ├── interfaces/   # Interfaces for LLM generators/validators
│   │   ├── validators/   # LLM-based answer validators
│   │   ├── factories.py  # Factories for creating generators/validators
│   │   ├── llm_base.py   # Base class for LLM services
│   │   ├── llm_service.py # Service for generation and validation via LLM
│   │   └── llm_translator.py # Service for translation via LLM
│   ├── services/         # External service clients (TTS, File Storage)
│   │   ├── file_storage_service.py # Cloudflare R2 file storage client
│   │   ├── google_translator.py    # Google Translate client
│   │   ├── notification_producer.py # Service for enqueuing notification tasks
│   │   └── tts_service.py          # Google Text-to-Speech client
│   ├── workers/          # Background workers
│   │   ├── arq_tasks/    # Tasks for the ARQ worker (e.g., reports)
│   │   ├── exercise_quality_monitor.py # Monitors exercise quality
│   │   ├── exercise_review_processor.py # Processes exercises flagged for review
│   │   ├── exercise_stock_refill.py # Refills the stock of exercises
│   │   ├── metrics_updater.py # Updates user metrics
│   │   └── notification_scheduler.py # Schedules user notifications
│   ├── arq_config.py     # Configuration for the ARQ worker
│   ├── celery_producer.py # Celery client setup
│   ├── config.py         # Application settings
│   ├── main.py           # FastAPI application entry point
│   └── ...
├── docs/                 # Project documentation
│   ├── project_overview_en.md # This file
│   └── project_overview_ru.md # Russian version of the overview
├── infra/                # Infrastructure configurations (Docker Compose, Nginx)
├── tests/                # Automated tests
├── Dockerfile            # Dockerfile for building the application image
├── entrypoint.sh         # Entrypoint script for the Docker container
├── pyproject.toml        # Project configuration (uv, ruff, mypy, pytest)
└── README.md             # Project README
```

## 3. Key Modules and Their Functionality

*   **`app/main.py`**: The entry point for the FastAPI application. It defines the `lifespan` context manager to initialize and gracefully shut down resources (DB, Redis, HTTPX client, LLM services, cache, notification producer). It also starts background workers on startup.
*   **`app/core/`**: Contains the core business logic and domain entities, aiming for independence from specific frameworks and external services.
    *   **`services/`**: Houses service classes that encapsulate business logic (e.g., `UserProgressService`, `ExerciseService`, `PaymentService`).
    *   **`entities/`**: Pydantic models representing the main domain entities (e.g., `User`, `Exercise`, `UserBotProfile`).
*   **`app/db/`**: The data access layer, implementing interactions with the PostgreSQL database using SQLAlchemy.
*   **`app/llm/`**: Manages integration with Large Language Models (LLMs), primarily via the LangChain library for the OpenAI API.
    *   **`generators/`**: Contains generator classes for different exercise types. `choose_accent_generator.py` is a special case that uses web scraping instead of an LLM.
    *   **`validators/`**: Contains validator classes for checking user answers.
    *   **`assessors/`**: Includes logic for assessing the quality of exercises.
*   **`app/services/`**: Contains clients for external services.
    *   **`tts_service.py`**: Integrates with Google Text-to-Speech to generate audio for exercises.
    *   **`file_storage_service.py`**: Handles file uploads to Cloudflare R2.
    *   **`notification_producer.py`**: Creates and enqueues notification tasks into a Celery queue.
*   **`app/workers/` & `app/arq_config.py`**: Contains background tasks.
    *   **`arq_config.py`** configures the ARQ worker for deferred tasks (like report generation).
    *   **`exercise_stock_refill.py`**: Periodically generates new exercises to maintain a sufficient stock.
    *   **`exercise_quality_monitor.py` & `exercise_review_processor.py`**: Work together to automatically assess exercise quality based on user performance and LLM analysis.
    *   **`notification_scheduler.py`**: Periodically checks user profiles to schedule notifications (e.g., session ready, long break reminders).
*   **`infra/`**: Contains configurations for deploying the application using Docker and Docker Compose, including setups for PostgreSQL, Redis, Nginx, and Prometheus.

## 4. Core Workflows

1.  **User Onboarding/Update**: The Telegram bot sends user data to the `PUT /api/v1/users/` endpoint. `UserService` and `UserBotProfileService` create or update the user's record and their bot-specific profile.

2.  **Getting the Next Action/Exercise**: The bot requests `GET /api/v1/users/{user_id}/bots/{bot_id}/next-action/`. `UserProgressService` analyzes the user's state (progress, limits) and decides the next action: return a new exercise, a message about reaching a limit, or an offer to pay for an early unlock.

3.  **Answering and Validation**: The user's answer is sent to `POST /api/v1/exercises/{exercise_id}/validate/`. `ExerciseService` (via `AttemptValidator`) checks a cache, then the database for a previously validated answer. If not found, it uses `LLMService` to validate the answer. The result is cached and stored, and a validation result is returned to the user.

4.  **Background Audio Generation**: When an exercise of type `StoryComprehension` is generated by the `exercise_stock_refill` worker, it calls `TTSService` to synthesize speech. The resulting audio file is uploaded to Cloudflare R2 via `FileStorageService`, and its Telegram `file_id` is cached. The URL and `file_id` are saved with the exercise.

5.  **Automated Quality Monitoring and Review**: The `exercise_quality_monitor` worker periodically calculates a weighted error rate for exercises. If an exercise's error rate exceeds a threshold, its status is set to `PENDING_REVIEW`. The `exercise_review_processor` worker then picks up these exercises, uses an LLM to analyze them, and decides whether to re-publish, archive, or flag for manual admin review.

6.  **On-Demand Detailed Report Generation**: A user requests a detailed report via an API endpoint. `UserReportService` enqueues a task (`generate_and_send_detailed_report_arq`) in ARQ. The ARQ worker generates the report text using an LLM, saves it to the database, and schedules another delayed task to send the notification to the user after a few minutes.

## 5. Dependencies and Integrations

-   **Primary Framework**: FastAPI
-   **Database**: PostgreSQL (with `asyncpg` and `SQLAlchemy 2.0`)
-   **Migrations**: Alembic
-   **Caching/Queuing**:
    -   **Redis**: Used for asynchronous task caching and as a broker for Celery and ARQ.
    -   **Celery**: Used as a producer to send notification tasks to a separate Notifier service.
    -   **ARQ**: Used for handling asynchronous background jobs like report generation.
-   **LLM (Large Language Models)**: OpenAI API (via `LangChain`)
-   **Text-to-Speech (TTS)**: Google GenAI API
-   **File Storage**: Cloudflare R2 (S3-compatible, via `aioboto3`)
-   **HTTP Client**: `httpx`
-   **Monitoring**: Prometheus
-   **Error Tracking**: Sentry
-   **Dependency Management**: `uv`

---
