from models import Taxonomy, coerce_row
from datetime import datetime

from flask import Flask
from flask.views import MethodView
import marshmallow as ma
from flask_smorest import Api, Blueprint

app = Flask(__name__)
app.config["API_TITLE"] = "Taxonomy Time Machine"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.2"
app.config["OPENAPI_URL_PREFIX"] = "/"
api = Api(app)

# TODO: we can cut down on the number of DB queries by fetching the events
# first and then filtering them ...

blp = Blueprint("taxonomy", "taxonomy", url_prefix="/", description="Taxonomy Time Machine API")


class QueryArgsSchema(ma.Schema):
    query = ma.fields.String()


class TaxIdQuerySchema(ma.Schema):
    tax_id = ma.fields.Integer()


class ChildrenQuerySchema(ma.Schema):
    tax_id = ma.fields.Integer()
    version_date = ma.fields.NaiveDateTime(required=False, allow_none=True)

    @ma.pre_load
    def coerce_empty_to_none(self, data, **kwargs):
        data = data.copy()
        for key, value in data.items():
            if value == "":
                data[key] = None
        return data


class TaxonSchema(ma.Schema):
    event_name = ma.fields.String()
    name = ma.fields.String()
    rank = ma.fields.String()
    tax_id = ma.fields.Integer()
    parent_id = ma.fields.Integer(allow_none=True)
    version_date = ma.fields.NaiveDateTime()


class VersionSchema(ma.Schema):
    version_date = ma.fields.NaiveDateTime()


@blp.route("/search")
class Search(MethodView):
    @blp.arguments(QueryArgsSchema, location="query")
    @blp.response(200, TaxonSchema(many=True))
    def get(self, args):
        """Return the most recent matching tax ID given a name"""
        db = Taxonomy()

        # fetch a list of matching names
        matches = db.search_names(query=args["query"], limit=10)

        return matches


@blp.route("/events")
class Events(MethodView):
    @blp.arguments(TaxIdQuerySchema, location="query")
    @blp.response(200, TaxonSchema(many=True))
    def get(self, args):
        db = Taxonomy()
        tax_id = args["tax_id"]
        return db.get_events(tax_id=tax_id)


@blp.route("/children")
class Children(MethodView):
    @blp.arguments(ChildrenQuerySchema, location="query")
    @blp.response(200, TaxonSchema(many=True))
    def get(self, args):
        db = Taxonomy()
        version = args.get("version_date")
        tax_id = args["tax_id"]

        return db.get_children(tax_id=tax_id, as_of=version)


@blp.route("/lineage")
class Lineage(MethodView):
    # TODO: more generic name for schema
    @blp.arguments(ChildrenQuerySchema, location="query")
    @blp.response(200, TaxonSchema(many=True))
    def get(self, args):
        db = Taxonomy()
        tax_id = args["tax_id"]
        version = args.get("version_date")

        return db.get_lineage(tax_id=tax_id, as_of=version)[::-1]


VERSION_DATES = [
    datetime(2010, 12, 31),
    datetime(2014, 12, 31),
    datetime(2015, 12, 31),
    datetime(2016, 12, 31),
    datetime(2017, 12, 31),
    datetime(2018, 12, 31),
    datetime(2019, 12, 31),
    datetime(2020, 12, 31),
    datetime(2021, 12, 31),
    datetime(2022, 12, 31),
    datetime(2023, 12, 31),
    datetime(2024, 12, 31),
]


@blp.route("/versions")
class Versions(MethodView):
    @blp.arguments(ChildrenQuerySchema, location="query")
    @blp.response(200, VersionSchema(many=True))
    def get(self, args):
        db = Taxonomy()
        tax_id = args.get("tax_id")
        versions = db.get_versions(tax_id=tax_id)
        if tax_id:
            resp = [{"version_date": v} for v in versions]
            return resp
        else:
            return []


api.register_blueprint(blp)


def main():
    app.run(host="0.0.0.0")


if __name__ == "__main__":
    main()
