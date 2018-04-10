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
    project = db.Column(db.String)
    private = db.Column(db.Boolean, default=False)
    usable = db.Column(db.Boolean, default=False)

    def __init__(self, name, ip, in_use, project, private=False, usable=False):
        self.name = name
        self.ip = ip
        self.in_use = in_use
        self.project = project
        self.private = private
        self.usable = usable
        self.required_keys = ["name", "ip", "project", "in_use"]
        self.immutable_keys = ["name", "project"]

    def __repr__(self):
        return '<id {0}, name {1}, ip {2}, in_use {3}, project {4}, private {5}, usable {6}>'.format(self.id, self.name, self.ip, self.in_use, self.project, self.private, self.usable)

    def map(self):
        return {"name": self.name,
                "ip": self.ip,
                "project": self.project,
                "in_use": self.in_use,
                "private": self.private,
                "usable": self.usable}

    def get_required_keys(self):
        return self.required_keys


#TODO: allow user to register more projects?
# class Project(BaseModel):
#     """Model for projects table"""
#     __tablename__ = 'projects'
#
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String)
#     secret = db.Column()
#
#     def __init__(self, name, secret=None):
#         self.name = name
#         self.secret = secret
