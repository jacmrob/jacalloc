#!/usr/bin/env bash

set -e

sleep 12

pip install oauth2client
pip install httplib2

python -m unittest test.apitests.TestCreateApi
python -m unittest test.apitests.TestDependentApi
