default: events.db
	./taxonomy_time_machine/query.py 2916678
	./taxonomy_time_machine/get_lineage.py 418784

dumps:
	scripts/fetch-data.sh

events.db: dumps
	./taxonomy_time_machine/load_data.py \
		--db-path $@

events-all.db: dumps
	./taxonomy_time_machine/load_data.py \
		--always-insert \
		--db-path $@

check-lineages: events.db
	./taxonomy_time_machine/check_lineages.py
