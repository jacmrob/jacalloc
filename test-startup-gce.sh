#!/usr/bin/env bash

set -e

sleep 12
python -m unittest test.apitests.TestCreateApiGcloud
python -m unittest test.apitests.TestDependentApiGcloud
