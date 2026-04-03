default: events.db

dumps:
	scripts/fetch-data.sh

migrate:
	alembic upgrade head

events.db: dumps migrate
	ttm-load --db-path $@

test-lineages: events.db
	./taxonomy_time_machine/check_lineages.py
