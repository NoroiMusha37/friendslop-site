COMPOSE := docker compose
# Lazy: only resolved by db-reset (needs .env)
PROJECT = $(shell $(COMPOSE) config | sed -n 's/^name: //p')

.DEFAULT_GOAL := help

.PHONY: help up down restart logs ps migrate migration admin seed smoke db-shell db-reset cli

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-15s %s\n", $$1, $$2}'

up: ## Build and start db + web in the background (API at http://localhost:8000)
	$(COMPOSE) up --build --detach --wait

down: ## Stop the stack, keep database data
	$(COMPOSE) down

restart: down up ## down + up

logs: ## Follow logs; service=<web|db> to filter
	$(COMPOSE) logs --follow $(service)

ps: ## Show service status
	$(COMPOSE) ps --all

migrate: ## Apply all pending migrations
	$(COMPOSE) run --rm web python manage.py migrate

migration: ## Create a migration; requires name=<slug>, optional app=<label>
	@test -n "$(name)" || (echo "usage: make migration name=<slug> [app=<label>]" && exit 1)
	$(COMPOSE) run --rm web python manage.py makemigrations --name "$(name)" $(app)

admin: ## Create a superuser (approved automatically); args="..." passthrough. Testing only
	$(COMPOSE) run --rm web python manage.py createsuperuser $(args)

seed: ## Not implemented: no seed data or seeder yet (RecipeNLG import is planned)
	@echo "make seed: not implemented yet (no seed data or seeder in the repo)" >&2; exit 1

smoke: ## Check the running app answers (admin login page, no health route yet)
	curl -fsS -o /dev/null http://localhost:8000/admin/login/
	@echo "ok: http://localhost:8000 is up"

db-shell: ## Open psql in the db container
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

db-reset: ## DESTRUCTIVE: delete the db container and its pgdata volume, start it again, migrate
	$(COMPOSE) rm --stop --force db
	docker volume rm --force $(PROJECT)_pgdata
	$(COMPOSE) up --detach --wait db
	$(MAKE) migrate

cli: ## Not implemented: no hand-run scripts yet
	@echo "make cli: not implemented yet (no hand-run scripts in the repo)" >&2; exit 1

# Swallow extra goals of `make cli <name> "<arg>"` so only the stub message prints
ifeq ($(firstword $(MAKECMDGOALS)),cli)
%:
	@:
endif
