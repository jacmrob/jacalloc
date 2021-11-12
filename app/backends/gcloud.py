from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import sys, os
import time
import requests


# return the credentials of a service account
def get_service_acct_creds(creds_json):
    return ServiceAccountCredentials.from_json_keyfile_name(creds_json)


# return an instance of Google Compute Engine
def create_compute_instance(credentials):
    return build('compute', 'v1', credentials=credentials)


def create_compute_instance_from_json_creds(creds_json):
    c = get_service_acct_creds(creds_json)
    return create_compute_instance(c)


def create_instance(compute, project, zone, name, tags, disk_size="100", disk_type="pd-ssd", machine_type="n1-standard-8"):
    image_response = compute.images().get(
        project='ubuntu-os-cloud', image='ubuntu-1604-xenial-v20210928').execute()
    source_disk_image = image_response['selfLink']
    network = 'managed' if project == 'broad-dsde-dev' else 'default'

    config = {
        'name': name,
        'machineType': "zones/" + zone + "/machineTypes/" + machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                    'diskType': 'zones/' + zone + '/diskTypes/' + disk_type,
                    'diskSizeGb': disk_size
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': "projects/" + project + "/global/networks/" + network,
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                "https://www.googleapis.com/auth/cloud.useraccounts.readonly",
                "https://www.googleapis.com/auth/devstorage.read_only",
                "https://www.googleapis.com/auth/logging.write",
                "https://www.googleapis.com/auth/monitoring.write",
                "https://www.googleapis.com/auth/service.management.readonly",
                "https://www.googleapis.com/auth/servicecontrol",
                "https://www.googleapis.com/auth/source.full_control"
            ]
        }],
        'tags': {
            'items': [t for t in tags]
        }
    }

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()


def delete_instance(compute, project, zone, name):
    return compute.instances().delete(
        project=project,
        zone=zone,
        instance=name).execute()


# returns list of instances that satisfies the given filters
def list_instances(compute, project, zone, name=None, tags=None):
    instances = compute.instances().list(project=project, zone=zone).execute()
    result = instances['items']
    if tags:
        result = filter(lambda x: x['tags'].get('items') and set(tags) < set(x['tags']['items']), result)
    if name:
        result = filter(lambda x: x.get('name') == name, result)
    return result


def start_instance(compute, project, zone, name):
    return compute.instances().start(
        project=project,
        zone=zone,
        instance=name).execute()


def stop_instance(compute, project, zone, name):
    return compute.instances().stop(
        project=project,
        zone=zone,
        instance=name).execute()


def reset_instance(compute, project, zone, name):
    return compute.instances().reset(
        project=project,
        zone=zone,
        instance=name).execute()


def get_instance(compute, project, zone, name):
    return compute.instances().get(
        project=project,
        zone=zone,
        instance=name
    ).execute()


def get_instance_status(compute, project, zone, name):
    instance = get_instance(compute, project, zone, name)
    return instance['status']


def wait_for_operation(compute, project, zone, operation):
    sys.stdout.write('Waiting for operation to finish')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        else:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(1)


def validate_token(access_token):
    '''Verifies that an access-token is valid and
    meant for this app.

    Returns None on fail, and an e-mail on success'''
    resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo",
                           headers={'Host': 'www.googleapis.com',
                                    'Authorization': access_token})

    print resp.json()
    print access_token
    if not resp.status_code == 200:
        print("Token validation returned status {0}".format(resp.status_code))
        return None

    return resp.json()['email']


def is_compute_editor(access_token, project):
    '''Verifies that the user linked to an access-token has the right
    permissions to create and delete compute instances in the given project

    Returns False on fail, and True on success'''
    resp = requests.post("https://cloudresourcemanager.googleapis.com/v1beta1/projects/{0}:testIamPermissions"
                         .format(project),
                         headers={"Authorization": access_token},
                         data={"permissions": ["compute.instances.create"]})
    return resp.status_code == 200
