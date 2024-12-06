default: events.db
	./scripts/query.py 2916678
	./scripts/get-lineage.py 418784

dumps:
	scripts/fetch-data.sh

events.db: dumps
	scripts/load-data.py

test-lineages: events.db
	./scripts/check-lineages.py
