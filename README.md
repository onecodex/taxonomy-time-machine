# taxonomy-time-machine

## TODO

1. [x] Fuzzy text search by name
2. [x] Display children of a node
3. [x] API (maybe just use flask-smorest)
4. [ ] Deploy!
5. [x] Better handling when there are more than one match to a name (e.g.,
   `environmental samples`)
6. [x] Proper search / type-ahead box (can fix 5)
7. [ ] show when a node was deleted
8. [ ] allow searching for synonyms
9. [ ] url query string routing
10. [ ] server side rendering
11. [ ] Add buttons to load interesting example queries
12. [ ] add descriptions and explanatory text to the page

## Setup

```sh
# install python dependencies
uv venv --seed
. venv/bin/activate
uv pip install

# front-end
npm install

# fetch data, create events.db
make

# start the backend
python app.py

# start the frontend
npm run dev
```

## Data Structure

Instead of storing every version of the taxonomy table in its entirety, only
_differences_ between version `n` and `n+1` are stored for every version of the
taxonomy database loaded. This allows for massive (98.4%) space savings while
providing a data structure for which writing useful queries is still
straightforward.

The taxonomy table contains the following rows:

```sql
CREATE TABLE IF NOT EXISTS taxonomy (
    event_name TEXT,
    version_date DATETIME,
    tax_id INTEGER,
    parent_id INTEGER,
    rank TEXT,
    name TEXT
)
```

The columns `tax_id`, `parent_id`, `rank` and `name` work like a regular NCBI
tax dump (with `names.dmp` and `nodes.dmp`) being combined into a single table.
The two additional columns are used to store version information.

This taxonomy table is constructed by iterating over the NCBI taxonomy dumps in
chronological order from first to latest, comparing the taxonomic information
for a given `tax_id` to to the previous version (if it exists) and writing a
row to the `taxonomy` table _only if` there was a change.

Querying this data structure allows you to reconstruct a taxonomic lineage at
any point in time. Do to this, just query the table as you would normally
but filter on `version_date <= t` and get the first row:

```sql
SELECT * FROM taxonomy WHERE tax_id = 821 AND version_date <= t LIMIT 1
```

By repeating this query for each `tax_id` in the lineage, you can reconstruct
the lineage from node to root at any point in time. Doing this all as a single
recursive SQL query is left as an exercise for the reader.

To get all of the _children_ of a node at any point in time:

```sql
SELECT * FROM taxonomy WHERE parent_id = 821 AND version_date <= t
```
