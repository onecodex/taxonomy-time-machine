# taxonomy-time-machine

https://taxonomy.onecodex.com

A web application and database for quickly browsing and comparing different
versions of the NCBI taxonomy database.


> [!NOTE]
> **Archives Wanted!**
> Archives of the NCBI taxonomy database only go as far
back as 2014. However, we suspect that there are even older versions collecting
dust on old HPCs, laptops, CD-ROMs and other ancient storage media. If you
think you have an old copy of `taxdump.tar.gz`, even if you don't know where
it's from, please send it to us (open a ticket)! You may be holding a valuable
ancient artifact.

## Setup

```bash
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

## API Documentation

### `api/lineage`

Return the taxonomic lineage for a given tax ID at a specific time

Parameters:

- `tax_id` (`str`)
- `version_date` (`str`) - ISO8601-formatted datetime string. If provided, the
  children of `tax_id` at the specific time will be returned. Otherwise, the
  current children will be returned

Example:

```bash
curl 'https://taxonomy.onecodex.com/api/lineage?tax_id=821&version_date=2014-10-22T00%3A00%3A00' | jq 
[
  ...
  {
    "event_name": "create",
    "name": "cellular organisms",
    "parent_id": 1,
    "rank": "no rank",
    "tax_id": 131567,
    "version_date": "2010-10-22T00:00:00"
  },
]
```

### `/api/search`

Search all taxonomic events by a tax ID or partial name

Parameters:

- `query` (`str`): query (tax ID or name)

Example:

```bash
curl 'https://taxonomy.onecodex.com/api/search?query=bacteroides%20dorei%CAG' | jq 

[
  {
    "event_name": "create",
    "name": "Bacteroides dorei CAG:222",
    "parent_id": 139043,
    "rank": "species",
    "tax_id": 1263042,
    "version_date": "2014-08-01T00:00:00"
  }
]
```

### `api/events`

Return taxonomic events given a Tax ID

Parameters:

- `tax_id` (`str`): query (tax ID)

Example:

```bash
curl 'https://taxonomy.onecodex.com/api/events?tax_id=821' | jq 

[
  {
    "event_name": "create",
    "name": "Bacteroides vulgatus",
    "parent_id": 816,
    "rank": "species",
    "tax_id": 821,
    "version_date": "2010-10-22T00:00:00"
  },
  ...
]
```

### `api/children`

Return direct descendants for a given tax ID

Parameters:

- `tax_id` (`str`)
- `version_date` (`str`) - ISO8601-formatted datetime string. If provided, the
  children of `tax_id` at the specific time will be returned. Otherwise, the
  current children will be returned

Example:

```bash
curl 'https://taxonomy.onecodex.com/api/children?tax_id=1&version_date=2010-10-22T00%3A00%3A00' | jq 
[
  ...
  {
    "event_name": "create",
    "name": "Viroids",
    "parent_id": 1,
    "rank": "no rank",
    "tax_id": 12884,
    "version_date": "2010-10-22T00:00:00"
  },
]
```

