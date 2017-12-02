#
# A Gunicorn setup script with a twist.  Basically this will let you set any
# Gunicorn config by setting an environment variable.  For example this will
# configure Gunicorn to run 16 worker processes:
#
#   GUNICORN_WORKERS=16
#
# ...the equivalent to hard-coding ``workers = 16`` in this file.
#
# Additionally, we've got some heavy caching work being done in on_starting(),
# which will only run if AGGRESSIVE_CACHING is set.
#

import json
import logging
import os
import sys

from collections import defaultdict

# Hack the Python path so we can access the Gene model
sys.path.append(os.path.dirname(__file__))

from src.models import Gene


# Set configuration values based on the environment

for k, v in os.environ.items():
    if k.startswith("GUNICORN_"):
        key = k.split("_", 1)[1].lower()
        locals()[key] = v


def on_starting(server):
    """
    What is this madness?  Dump the entire database into a JSON file?  Are you
    high?

    Bear with me on this one.

    The data in question leans heavily in the direction of "write once, read
    often".  With this in mind, building a hard cross-internet turn-around time
    into each call makes little sense.  Indeed as this data is likely to change
    rarely, keeping a local copy only makes sense.

    What we're doing here is pulling down only the data we need for the
    suggestions API and storing it in a cache file which is then sourced by
    each worker at server start time.  To refresh the data, you need only
    restart the server, which triggers a re-fetching of the data and
    re-populating of the view-level caches.

    There are more complex alternatives to this model, including simple options
    like a local Sqlite db, or more complex cross-continental, "eventually
    consistent" MySQL clustering, but for data that rarely if ever changes,
    this makes the most sense to me.

    This nice thing about this system is that you can spin up multiple copies
    of it all over the world, maybe even run it on a service like AWS Lambda,
    since the local storage is transitory.  Any way you cut it, you never have
    a bottleneck on your data server and the turn-around is stupid fast.
    """

    if not os.getenv("AGGRESSIVE_CACHING"):
        return

    logger = logging.getLogger(__name__)

    logger.warning("Populating cache. You may want to go get a coffee")

    records = Gene.objects.query(Gene)\
        .order_by(Gene.species, Gene.display_label)

    db = defaultdict(list)
    for record in records:
        db[record.species].append(record.display_label)

    with open("/tmp/db.json", "w") as f:
        json.dump(db, f)

    logger.info("Cache is stocked. Completing start-up.")
