import os

from flask import Flask
from werkzeug.contrib.fixers import ProxyFix

from .views import AutocompleteView


def setup():
    """
    This is a little more complicated than your usual Flask app because we're
    doing something a little unorthodox: in the even that we've toggled
    AGGRESSIVE_CACHING, we dump a bunch of data onto the view class (not the
    instance).  This is purely for performance, since we don't want to load &
    unload all of this for every request and the data is basically static.
    """

    app = Flask(__name__)

    # Aggressive caching toggle

    kwargs = {}
    aggressive_caching = os.getenv("AGGRESSIVE_CACHING")
    if aggressive_caching:
        with app.app_context():
            AutocompleteView.populate_cache()
        kwargs["aggressive_caching_enabled"] = True

    # URLs

    app.add_url_rule(
        "/gene_suggest/",
        view_func=AutocompleteView.as_view("gene-suggest", **kwargs)
    )

    # WSGI hack

    app.wsgi_app = ProxyFix(app.wsgi_app)

    return app


application = setup()
if __name__ == "__main__":
    application.run(debug=True)
