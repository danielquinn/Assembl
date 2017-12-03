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

## Configuration

Assembl follows the [12factor](https://12factor.net/) methodology, so it's
configured by way of environment variables.  The only variable that *must* be
defined is `DATABASE_URL`, but we have a few others as well:

Additional variables can be defined in the environment, but `DATABASE_URL` is
the only one that's required:

Variable Name | Required | Description | Default Value
------------- | -------- | ----------- | -------------
DATABASE_URL  | yes | Defines the connection info for your database.  It should be in the following format: `mysql://<user>@<host>/<db-name>` | `None`
LABEL_MINIMUM | no | The minimum number of characters to which the server will attempt to look up.  Fewer characters than this will just return an empty list. | `3`
DEFAULT_LIMIT | no | The limit of results returned if no `limit=` value was specified. | `5`
MAXIMUM_LIMIT | no | The highest value we will permit for a user-specified `limit=` value. | `25`

In production, you can also configure the Gunicorn server by setting
environment variables prefixed with `GUNICORN_`.  See the comments in
`gunicorn.py` for more information.

## Run this Thing

### Development

If you want to run it locally, you can just use the Flask development server.
Assuming that you're declaring your environment variables on the command line,
here's what that would look like:

```bash
$ DATABASE_URL="mysql://<user>@<host>/<db-name>" FLASK_APP="src/app.py" flask run
```

### Production

For a production setup though, there's a handy Docker container to do the job.
Just build the container and `run` it, passing in whatever variables you like:

```bash
$ docker build -it danielquinn/assembl
$ docker run --rm -p 8000:8000 \
  -e GUNICORN_WORKERS=16 \
  -e DATABASE_URL="mysql://<user>@<host>/<db-name>" \
  --name assembl \
  --detach \
  danielquinn/assembl
```

The container will start and invoke Assembl with Gunicorn running 16 workers,
connecting to the database with your credentials.  It will be bound on port
`8000`, so you'll want to tweak Nginx to point there.

## Scaling

One of the questions in the spec was about scaling, so I chose to go with the
nuclear option: *Cache All The Things* locally and read directly from memory.
Check out the docstring for more information:

> What is this madness?  Dump the entire database into a JSON file?  Are you
> high?
>
> Bear with me on this one.
>
> The data in question leans heavily in the direction of "write once, read
> often".  With this in mind, building a hard cross-internet turn-around time
> into each call makes little sense.  Indeed as this data is likely to change
> rarely, referencing a local copy is only sensible.
>
> What we're doing here is pulling down only the data we need for the
> suggestions API and storing it in a cache file which is then sourced by
> each worker at server start time.  To refresh the data, you need only
> restart the server, which triggers a re-fetching of the data and
> re-populating of the view-level caches.
>
> There are more complex alternatives to this model, including simple options
> like a local Sqlite db, a Redis cache, or more complex cross-continental,
> "eventually consistent" MySQL clustering, but for data that rarely if ever
> changes, this makes the most sense to me.
>
> The nice thing about this system is that you can spin up multiple copies
> of it all over the world, maybe even run it on a service like AWS Lambda,
> since the local storage is transitory.  Any way you cut it, you never have
> a bottleneck on your data server and the turn-around is stupid fast.

To enable this, you just need to set `AGGRESSIVE_CACHING=1` in the environment,
so the above docker command would look like this:

```
$ docker run --rm -p 8000:8000 \
  -e GUNICORN_WORKERS=16 \
  -e DATABASE_URL="mysql://<user>@<host>/<db-name>" \
  -e AGGRESSIVE_CACHING=1 \
  --name assembl \
  --detach
  danielquinn/assembl
```

This isn't supported in the development environment (using `flask run`) because
the caching code is run by the Gunicorn launcher.

For details on how this is being done, have a look at `gunicorn.py` and
`src/views.py::AutocompleteView::populate_cache`.

## Tests

We're using the typical [pytest](https://docs.pytest.org/en/latest/) and [flake8](http://flake8.pycqa.org/en/latest/)
inside [tox](https://tox.readthedocs.io/en/latest/), so hopefully you're
familiar with this setup.  To run all the tests, just do the following whilst
in the project root:

```bash
$ tox
```
