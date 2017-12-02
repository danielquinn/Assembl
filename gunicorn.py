#
# A quick & dirty Gunicorn setup script.  Basically this will let you set any
# Gunicorn config by setting an environment variable.  For example this will
# configure Gunicorn to run 16 worker processes:
#
#   GUNICORN_WORKERS=16
#
# ...the equivalent to hard-coding ``workers=16`` in this file.
#


import os

for k, v in os.environ.items():
    if k.startswith("GUNICORN_"):
        key = k.split("_", 1)[1].lower()
        locals()[key] = v
