#!/bin/sh

# Sync web source files to S3 bucket
# note: export AWS_PROFILE
# note: activate virtual env for AWS CLI

BASE_DIR=$(dirname "$0")
aws s3 sync ${BASE_DIR}/../src s3://brycon.io --exclude .DS_Store --delete --profile brycon
