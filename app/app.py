from flask import Flask, request
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_pyfile('config.py')
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://jacalloc:jacalloc123@postgres:5432/jacalloc'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

## Routes ##

@app.route('/')
def health():
    return 'jacalloc running', 200

@app.route('/allocate', methods=['POST'])
def allocate():
    pass

@app.route('/query', methods=['GET'])
def query():
    pass


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')