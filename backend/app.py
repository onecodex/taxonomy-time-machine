from taxonomy_time_machine.models import Taxonomy
from datetime import datetime

import os
import random
from flask import Flask, g
from flask.views import MethodView
import marshmallow as ma
from flask_smorest import Api, Blueprint
from flask_cors import CORS

app = Flask(__name__)

# Configure CORS for development and production
if os.environ.get("FLASK_DEBUG"):
    # In development, allow frontend dev server
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
else:
    # In production, allow the production domain
    CORS(app, origins=["https://taxonomy.onecodex.com"])
app.config["API_TITLE"] = "Taxonomy Time Machine"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.2"
app.config["OPENAPI_URL_PREFIX"] = "/"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["OPENAPI_REDOC_PATH"] = "/redoc"
app.config["OPENAPI_REDOC_URL"] = (
    "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
)

if not os.environ.get("FLASK_DEBUG"):
    app.config["API_SPEC_OPTIONS"] = {
        "servers": [
            {"url": "https://taxonomy.onecodex.com/api", "description": "Production server"}
        ]
    }

api = Api(app)

# TODO: we can cut down on the number of DB queries by fetching the events
# first and then filtering them ...

blp = Blueprint("taxonomy", "taxonomy", url_prefix="/", description="Taxonomy Time Machine API")

DATABASE_PATH = os.environ.get("DATABASE_PATH", "events.db")


def get_taxonomy():
    if not hasattr(g, "taxonomy"):
        g.taxonomy = Taxonomy(database_path=DATABASE_PATH)
    return g.taxonomy


class QueryArgsSchema(ma.Schema):
    query = ma.fields.String(
        metadata={"description": "Search term (taxon name or ID)", "example": "Bacteroides dorei"}
    )


class TaxIdQuerySchema(ma.Schema):
    tax_id = ma.fields.Integer(metadata={"description": "NCBI Taxonomy ID", "example": 9606})


class ChildrenQuerySchema(ma.Schema):
    tax_id = ma.fields.String(metadata={"description": "NCBI Taxonomy ID", "example": "9606"})
    version_date = ma.fields.NaiveDateTime(
        required=False,
        allow_none=True,
        metadata={
            "description": "ISO8601-formatted datetime (e.g. 2014-08-01T00:00:00)",
            "example": "2014-08-01T00:00:00",
        },
    )

    @ma.pre_load
    def coerce_empty_to_none(self, data, **kwargs):
        data = data.copy()
        for key, value in data.items():
            if value == "":
                data[key] = None
        return data


class TaxonSchema(ma.Schema):
    event_name = ma.fields.String(
        metadata={"description": "Type of taxonomic event", "example": "create"}
    )
    name = ma.fields.String(metadata={"description": "Scientific name", "example": "Homo sapiens"})
    rank = ma.fields.String(metadata={"description": "Taxonomic rank", "example": "species"})
    tax_id = ma.fields.String(metadata={"description": "NCBI Taxonomy ID", "example": "9606"})
    parent_id = ma.fields.String(
        allow_none=True, metadata={"description": "Parent taxon ID", "example": "9605"}
    )
    version_date = ma.fields.NaiveDateTime(
        metadata={"description": "ISO8601-formatted datetime", "example": "2014-08-01T00:00:00"}
    )


class VersionSchema(ma.Schema):
    version_date = ma.fields.NaiveDateTime()


class RandomSpeciesResponseSchema(ma.Schema):
    tax_id = ma.fields.String(metadata={"description": "NCBI Taxonomy ID", "example": "9606"})
    name = ma.fields.String(metadata={"description": "Scientific name", "example": "Homo sapiens"})
    event_count = ma.fields.Integer(
        metadata={"description": "Number of taxonomic events", "example": 5}
    )


@blp.route("/search")
class Search(MethodView):
    @blp.arguments(QueryArgsSchema, location="query")
    @blp.response(200, TaxonSchema(many=True))
    def get(self, args):
        """Return the most recent matching tax ID given a name"""
        db = get_taxonomy()

        # fetch a list of matching names
        matches = db.search_names(query=args["query"], limit=10)

        return matches


@blp.route("/events")
class Events(MethodView):
    @blp.arguments(TaxIdQuerySchema, location="query")
    @blp.response(200, TaxonSchema(many=True))
    def get(self, args):
        """Return all taxonomic events for a given tax ID"""
        db = get_taxonomy()
        tax_id = args["tax_id"]
        return db.get_events(tax_id=tax_id)


@blp.route("/children")
class Children(MethodView):
    @blp.arguments(ChildrenQuerySchema, location="query")
    @blp.response(200, TaxonSchema(many=True))
    def get(self, args):
        """Return direct descendants for a given tax ID at a specific time"""
        db = get_taxonomy()
        version = args.get("version_date")
        tax_id = args["tax_id"]

        return db.get_children(tax_id=tax_id, as_of=version)


@blp.route("/lineage")
class Lineage(MethodView):
    # TODO: more generic name for schema
    @blp.arguments(ChildrenQuerySchema, location="query")
    @blp.response(200, TaxonSchema(many=True))
    def get(self, args):
        """Return the complete taxonomic lineage for a given tax ID at a specific time"""
        db = get_taxonomy()
        tax_id = args["tax_id"]
        version = args.get("version_date")

        return db.get_lineage(tax_id=tax_id, as_of=version)[::-1]


@blp.route("/versions")
class Versions(MethodView):
    @blp.arguments(ChildrenQuerySchema, location="query")
    @blp.response(200, VersionSchema(many=True))
    def get(self, args):
        """Return all available database versions where the given tax ID appears"""
        db = Taxonomy(database_path=DATABASE_PATH)
        tax_id = args.get("tax_id")
        versions = db.get_versions(tax_id=tax_id)
        if tax_id:
            resp = [{"version_date": v} for v in versions]
            return resp
        else:
            return []


@blp.route("/random-species")
class RandomSpecies(MethodView):
    @blp.response(200, RandomSpeciesResponseSchema)
    def get(self):
        """Return a random species with taxonomic history"""
        db = get_taxonomy()
        cursor = db.cursor

        # Fast random selection using OFFSET with cached count
        # Use hardcoded count for speed (approximately 874,797 as of last check)
        # This doesn't need to be perfectly accurate for random selection
        total_count = 870_000
        random_offset = random.randint(0, total_count - 1)

        # Get random species using OFFSET
        cursor.execute(
            """
            SELECT tax_id, name
            FROM taxonomy
            WHERE rank = 'species'
            LIMIT 1 OFFSET ?
        """,
            (random_offset,),
        )

        result = cursor.fetchone()

        # Get event count for the selected species
        cursor.execute(
            """
            SELECT COUNT(*) as event_count
            FROM taxonomy
            WHERE tax_id = ?
        """,
            (result["tax_id"],),
        )

        count_result = cursor.fetchone()
        return {
            "tax_id": result["tax_id"],
            "name": result["name"],
            "event_count": count_result["event_count"] if count_result else 1,
        }


api.register_blueprint(blp)


def main():
    app.run(host="0.0.0.0", port=9606)


if __name__ == "__main__":
    main()
