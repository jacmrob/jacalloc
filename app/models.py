from flask.ext.sqlalchemy import SQLAlchemy
import json
from datetime import datetime, timedelta
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
    timestamp = db.Column(db.DateTime, default=None)

    def __init__(self, name, ip, in_use, project, private=False, usable=False):
        self.name = name
        self.ip = ip
        self.in_use = in_use
        self.project = project
        self.private = private
        self.usable = usable
        self.timestamp = None

    def __repr__(self):
        return '<id {0}, name {1}, ip {2}, in_use {3}, project {4}, private {5}, usable {6}, timestamp {7}>'.format(
            self.id, self.name, self.ip, self.in_use, self.project, self.private, self.usable, self.timestamp)

    def map(self):
        return {"name": self.name,
                "ip": self.ip,
                "project": self.project,
                "in_use": self.in_use,
                "private": self.private,
                "usable": self.usable,
                "time_running": str(self.get_time_running())}

    def get_required_keys(self):
        return self.required_keys

    def get_time_running(self):
        return datetime.now() - self.timestamp if self.timestamp else None

    # 5 hr timeout
    def is_expired(self, expiry=18000):
        if self.get_time_running():
            return self.get_time_running().total_seconds() >= expiry
        else:
            return False


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
