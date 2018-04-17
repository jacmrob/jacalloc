from flask import Flask, request, jsonify
import json
import sys
from sqlalchemy import exc
from flasgger import Swagger
from flasgger.utils import swag_from
from config import generate_config
from models import db

from methods import generate_resource_methods
from checkers import generate_request_checker

app = Flask(__name__)
Swagger(app)
app.config.from_object('config.Config')
db.init_app(app)
backend_config = generate_config(app.config['RESOURCE_BACKEND'])
resource_methods = generate_resource_methods(app.config['RESOURCE_BACKEND'], backend_config)
check_request = generate_request_checker(app.config['RESOURCE_BACKEND'])

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
    print resource_methods

    if request.method == 'GET':
        resp = resource_methods.get_all_resources(in_use=request.args.get('in_use'), project=request.args.get('project'), private=request.args.get('private'))
        return json.dumps(resp), 200

    elif request.method == 'POST':
        body = request.get_json()
        if not body:
            return "Empty request body", 400
        errors = check_request.check_request_create(body)

        # validate request
        if errors:
            return str(errors), 400
        else:
            # new resource
            if not resource_methods.get_resource_by_name(name=body['name']):
                try:
                    resource_methods.create_resource(body)
                    print "Created record for {0}".format(body['name'])
                    return json.dumps(body), 201

                except:
                    _, exc_value, _ = sys.exc_info()
                    errors = "Unable to create new record for {0}: {1}".format(body['name'], exc_value)

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
      - in: query
        description: Resource project
        name: project
        required: false
        type: string
    '''
    try:
        resp = resource_methods.get_resource_by_name(name, project=request.args.get('project'))
        if resp:
            return json.dumps(resp.map()), 200

        else:
            return "Resource not found!", 404
    except:
        _, exc_value, _ = sys.exc_info()
        return "Unable to fetch record {0}: {1}".format(name, exc_value), 500


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
        resp = resource_methods.list_resources_by_keyword(keyword)
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
    try:
        request.get_json()
    except:
        return "Empty request body", 400

    resp = resource_methods.get_resource_by_name(name)
    if resp:
        body = request.get_json()
        errors = check_request.check_request_update(body)
        if not errors:
            try:

                resource_methods.update_resource(name, body)
                new = resource_methods.get_resource_by_name(name)
                return json.dumps(new.map()), 200
            except:
                a, exc_value, _ = sys.exc_info()
                errors = "Unable to update record for {0}: {1}".format(name, exc_value)
        else:
            return str(errors), 400

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
        resource_methods.delete_resource(name)
        return "Deleted resource {0}".format(name), 204
    except:
        e = sys.exc_info()[1]
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

    free = resource_methods.get_all_resources(in_use="false", project=request.args.get('project'),
                                              private="false", usable="true")
    if free:
        try:
            allocated = resource_methods.pick_random_resource(free)
            resource_methods.update_resource(allocated['name'], {'in_use': True})
            allocated['in_use'] = True
            return json.dumps(allocated), 200
        except:
            e = sys.exec_info()[1]
            return str(e), 500
    else:
        return "No resources are free!", 412


@app.route('/resources/allocate/timeout', methods=['GET'])
def api_get_timeouts():
    '''
    Gets all allocated resources that have timed out
    ---
    tags:
      - Jacalloc API
    responses:
      '200':
        description: List of resources
      '500':
        description: Something went wrong during fetch
    parameters:
      - in: query
        description: Resource project
        name: project
        required: false
        type: string
      - in: query
        description: If resource private
        name: private
        required: false
        enum: ["true","false"]
      - in: query
        description: Amount of time (in seconds) in_use to filter resources by
        name: timeout
        required: false
        type: integer
        minimum: 1
    '''
    try:
        r = resource_methods.get_all_resources(in_use="true",
                                               project=request.args.get("project"),
                                               private=request.args.get("private"),
                                               expired=int(request.args.get("timeout")))
        return json.dumps(r), 200

    except:
        _, e, _ = sys.exec_info()
        return str(e), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
