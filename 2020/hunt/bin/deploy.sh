#!/bin/sh
# note: export AWS_PROFILE
# note: run build.sh first

[[ -z "${AWS_PROFILE}" ]] && { echo "must define AWS_PROFILE"; exit 1; }

echo "updating lambda code..."

LAMBDA_ARCHIVE=../lib/lambda.zip
aws lambda update-function-code \
  --function-name game_hunt_controller \
  --zip-file fileb://${LAMBDA_ARCHIVE} \
  --region us-east-1 \
  >/dev/null

echo "publishing new lambda version..."

NEW_VERSION=$(
aws lambda publish-version \
  --function-name game_hunt_controller \
  --region us-east-1 \
  --output text \
  --query 'Version'
)

echo "new function version: $NEW_VERSION"

echo "getting cloudfront distribution..."

CF_DISTRIBUTION=E3UXOZYS5XDNUN
aws cloudfront get-distribution-config --id ${CF_DISTRIBUTION} \
  > ${CF_DISTRIBUTION}.json

ETAG=$(jq -r .ETag ${CF_DISTRIBUTION}.json)

jq -r .DistributionConfig ${CF_DISTRIBUTION}.json \
  | sed -e "s/game_hunt_controller:[0-9]*/game_hunt_controller:${NEW_VERSION}/" \
  > ${CF_DISTRIBUTION}-config.json

echo "updating cloudfront distribution..."

aws cloudfront update-distribution --id ${CF_DISTRIBUTION} \
  --distribution-config file://${CF_DISTRIBUTION}-config.json \
  --if-match ${ETAG} \
  --query "Distribution.DistributionConfig.CacheBehaviors.Items[0].LambdaFunctionAssociations.Items[0].LambdaFunctionARN"

