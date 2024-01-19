#!/bin/bash

PROJECT_BASE_DIR=$(pwd)/../

PROJECT_NAME=shut-no-shut
CHECKOUT=jifox-dev

cruft create \
    --directory=nautobot-app \
    --overwrite-if-exists \
    --checkout=${CHECKOUT} \
    --config-file=${PROJECT_BASE_DIR}/nautobot-app-${PROJECT_DIR}/.cruft_data.json \
    --output-dir=${PROJECT_BASE_DIR}/${PROJECT_DIR} \
    /home/ansible/dev-nautobot-v2/cookiecutter-nautobot-app
