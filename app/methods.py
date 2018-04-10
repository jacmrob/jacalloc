from models import db, Resource
from backends.gcloud import *
import random
from googleapiclient.errors import HttpError


class CheckRequest:

    def check_request_contains(self, request_dict, keys):
        missing = []
        for k in keys:
            if k not in request_dict.keys():
                missing.append(k)
        return missing

    def check_request_does_not_contain(self, request_dict, keys):
        banned = []
        for k in keys:
            if k in request_dict:
                banned.append(k)
        return banned

    def check_request_create(self, request_dict):
        return self.check_request_contains(request_dict, Resource.required_keys)

    def check_request_update(self, request_dict):
        return self.check_request_does_not_contain(request_dict, Resource.immutable_keys)


class CheckRequestGcloud(CheckRequest):

    def check_request_create(self, request_dict):
        return CheckRequest.check_request_contains(self, request_dict, ["name", "tags", "project", "zone", "in_use"])


class ResourceMethods:
    """
    Provides default functionality for performing actions on Resources.
    """

    def get_resource_by_name(self, name, project=None):
        return Resource.query.filter(Resource.name == name).first()

    def list_resources_by_keyword(self, keyword):
        return Resource.query.filter(Resource.name.op("~")(keyword))

    def get_all_resources(self, **filters):
        res = Resource.query
        for name, filt in filters.iteritems():
            if filt is not None:
                d = {name: filt}
                res = res.filter_by(**d)
        return [x.map() for x in res.all()]

    def create_resource(self, body):
        resource = Resource(
            name=body['name'],
            ip=body['ip'],
            in_use=body['in_use'],
            project=body['project'],
            private=body.get('private') or False,
            usable=body.get('usable') or False
        )
        db.session.add(resource)
        db.session.commit()

    def update_resource(self, name, body):
        r = self.get_resource_by_name(name=name)
        for f in Resource.required_keys:
            if f in body:
                r.f = body[f]
        db.session.commit()

    def delete_resource(self, name):
        Resource.query.filter(Resource.name == name).delete()
        db.session.commit()

    def pick_random_resource(self, resources):
        x = random.randint(0, len(resources) - 1)
        return resources[x]


class GcloudResourceMethods(ResourceMethods):
    """
    Special functionality for performing actions on gcloud resources.
    """
    def __init__(self, backend_config):
        self.backend_config = backend_config

    def get_resource_by_name(self, name, project=None):
        if project:
            # Check within the scope of a specific project
            return GcloudInstanceResourceMethods(self.backend_config, project).get_resource_by_name(name, project)
        else:
            # Look within all projects; return first match found
            x = None
            for p in self.backend_config.projects:
                x = GcloudInstanceResourceMethods(self.backend_config, p).get_resource_by_name(name, p)
                if x:
                    break
            return x

    def update_resource(self, name, body):
        r = self.get_resource_by_name(name)
        if r:
            GcloudInstanceResourceMethods(self.backend_config, r["project"]).update_resource(name, body)

    def create_resource(self, body):
        GcloudInstanceResourceMethods(self.backend_config, body["project"]).create_resource(body)

    def delete_resource(self, name):
        r = self.get_resource_by_name(name)
        if r:
            GcloudInstanceResourceMethods(self.backend_config, r["project"]).delete_resource(name)


class GcloudInstanceResourceMethods(GcloudResourceMethods):
    def __init__(self, backend_config, project):
        GcloudResourceMethods.__init__(self, backend_config)
        self.project = project
        self.project_attrs = backend_config.projects.get(project)

    def get_resource_by_name(self, name, project=None):
        if self.project_attrs:
            try:
                instance = get_instance(self.project_attrs.compute, self.project, self.project_attrs.zone, name)
                return ResourceMethods.get_resource_by_name(self, name, project)

            except HttpError as e:
                if e.resp.status == 404:
                    if ResourceMethods.get_resource_by_name(self, name, project):
                        print "[DEBUG] Resource found in allocator db but not in google. Deleting from allocator db to clean up state."
                        ResourceMethods.delete_resource(name)
                    return None
                else:
                    raise StandardError("Something went wrong during instance get.")
        else:
            raise StandardError("Cannot fetch resource; no gcloud credentials for project {0}".format(self.project))

    def update_resource(self, name, body):
        if self.project_attrs:
            if body['usable']:
                try:
                    operation = start_instance(self.project_attrs.compute, self.project, self.project_attrs.zone, name)
                    wait_for_operation(self.project_attrs.compute, self.project, self.project_attrs.zone, operation['name'])
                except HttpError as e:
                    raise StandardError("Instance startup failed with status {0}".format(e.resp.status))

            if not body['usable']:
                try:
                    operation = stop_instance(self.project_attrs.compute, self.project, self.project_attrs.zone, name)
                    wait_for_operation(self.project_attrs.compute, self.project, self.project_attrs.zone, operation['name'])
                except HttpError as e:
                    raise StandardError("Instance startup failed with status {0}".format(e.resp.status))

            ResourceMethods.update_resource(self, name, body)
        else:
            raise StandardError("Cannot update resource; no gcloud credentials for project {0}".format(self.project))

    def create_resource(self, body):
        if self.project_attrs:
            try:
                operation = create_instance(self.project_attrs.compute, self.project, self.project_attrs.zone,
                                            body["name"], body["tags"],  disk_size=(body.get("disk_size") or '100'),
                                            disk_type=(body.get("disk_type") or "pd-ssd"),
                                            machine_type=(body.get("machine_type") or "n1-standard-8"))
                wait_for_operation(self.project_attrs.compute, self.project, self.project_attrs.zone, operation['name'])
                instance_data = list_instances(self.project_attrs.compute, self.project, self.project_attrs.zone, name=body['name'])[0]
                body["ip"] = str(instance_data['networkInterfaces'][0]['accessConfigs'][0]['natIP'])
                ResourceMethods.create_resource(self, body)

            except HttpError as e:
                if e.resp.status == 409:
                    raise StandardError("Error! instance {0} already exists in gcloud.".format(body["name"]))
                else:
                    raise StandardError("Something went wrong during instance creation.")
        else:
            raise StandardError("Cannot create resource; no gcloud credentials for project {0}".format(self.project))

    def delete_resource(self, name):
        if self.project_attrs:
            try:
                operation = delete_instance(self.project_attrs.compute, self.project, self.project_attrs.zone)
                wait_for_operation(self.project_attrs.compute, self.project, self.project_attrs.zone, operation['name'])
                ResourceMethods.delete_resource(self, name)

            except HttpError as e:
                if e.resp.status == 404:
                    # if we arrived here, we did not find the resource in google but we DID find it in the db
                    # deleting the db entry to clean up
                    raise StandardError("Error! instance {0} not found in gcloud.".format(body["name"]))
                else:
                    raise StandardError("Something went wrong during instance creation.")
        else:
            raise StandardError("Cannot delete resource; no gcloud credentials for project {0}".format(self.project))


def generate_resource_methods(backend, backend_config):
    if backend == 'gce':
        return GcloudResourceMethods(backend_config)
    else:
        return ResourceMethods


def generate_request_checker(backend):
    if backend == 'gce':
        return CheckRequestGcloud
    else:
        return CheckRequest
