# Bookbot

Agentic AI bookkeeping workspace for CPA firms — turns raw client documents into
auditable, double-entry ledger entries with a human-in-the-loop review.

## Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Django 5 + Django REST Framework    |
| Database  | PostgreSQL 16                       |
| Queue     | Redis 7 + Celery                    |
| Frontend  | Streamlit                           |
| VLM       | OpenRouter (configurable model)     |
| Packaging | Docker + Docker Compose             |

## Repository layout

```
bookbot/
├── backend/          # Django project (API, pipeline, agents)
├── frontend/         # Streamlit app
├── docker-compose.yml
└── Makefile
```

## Quickstart

```bash
cp .env.example .env
docker compose up --build
```

| Service  | URL                     |
|----------|-------------------------|
| Backend  | http://localhost:8000   |
| Frontend | http://localhost:8501   |
| Health   | http://localhost:8000/api/v1/health/ |

## Development

```bash
make build     # build images
make up        # start stack
make down      # stop stack
make logs      # tail logs
make migrate   # run migrations
make test      # run tests
```

## License

MIT — see [LICENSE](LICENSE).
