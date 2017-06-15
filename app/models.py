from app import db
from sqlalchemy.dialects.postgresql import JSON

class BaseModel(db.Model):
    __abstract__ = True

class Allocations(BaseModel):
    """Model for allocations table"""
    __tablename__ = 'allocations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    ip = db.Column(db.String)
    free = db.Column(db.Boolean)

    # def __init__(self, url):
    #     self.url = url
    #     self.name = ""
    #     self.ip = ""
    #     self.alloc = False
    #
    # def __repr__(self):
    #     return '<id {}>'.format(self.id)