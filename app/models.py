from flask.ext.sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()


class BaseModel(db.Model):
    __abstract__ = True

class Resource(BaseModel):
    """Model for resources table"""
    __tablename__ = 'resources'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    ip = db.Column(db.String)
    in_use = db.Column(db.Boolean)

    def __init__(self, name, ip, in_use):
        self.name = name
        self.ip = ip
        self.in_use = in_use

    def __repr__(self):
        return '<id {0}, name {1}, ip {2}, in_use {3}>'.format(self.id, self.name, self.ip, self.in_use)

    def map(self):
        return {"name": self.name,
                "ip": self.ip,
                "in_use": self.in_use}

