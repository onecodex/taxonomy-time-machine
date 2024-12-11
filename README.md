# taxonomy-time-machine

https://taxonomy.onecodex.com

A web application and database for quickly browsing and comparing different
versions of the NCBI taxonomy database.


> [!NOTE]
> Archives of the NCBI taxonomy database only go as far
back as 2014. However, we suspect that there are even older versions collecting
dust on old HPCs, laptops, CD-ROMs and other ancient storage media. If you
think you have an old copy of `taxdump.tar.gz`, even if you don't know where
it's from, please send it to us so that we can add it to the archive!

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
