import json
import os
import re

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from flask import Flask, request
from flask.views import MethodView
from werkzeug.contrib.fixers import ProxyFix

from .models import Gene


class AutocompleteView(MethodView):

    #
    # You can change these constants by setting them in environment variables,
    # just note that we're not doing any complex checking here for types, so
    # if you set LABEL_MINIMUM to "seven" you're doing it wrong ;-)
    #

    LABEL_MINIMUM = int(os.getenv("LABEL_MINIMUM", 3))
    DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", 5))
    MAXIMUM_LIMIT = int(os.getenv("MAXIMUM_LIMIT", 25))

    def __init__(self):
        """
        I hate the way Flask puts stuff into the package scope by default. It's
        so cluttered and messy.  I much prefer the Django-style system where
        database interactions are managed by way of a manager on each model, so
        given that we're using Flask today, I thought it best to at least
        bundle these bits in here rather than leaving them flapping about out
        there.

        Of course, I can do this because there's only one view in this project.
        If this were a Proper Thing, I'd probably break these bits out into a
        singleton that can be imported where it's needed.

        Configuration is managed by way of a single environment variable,
        ``DATABASE_URL`` which follows the common format outlined here:
        http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
        """

        MethodView.__init__(self)

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise EnvironmentError(
                "DATABASE_URL must be defined for Assembl to function."
            )

        engine = create_engine(database_url, encoding="latin1")
        declarative_base().metadata.bind = engine

        self.session = sessionmaker(bind=engine)()

    def get(self):
        """
        One annoying part of this assignment is that I have no control over the
        nature of the data.  If I did, I'd fix it first so that all of the
        ``display_label`` fields were in the same case.  Interestingly, and
        so typical of MySQL, a ``LIKE`` query appears to be case insensitive,
        so the query itself can be simpler, but we still have to modify the
        output to conform which seems rather silly.
        """

        species = self._get_species()
        limit = self._get_limit()
        label = self._get_label()

        # I had considered returning a 400 here with an error message, but I
        # figured that since this the sort of thing typically used in a
        # Javascript autocomplete box, an error message is just less useful
        # than an empty list.

        if len(label) < self.LABEL_MINIMUM or not species:
            return self._render([])

        suggestions = self.session.query(Gene)\
            .filter(Gene.species == species)\
            .filter(Gene.display_label.contains(label))\
            .limit(limit)\
            .values("display_label")

        return self._render([s[0].upper() for s in suggestions])

    def _render(self, data, status=200):
        """
        A nice uniform place to handle what we send back to the user.
        :param data: A python object that can be serialised with JSON
        :param status: A numeric HTTP status code
        :return: A tuple consisting of a JSON-serialised string, the status
                 code, and the headers required for a JSON server.  Everything
                 you need for a proper Flask response.
        """
        return (
            json.dumps(data, separators=(",", ":")),
            status,
            {"Content-Type": "application/json"}
        )

    def _get_label(self):
        return self._sanitise("query")

    def _get_limit(self):
        try:
            return min(int(request.args.get("limit", "")), self.MAXIMUM_LIMIT)
        except ValueError:
            return self.DEFAULT_LIMIT

    def _get_species(self):
        return self._sanitise("species")

    def _sanitise(self, name):
        """
        Sanitise a parameter for non alphanumerics.  Stuff like ``%`` will just
        gum things up, and there's really no legit reason for non-ascii's
        anyway.
        """
        return re.sub(r"[^\w]", "", request.args.get(name, ""))


app = Flask(__name__)
app.add_url_rule(
    "/gene_suggest/", view_func=AutocompleteView.as_view("gene-suggest"))

app.wsgi_app = ProxyFix(app.wsgi_app)

if __name__ == "__main__":
    app.run(debug=True)
