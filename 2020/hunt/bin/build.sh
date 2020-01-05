#!/bin/sh

LAMBDA_DEPS=../lib/package
LAMBDA_SRC=../src
LAMBDA_REQUIREMENTS=../lib/requirements.txt
LAMBDA_ARCHIVE=../lib/lambda.zip

# create/update package dependencies

mkdir -p ${LAMBDA_DEPS}
pip install \
  --upgrade \
  --requirement ${LAMBDA_REQUIREMENTS} \
  --target ${LAMBDA_DEPS} \
  --no-warn-conflicts

# create Lambda archive

rm -f ${LAMBDA_ARCHIVE}
(cd ${LAMBDA_DEPS}; zip -q -r9 ${OLDPWD}/${LAMBDA_ARCHIVE} .)
(cd ${LAMBDA_SRC}; zip -r9 ${OLDPWD}/${LAMBDA_ARCHIVE} *.py *.yaml *.html *.json)
