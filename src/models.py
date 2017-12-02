from sqlalchemy import Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import PrimaryKeyConstraint

from .database import db

Base = declarative_base()


class Gene(Base):

    __tablename__ = "gene_autocomplete"
    __table_args__ = (PrimaryKeyConstraint("species", "display_label"),)

    species = Column(String(255))
    display_label = Column(String(128))

    objects = db  # Look, it's like Django, but less elegant!

    def __str__(self):
        return "{}.{}".format(self.species, self.display_label)
