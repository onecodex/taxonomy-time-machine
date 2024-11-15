# taxonomy-time-machine

## TODO

1. [x] Fuzzy text search by name
2. [x] Display children of a node
3. [x] API (maybe just use flask-smorest)
4. [ ] Deploy!
5. [ ] Better handling when there are more than one match to a name (e.g.,
   `environmental samples`)
6. [ ] Proper search / type-ahead box (can fix 5)

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
