# taxonomy-time-machine

https://taxonomy.onecodex.com

A web application and database for quickly browsing and comparing different
versions of the NCBI taxonomy database.

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
