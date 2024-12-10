default: events.db
	./scripts/query.py 2916678
	./scripts/get-lineage.py 418784
	./scripts/check-lineages.py

dumps:
	scripts/fetch-data.sh

events.db: dumps
	scripts/load-data.py
