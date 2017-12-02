import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def get_db():
    """
    A quick & dirty way to setup a database connection.  I tried out
    Flask-SQLAlchemy, but it proved to be too convoluted, circular, and rigid
    in is execution.  This did the job.

    :return: A SQLAlchemy database session.
    """

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise EnvironmentError(
            "DATABASE_URL must be defined for Assembl to function."
        )

    engine = create_engine(database_url, encoding="latin1")
    declarative_base().metadata.bind = engine

    return sessionmaker(bind=engine)()


db = get_db()
