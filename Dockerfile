FROM python:3-alpine

MAINTAINER Daniel Quinn <code@danielquinn.org>

COPY requirements.txt /

# Add a user to our container, using the uid/gid of the host user
RUN addgroup -S app -g 1000 \
  && adduser -S app -u 1000 -s /bin/sh -G app

RUN apk add --no-cache --update build-base mariadb-dev \
  && pip install --upgrade pip \
  && pip install --requirement /requirements.txt \
  && apk del build-base \
  && rm /var/cache/apk/*

EXPOSE 8000

ENTRYPOINT /app/scripts/entrypoint
