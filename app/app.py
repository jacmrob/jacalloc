from flask import Flask, request, jsonify
import json
import sys
import random
from sqlalchemy import exc
from flasgger import Swagger
from flasgger.utils import swag_from

from models import db, Resource

app = Flask(__name__)
Swagger(app)
app.config.from_pyfile('config.py')
db.init_app(app)

## Resources Table methods ##

def check_request(request_dict, keys):
    missing = []
    for k in keys:
        if k not in request_dict:
            missing.append(k)
    return missing

def create_resource(body):
    resource = Resource(
        name=body['name'],
        ip=body['ip'],
        in_use=body['in_use'],
        project=body['project']
    )
    db.session.add(resource)
    db.session.commit()

def update_resource(name, body):
    r = Resource.query.filter_by(name=name).first()
    if 'in_use' in body:
        r.in_use = body['in_use']
    if 'name' in body:
        r.name = body['name']
    if 'ip' in body:
        r.ip = body['ip']
    if 'project' in body:
        r.project = body['project']
    db.session.commit()

def delete_resource(name):
    Resource.query.filter(Resource.name == name).delete()
    db.session.commit()


def get_resource_by_name(name):
    return Resource.query.filter(Resource.name == name)[0].map()

def get_all_resources(in_use=None, project=None):
    if in_use and project:
        return [x.map() for x in Resource.query.filter(Resource.project == project).filter(Resource.in_use == in_use)]
    if project:
        return [x.map() for x in Resource.query.filter(Resource.project == project)]
    if in_use:
        return [x.map() for x in Resource.query.filter(Resource.in_use == in_use)]
    return [x.map() for x in Resource.query.all()]


def pick_random_resource(resources):
    x = random.randint(0, len(resources) - 1)
    return resources[x]

## Routes ##

@app.route('/')
def api_health():
    '''
    Health check
    ---
    tags:
      - health
    responses:
      '200':
        description: App is running
    '''
    # TODO: check if can ping db
    return 'Service running!', 200


@app.route('/resources', methods=['GET', 'POST'])
@swag_from('swagger/resources_get.yml', methods=['GET'])
@swag_from('swagger/resources_post.yml', methods=['POST'])
def api_create_resource():
    errors = []
    print request

    if request.method == 'GET':
        resp = get_all_resources(in_use=request.args.get('in_use'), project=request.args.get('project'))
        return json.dumps(resp), 200

    elif request.method == 'POST':
        body = request.get_json()
        if not body:
            return "Empty request body", 400
        missing = check_request(body, ['name', 'ip', 'in_use', 'project'])

        # validate request
        if missing:
            return 'Request missing following fields: {}'.format(missing), 400
        else:
            # new resource
            if not Resource.query.filter_by(name=body['name']).first():
                try:
                    create_resource(body)
                    print "Created record for {0}".format(body['name'])
                    return json.dumps(body), 201
                except:
                    e = sys.exc_info()[0]
                    errors.append("Unable to create new record for {0}: {1}".format(body['name'], e))

            else:
                return "Resource already exists!", 409
        if errors:
            return str(errors), 500


@app.route('/resources/<name>', methods=['GET'])
def api_get_resource(name):
    '''
    Gets a resource
    ---
    tags:
      - Jacalloc API
    responses:
      '200':
        description: Resource found
      '404':
        description: Resource not found
    parameters:
      - in: path
        description: resource name
        name: name
        required: true
        type: string
    '''
    resp = Resource.query.filter(Resource.name == name).first()
    if resp:
        return json.dumps(resp.map()), 200

    else:
        return "Resource not found!", 404


@app.route('/resources/name/<keyword>', methods=['GET'])
def api_get_by_search(keyword):
    '''
    Gets all resources on a keyword
    ---
    tags:
      - Jacalloc API
    responses:
      '200':
        description: Resource(s) found matching request
      '404':
        description: No resource(s) found matching request
      '400':
        description: Resource request malformed
    parameters:
      - in: path
        description: keyword to search on
        name: keyword
        required: true
        type: string
    '''
    try:
        resp = Resource.query.filter(Resource.name.op("~")(keyword))
        if resp:
            return json.dumps([x.map() for x in resp.all()]), 200
        else:
            return "No resources found matching regex!", 404

    except exc.DataError as e:
        return ("Invalid keyword \"{0}\". Try removing bad characters.".format(keyword, e)), 400


@app.route('/resources/<name>', methods=['POST'])
def api_update_resource(name):
    '''
    Updates a resource
    ---
    tags:
      - Jacalloc API
    responses:
      '200':
        description: Resource successfully updated
      '400':
        description: Malformed request
      '404':
        description: Resource not found
    parameters:
      - in: path
        description: Resource name
        name: name
        required: true
        type: string
      - in: body
        name: body
        required: true
        schema:
          properties:
            ip:
              type: string
              description: Resource IP
            project:
              type: string
              description: Resource project
            in_use:
              type: string
              enum: ["true", "false"]
              description: Resource status
    '''
    errors = []
    print request
    try:
        request.get_json()
    except:
        return "Empty request body", 400

    resp = Resource.query.filter(Resource.name == name).first()
    if resp:
        body = request.get_json()
        try:
            update_resource(name, body)
            new = get_resource_by_name(name)
            return json.dumps(new), 200
        except:
            e = sys.exc_info()[0]
            errors.append("Unable to update record for {0}: {1}".format(body['name'], e))

    else:
        return "Resource not found. Cannot update.", 404

    if errors:
        return str(errors), 500


@app.route('/resources/<name>', methods=['DELETE'])
def api_delete_resource(name):
    '''
    Deletes a resource
    ---
    tags:
      - Jacalloc API
    responses:
      '201':
        description: Resource successfully deleted
      '500':
        description: Resource delete failed
    parameters:
      - in: path
        description: Resource name
        name: name
        required: true
        type: string
    '''
    try:
        delete_resource(name)
        return "Deleted resource {0}".format(name), 201
    except:
        e = sys.exc_info()[0]
        return str(e), 500


@app.route('/resources/allocate', methods=['POST'])
def api_allocate():
    '''
    Allocates a resource
    Chooses a random resource where in_use == False and sets in_use = True
    ---
    tags:
      - Jacalloc API
    responses:
      '200':
        description: Resource successfully allocated
      '412':
        description: No resources are free to allocate
      '500':
        description: Resource allocation failed
    parameters:
      - in: query
        description: Resource project
        name: project
        required: false
        type: string
    '''

    free = get_all_resources(in_use="false", project=request.args.get('project'))
    if free:
        try:
            allocated = pick_random_resource(free)
            update_resource(allocated['name'], {'in_use': True})
            allocated['in_use'] = True
            return json.dumps(allocated), 200
        except:
            e = sys.exec_info()[0]
            return str(e), 500
    else:
        return "No resources are free!", 412



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')