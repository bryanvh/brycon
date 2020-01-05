#!/bin/sh
# note: export AWS_PROFILE

# siple script for cleaning up old function versions, 10 at a time

P="7"

for V in 0 1 2 3 4 5 6 7 8 9; do
aws lambda delete-function \
  --function-name game_hunt_controller \
  --qualifier ${P}${V} \
  --region us-east-1
done
