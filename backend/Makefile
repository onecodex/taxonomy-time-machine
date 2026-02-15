default: events.db
	./taxonomy_time_machine/query.py 2916678
	./taxonomy_time_machine/get_lineage.py 418784

dumps:
	scripts/fetch-data.sh

migrate:
	alembic upgrade head

events.db: dumps migrate
	ttm-load --db-path $@

events-all.db: dumps
	ttm-load --always-insert --db-path $@

test-lineages: events.db
	./taxonomy_time_machine/check_lineages.py
