from models import db, Resource
from backends.gcloud import *
import random
import datetime
from googleapiclient.errors import HttpError


class ResourceMethods:
    """
    Provides default functionality for performing actions on Resources.
    """

    def get_resource_by_name(self, name, project=None):
        if project:
            return Resource.query.filter(Resource.project == project).filter(Resource.name == name).first()
        return Resource.query.filter(Resource.name == name).first()

    def list_resources_by_keyword(self, keyword):
        return Resource.query.filter(Resource.name.op("~")(keyword))

    def get_all_resources(self, **filters):
        res = Resource.query
        for name, filt in filters.iteritems():
            if filt is not None and name is not 'expired':
                d = {name: filt}
                res = res.filter_by(**d)
        if 'expired' in filters:
            return [x.map() for x in res.all() if x.is_expired(filters['expired'] or 18000)]
        return [x.map() for x in res.all()]


    def create_resource(self, body):
        resource = Resource(
            name=body['name'],
            ip=body['ip'],
            in_use=body.get('in_use') or False,
            project=body['project'],
            private=body.get('private') or False,
            usable=body.get('usable') or False
        )
        db.session.add(resource)
        db.session.commit()

    def update_resource(self, name, body):
        if body.get('in_use'):
            body['timestamp'] = datetime.datetime.now()

        r = self.get_resource_by_name(name=name)
        for f in body.keys():
            if hasattr(r, f):
                setattr(r, f, body[f])

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

    def get_all_resources(self, **filters):
        resources = ResourceMethods.get_all_resources(self, **filters)
        return [r for r in resources if self.get_resource_by_name(r["name"], r["project"])]

    def update_resource(self, name, body):
        r = self.get_resource_by_name(name)
        if r:
            GcloudInstanceResourceMethods(self.backend_config, r.project).update_resource(name, body)

    def create_resource(self, body):
        GcloudInstanceResourceMethods(self.backend_config, body["project"]).create_resource(body)

    def delete_resource(self, name):
        r = self.get_resource_by_name(name)
        if r:
            GcloudInstanceResourceMethods(self.backend_config, r.project).delete_resource(name)
        else:
            raise StandardError("Resource {0} not found!".format(name))


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
                        print "[DEBUG] Resource found in allocator db but not in google. " \
                              "Deleting from allocator db to clean up state."
                        ResourceMethods.delete_resource(self, name)
                    return None
                else:
                    raise StandardError("Something went wrong during instance get.")
        else:
            print "[DEBUG] Cannot fetch resource; no gcloud credentials for project {0}".format(self.project)
            return None

    def update_resource(self, name, body):
        if self.project_attrs:
            usable = body.get('usable')
            if usable:
                try:
                    operation = start_instance(self.project_attrs.compute, self.project, self.project_attrs.zone, name)
                    wait_for_operation(self.project_attrs.compute, self.project, self.project_attrs.zone, operation['name'])
                    instance_data = list_instances(self.project_attrs.compute, self.project, self.project_attrs.zone, name=name)[0]
                    body["ip"] = str(instance_data['networkInterfaces'][0]['accessConfigs'][0]['natIP'])

                except HttpError as e:
                    raise StandardError("Instance startup failed with status {0}".format(e.resp.status))

            # Must use an explicit check of if usable == False to avoid turning off resource in the case where usable is not in body
            #   in this case, body.get('usable') will return None.  None != False :)
            if usable == False:
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
                                            body["name"], body["tags"],
                                            disk_size=(body.get("disk_size") or '100'),
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
                operation = delete_instance(self.project_attrs.compute, self.project, self.project_attrs.zone, name)
                wait_for_operation(self.project_attrs.compute, self.project, self.project_attrs.zone, operation['name'])
                ResourceMethods.delete_resource(self, name)

            except HttpError as e:
                if e.resp.status == 404:
                    # if we arrived here, we did not find the resource in google but we DID find it in the db
                    # deleting the db entry to clean up
                    raise StandardError("Error! instance {0} not found in gcloud.".format(name))
                else:
                    raise StandardError("Something went wrong during instance creation.")
        else:
            raise StandardError("Cannot delete resource; no gcloud credentials for project {0}".format(self.project))


## Object Generators ##

def generate_resource_methods(backend, backend_config):
    if backend == 'gce':
        return GcloudResourceMethods(backend_config)
    else:
        return ResourceMethods()

