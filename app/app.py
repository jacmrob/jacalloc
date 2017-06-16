from flask import Flask, request, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
import json
import sys

from models import db, Resource

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)


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
        in_use=body['in_use']
    )
    db.session.add(resource)
    db.session.commit()

def update_resource(body):
    r = Resource.query.filter_by(name=body['name']).first()
    r.in_use = body['in_use']
    db.session.commit()

def get_all_unallocated():
    return [x.map() for x in Resource.query.filter(Resource.in_use == False)]

## Routes ##

@app.route('/')
def health():
    return 'Service running!', 200

@app.route('/allocate', methods=['POST'])
def allocate():
    errors = []
    print request
    try:
        request.get_json()
    except:
        return "Empty request body", 400

    body = request.get_json()
    missing = check_request(body, ['name', 'ip', 'in_use'])

    # validate request
    if missing:
        return 'Request missing following fields: {}'.format(missing), 400
    else:
        # new resource
        if not Resource.query.filter_by(name=body['name']).first():
            try:
                create_resource(body)
                return "Created record for {0}".format(body['name']), 200
            except:
                e = sys.exc_info()[0]
                errors.append("Unable to create new record for {0}".format(body['name']))

        # update resource
        else:
            try:
                update_resource(body)
                return "Updated record for {0}.  In Use = {1}".format(body['name'], body['in_use']), 200
            except:
                e = sys.exc_info()[0]
                errors.append("Unable to update record for {0}: {1}".format(body['name'], e))

    if errors:
        return str(errors), 500


@app.route('/query', methods=['GET'])
def query():
    resp = None
    if request.args.get('name'):
        resp = Resource.query.filter(Resource.name == request.args.get('name')).first()
    elif request.args.get('ip'):
        resp = Resource.query.filter(Resource.ip == request.args.get('ip')).first()
    else:
        # return all unallocated resources
        return json.dumps(get_all_unallocated()), 200

    if resp:
        return str(resp.in_use), 200

    else:
        return "Resource not found!", 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')