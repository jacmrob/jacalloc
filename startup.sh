#!/usr/bin/env bash

sleep 10
python manage.py db init
python manage.py db migrate

python app.py