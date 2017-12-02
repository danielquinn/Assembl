from sqlalchemy import Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import PrimaryKeyConstraint

Base = declarative_base()


db_credentials = "mysql://anonymous@ensembldb.ensembl.org/ensembl_website_90"


class Gene(Base):

    __tablename__ = "gene_autocomplete"
    __table_args__ = (PrimaryKeyConstraint("species", "display_label"),)

    species = Column(String(255))
    display_label = Column(String(128))

    def __str__(self):
        return "{}.{}".format(self.species, self.display_label)
