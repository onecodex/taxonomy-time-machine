default: events.db
	./scripts/query.py 2916678
	./scripts/get-lineage.py 418784

dumps:
	scripts/fetch-data.sh

events.csv: dumps
	scripts/create-events-csv.py

events.db: events.csv
	scripts/load-data.sh
