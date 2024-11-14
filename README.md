# taxonomy-time-machine

## TODO

1. [ ] Fuzzy text search by name
2. [x] Display children of a node
3. [ ] Fix bug where we sometimes find irrelevant events in the history because
   two events cancel each other out
   - easy fix: just deduplicate the history table
4. [ ] API (maybe just use flask-smorest)

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
