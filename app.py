from flask import Flask, request, jsonify
from models import Taxonomy
from datetime import datetime


app = Flask(__name__)

# TODO: we can cut down on the number of DB queries by fetching the events
# first and then filtering them ...


@app.route("/search", methods=["GET"])
def search():
    """Return the most recent matching tax ID given a name"""
    db = Taxonomy()

    # these are just names
    matches = db.search_names(query=request.args.get("query"))

    if len(matches) == 0:
        return jsonify(None)
    else:
        best_match = matches[0]["name"]

        # find the most recent row
        # this is when the name was *created*, not deprecated aka "valid
        # until", which is a little confusing
        rows = db.cursor.execute(
            f"SELECT * from taxonomy where NAME = '{best_match}' order by version_date desc limit 1;"
        ).fetchall()

        if len(rows) == 0:
            return jsonify(None)
        else:
            return jsonify(dict(rows[0]))


@app.route("/events", methods=["GET"])
def events():
    db = Taxonomy()
    tax_id = request.args.get("tax_id")
    events = list(db.get_events(tax_id=tax_id))
    return jsonify(events)


@app.route("/children", methods=["GET"])
def children():
    db = Taxonomy()
    version = request.args.get("version")
    tax_id = int(request.args.get("tax_id"))

    if version:
        version = datetime.fromisoformat(version)

    children = list(db.get_children(tax_id=tax_id, as_of=version))

    return jsonify(children)


@app.route("/lineage", methods=["GET"])
def lineage():
    db = Taxonomy()
    version = request.args.get("version")
    tax_id = int(request.args.get("tax_id"))

    if version:
        version = datetime.fromisoformat(version)

    lineage = list(db.get_lineage(tax_id=tax_id, as_of=version))

    return jsonify(lineage)


@app.route("/versions", methods=["GET"])
def versions():
    db = Taxonomy()
    tax_id = request.args.get("tax_id")
    if tax_id:
        versions = [{"version_date": v.isoformat()} for v in db.get_versions(tax_id=tax_id)]
        return jsonify(versions)
    else:
        return jsonify([])


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
