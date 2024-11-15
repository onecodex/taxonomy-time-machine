# taxonomy-time-machine

## TODO

1. [x] Fuzzy text search by name
2. [x] Display children of a node
3. [ ] Fix bug where we sometimes find irrelevant events in the history because
   two events cancel each other out
   - easy fix: just deduplicate the history table
4. [x] API (maybe just use flask-smorest)
5. [ ] Deploy!
6. [ ] Better handling when there are more than one match to a name (e.g.,
   `environmental samples`)
7. [ ] Instead of showing a list of version dates, allow the user to select the
   date (maybe with a neat timeline UI element). This would also help with some
   bugs where we only show the versions where a node's lineage changed (and not
   the ones where its children changes7. [ ] Instead of showing a list of
   version dates, allow the user to select the date (maybe with a neat timeline
   UI element). This would also help with some bugs where we only show the
   versions where a node's lineage changed (and not the ones where its children
   changed)

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
