from flask import Flask, request, jsonify, abort
import json
import sys
from sqlalchemy import exc
from flasgger import Swagger
from flasgger.utils import swag_from
from config import generate_config
from models import db
from backends.gcloud import validate_token

from methods import generate_resource_methods
from checkers import generate_request_checker

swagger_template = {
    # Other settings

    'securityDefinitions': {
        'authorization': {
            'type': 'oauth2',
            'authorizationUrl': 'https://accounts.google.com/o/oauth2/auth',
            'flow': 'implicit',
            'scopes': {
                'https://www.googleapis.com/auth/cloud-platform': 'cloud platform authorization',
                'email': 'email authorization',
                'profile': 'profile authorization'
            }
        }
    }

    # Other settings
}

swagger_config = {
    "headers": [
    ],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    # "static_folder": "static",  # must be set by user
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}


app = Flask(__name__)
app.config.from_object('config.Config')
Swagger(app, config=swagger_config, template=swagger_template)
db.init_app(app)
backend_config = generate_config(app.config['RESOURCE_BACKEND'])
resource_methods = generate_resource_methods(app.config['RESOURCE_BACKEND'], backend_config)
check_request = generate_request_checker(app.config['RESOURCE_BACKEND'])


## Authentication & Authorization ##

def authorized(fn):
    """Decorator that checks that requests
    contain an id-token in the request header.
    userid will be None if the
    authentication failed, and have an id otherwise.

    Usage:
    @app.route("/")
    @authorized
    def secured_root(userid=None):
        pass
    """

    def _wrap(*args, **kwargs):

        if 'Authorization' not in request.headers:
            # Unauthorized
            print("No token in header")
            abort(401)
            return None

        print("Checking token...")
        userid = validate_token(request.headers['Authorization'])
        if not userid:
            print("Authentication returned FAIL!")
            # Unauthorized
            abort(401)
            return None
        if app.config['RESOURCE_BACKEND'] == 'gce':
            if not backend_config.is_authorized(request.headers['Authorization'], app.config['OAUTH_PROJECT']):
                print("Authorization returned FAIL!")
                # Unauthorized
                abort(401)
                return None

        return fn(*args, **kwargs)
    _wrap.func_name = fn.func_name
    return _wrap


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
@authorized
def api_create_resource():
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
@swag_from('swagger/resources_get_single.yml', methods=['GET'])
@authorized
def api_get_resource(name):
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
@swag_from('swagger/resources_get_on_kwd.yml', methods=['GET'])
@authorized
def api_get_by_search(keyword):
    try:
        resp = resource_methods.list_resources_by_keyword(keyword)
        if resp:
            return json.dumps([x.map() for x in resp.all()]), 200
        else:
            return "No resources found matching regex!", 404

    except exc.DataError as e:
        return ("Invalid keyword \"{0}\". Try removing bad characters.".format(keyword, e)), 400


@app.route('/resources/<name>', methods=['POST'])
@swag_from('swagger/resources_post_name.yml', methods=['POST'])
@authorized
def api_update_resource(name):
    try:
        request.get_json()
    except:
        return "Empty request body", 400

    resp = resource_methods.get_resource_by_name(name)
    if resp:
        body = request.get_json()
        errors = check_request.check_request_update(body)
        if not errors:
            if not check_request.if_can_update_attr(body, resp.map()):
                return "Resource is not usable!  Cannot update.", 405
            else:
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
@swag_from('swagger/resources_delete.yml', methods=['DELETE'])
@authorized
def api_delete_resource(name):
    try:
        resource_methods.delete_resource(name)
        return "Deleted resource {0}".format(name), 204
    except:
        e = sys.exc_info()[1]
        return str(e), 500


@app.route('/resources/allocate', methods=['POST'])
@swag_from('swagger/resources_allocate.yml', methods=['POST'])
@authorized
def api_allocate():

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
@swag_from('swagger/resources_allocate_timeout.yml', methods=['GET'])
@authorized
def api_get_timeouts():
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
