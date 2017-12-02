# Assembl

This is a simple Flask REST server to make an autocomplete tool based on the
public Ensembl MySQL server.

## Installation

Clone this Repo:

```bash
$ git clone https://github.com/danielquinn/Assembl
```

Install the required dependencies with pip:

```bash
$ pip install -r requirements.txt
```

## Run this Thing

Assembl follows the [12factor](https://12factor.net/) methodology, so it's
configured by way of environment variables.  These can be set in the
environment any way you please, but for the sake of simplicity, we'll do it on
the command line.

```bash
$ DATABASE_URL="mysql://<user>@<host>/<db-name>" FLASK_APP="src/app.py" flask run
```

Additional variables can be defined in the environment, but `DATABASE_URL` is
the only one that's required:

Variable Name | Description | Default Value
------------- | ----------- | -------------
LABEL_MINIMUM | The minimum number of characters to which the server will attempt to look up.  Fewer characters than this will just return an empty list. | 3
DEFAULT_LIMIT | The limit of results returned if no `limit=` value was specified. | 5
MAXIMUM_LIMIT | The highest value we will permit for a user-specified `limit=` value. | 25
