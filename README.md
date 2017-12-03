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


## Deployment

This is such a broad subject and it depends on too many variables to supply
anything resembling a good answer, but I'll take a crack at it by sorting the
recommendations from simple to elaborate.

### 1. Simple Setup: Nginx + Docker + Gunicorn, no caching

Maybe your dataserver is super-powerful and you're not concerned at all about
reducing requests to it, and maybe you'd be hosting this code in the same
data centre as that database so the turn-around time on database requests would
be minimal.  In this case, it's perfectly reasonable to have code like this
setup without caching, though I wouldn't recommend it.

Basically you'd start this up in the Docker container provided and call it a
day.  Though honestly, if you're going to spin up an entirely separate web
service to do a job as simple as this, you're basically making work for
yourself.  If this was your setup, I'd advise you not to use this project at
all, but to build a REST application into your broader web app.  This way you
could take advantage of things like a reusable ORM, shared code across the rest
of the app etc.

### 2. Let's Use Some Caching: Nginx + Docker + Gunicorn with caching

Assuming turn-around on this sort of thing is critical, you'll want to be
handling all of the requests via a local cache and *not* hitting a database
with 2million rows in it.  This code will adapt nicely: just setup a server
somewhere (preferably near your data server) and configure Nginx to sit in
front of the docker container running Gunicorn just like option #1.  The
biggest difference here is that you'd set `AGGRESSIVE_CACHING=1` and Assembl
bear the brunt of your web traffic.  You'd also probably want to build some
sort of trigger system to re-start the server whenever there's a change to
these values.

### 3. Smarter Caching: Nginx + Docker + Gunicorn + Cached JSON

The start-up process is **slow** when you enable `AGGRESSIVE_CACHING` and it
introduces an ugly wait while Assembl queries the database for about 17MB of
data.  Additionally, your local cache can get stale, necessitating restarts,
which is messy and brings back that wait time.

A better option would be to setup a webserver that hosts an xz-compressed JSON
blob like the one ``gunicorn.py`` creates at start time.  Then we'd tweak
Assembl to grab this file at start up and forego the database altogether.  The
file would be generated whenever necessary and the Assembl service could be
restarted as soon as the new file was uploaded.

Some fun stats about this option:

* Total amount of data to be cached (JSON): 17MB
* Total size of xz-compressed data: 1MB
* Time to decompress the file: sub-second

### 4. Even Better Caching: Nginx + Docker + Gunicorn + Redis

The thing is, if this data changes more than I assume it does, then option #3
creates a lot more server restarts and traffic than we want.  In this case, we
probably want to look at something with a few more moving parts, like a proper
caching server.

You could setup Redis to store a whole bunch of key/value pairs in the format:

```python
species: [label, label, label]
```

Assembl would then drop this whole "cache all the things" in memory mentality
and instead just reference the redis store, looking up by `species` and
filtering the value list locally.  The cache would be updated atomically, so
all Assembl instances would have the latest data and would never require a
restart.

### 5. Do All The Things: Nginx + Docker + Gunicorn + caching + HA + Geographic Distribution

Say that for some reason, this autocomplete thingy is **super** important and
its performance is paramount.  We can go all the way on this too:

* Nginx/Docker/Gunicorn instaces setup all over the world
* Each node consists of no fewer than 3 instances of Assembl and 2 clustered
  Redis stores
* You load-balance both sets in each node, and push out updates to the caches
  from a central service
* Setup Cloudflare (or a similar system) in front of it all.

I mean, you *could* go this far, but I wouldn't.  Not for this.


## Tests

We're using the typical [pytest](https://docs.pytest.org/en/latest/) and [flake8](http://flake8.pycqa.org/en/latest/)
inside [tox](https://tox.readthedocs.io/en/latest/), so hopefully you're
familiar with this setup.  To run all the tests, just do the following whilst
in the project root:

```bash
$ tox
```
