# API Service

Future FastAPI application service.

Responsibilities:
- learner profile and progression
- curriculum graph and checkpoints
- session state and evidence
- REST endpoints for the web app

Database bootstrap:
- `alembic upgrade head`
- `alembic revision --autogenerate -m "describe change"`
