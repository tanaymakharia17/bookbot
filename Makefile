COMPOSE ?= docker compose

.DEFAULT_GOAL := help

.PHONY: help env build up down restart logs ps migrate makemigrations shell superuser test reset

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.example if missing
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

build: env ## Build backend + frontend images
	$(COMPOSE) build

up: env ## Start the full stack in the background
	$(COMPOSE) up -d

down: ## Stop the stack
	$(COMPOSE) down

restart: down up ## Restart the stack

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

ps: ## List running services
	$(COMPOSE) ps

migrate: ## Apply database migrations
	$(COMPOSE) exec backend python manage.py migrate

makemigrations: ## Create new migrations
	$(COMPOSE) exec backend python manage.py makemigrations

shell: ## Open a Django shell
	$(COMPOSE) exec backend python manage.py shell

superuser: ## Create a Django admin user
	$(COMPOSE) exec backend python manage.py createsuperuser

test: ## Run backend tests
	$(COMPOSE) exec backend python manage.py test

reset: ## Stop the stack and delete volumes
	$(COMPOSE) down -v