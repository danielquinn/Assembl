import json
import os
import re

from collections import defaultdict

from flask import request
from flask.views import MethodView

from .models import Gene


class AutocompleteView(MethodView):

    #
    # You can change these constants by setting them in environment variables,
    # just note that we're not doing any complex checking here for types, so
    # if you set LABEL_MINIMUM to "seven" you're doing it wrong ;-)
    #

    CACHE = defaultdict(list)
    LABEL_MINIMUM = int(os.getenv("LABEL_MINIMUM", 3))
    DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", 5))
    MAXIMUM_LIMIT = int(os.getenv("MAXIMUM_LIMIT", 25))

    def __init__(self, aggressive_caching_enabled=False):

        MethodView.__init__(self)

        self.aggressive_caching_enabled = aggressive_caching_enabled

    # Public methods

    def get(self):

        species = self._get_species()
        query = self._get_query()
        limit = self._get_limit()

        # I had considered returning a 400 here with an error message, but I
        # figured that since this is the sort of thing typically used in a
        # Javascript autocomplete box, an error message is just less useful
        # than an empty list.

        if len(query) < self.LABEL_MINIMUM or not species:
            return self._render([])

        if self.aggressive_caching_enabled:
            return self._render(self._get_from_cache(species, query, limit))

        return self._render(self._get_from_db(species, query, limit))

    # Class methods

    @classmethod
    def populate_cache(cls):
        """
        Grab the lookup data from a local json file and dump it into memory for
        quick turn-around.  This cache file is created at server start-time.
        See ``gunicorn.py`` for details.
        """

        with open("/tmp/db.json") as f:
            cls.CACHE = json.load(f)

    # Private methods

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

    def _get_from_db(self, species, query, limit):
        """
        The (much) slower, but always up-to-date option.  This initiates a
        connection to the db server, performs the query, and returns a list of
        suggestions.
        :param species:  str  A species like ``homo_sapiens``
        :param query:  str  A partial label, like ``BRC``
        :param limit:  int  The maximum number of results to return
        :return:  list  A list of complete labels.
        """

        suggestions = Gene.objects.query(Gene)\
            .filter(Gene.species == species)\
            .filter(Gene.display_label.contains(query))\
            .limit(limit)\
            .values("display_label")

        return [self._cleanup_label(s[0]) for s in suggestions]

    def _get_from_cache(self, species, query, limit):
        try:
            return [self._cleanup_label(l) for l in self.CACHE[species] if query in l][:limit]  # NOQA: E501
        except KeyError:
            return []

    def _get_query(self):
        return self._sanitise_input("query")

    def _get_limit(self):
        """
        Make sure we get a number > 0 and < MAXIMUM_LIMIT.  If not, we return
        the default.
        """

        try:
            return min(int(request.args.get("limit", "")), self.MAXIMUM_LIMIT)
        except ValueError:
            return self.DEFAULT_LIMIT

    def _get_species(self):
        return self._sanitise_input("species")

    def _sanitise_input(self, name):
        """
        Sanitise a parameter for unexpected characters. Stuff like ``%`` will
        just gum things up, and there's really no legit reason for these
        anyway.
        """
        return re.sub(r"[^\w]", "", request.args.get(name, ""))

    def _cleanup_label(self, label):
        """
        One annoying part of this assignment is that I have no control over the
        nature of the data.  If I did, I'd fix it first so that all of the
        ``display_label`` fields followed a uniform case style.  Interestingly,
        and typical of MySQL, a ``LIKE`` query is case insensitive, so the
        query itself can be simpler, but we still have to modify the output for
        uniformity, which seems rather silly.
        """
        bits = label.split(" ", 1)
        bits[0] = bits[0].upper()
        return " ".join(bits)
