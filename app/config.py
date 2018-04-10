import sys, os
from backends.gcloud import create_compute_instance_from_json_creds
import dotenv

# Flask config.py

class Config():
    SQLALCHEMY_DATABASE_URI = os.environ.get('POSTGRES_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    RESOURCE_BACKEND = os.environ.get('RESOURCE_BACKEND') or 'default'
    RESOURCE_TYPE = os.environ.get('RESOURCE_TYPE') or 'default'
    ROOT_DIR = os.environ.get("ROOT_DIR") or "/app"
    ALL_FIELDS = ["name", "ip", "project", "in_use", "private"]
    REQUIRED_FIELDS = ["name", "ip", "project", "in_use"]


class GcloudConfig(Config):
    def __init__(self):
        self.projects = self.init_projects()

    def init_projects(self):
        projects = {}
        for _, _, files in os.walk(os.getcwd()):
            for f in files:
                if f.endswith(".env"):
                    p_name = f.split(".")[0]
                    projects[p_name] = GcloudProjConfig(p_name)
        return projects


class GcloudProjConfig():
    def __init__(self, project_name):
        dotenv.load_dotenv(dotenv.find_dotenv(project_name + ".env"))
        self.compute = create_compute_instance_from_json_creds(os.getenv("SVC_ACCT_PATH"))
        self.zone = os.getenv("ZONE")
        self.project = project_name


def generate_config(resource_backend):
    if resource_backend == 'gce':
        return GcloudConfig()
    else:
        print "[WARN] No resource backend specified, using default config."
        return None
