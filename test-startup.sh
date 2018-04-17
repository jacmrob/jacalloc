#!/usr/bin/env bash

set -e

sleep 12
python -m unittest test.apitests.TestCreateApi
python -m unittest test.apitests.TestDependentApi
