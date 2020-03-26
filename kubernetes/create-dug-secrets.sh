#!/bin/bash

random-string() {
  env LC_CTYPE=C tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w ${1:-32} | head -n 1
}

SECRET_PROPS=./dug-secrets.properties
if [ -f $SECRET_PROPS ]
then
  source $SECRET_PROPS
fi
NAMESPACE=${NAMESPACE-"default"}

# If passwords are empty then set to a random string.
ELASTIC_PASSWORD=${ELASTIC_PASSWORD-`random-string 12`}
NEO4J_PASSWORD=${NEO4J_PASSWORD-`random-string 12`}
REDIS_PASSWORD=${REDIS_PASSWORD-`random-string 12`}

LOG="create-dug-secret-out.log"

# Echo passwords to a file so they are known if randomly set.
date >> $LOG
echo "ELASTIC_PASSWORD=$ELASTIC_PASSWORD" >> $LOG
echo "NEO4J_PASSWORD=$NEO4J_PASSWORD" >> $LOG
echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> $LOG
echo "---" >> $LOG

export ELASTIC_PASSWORD=`echo -n "$ELASTIC_PASSWORD" | base64`
export NEO4J_PASSWORD=`echo -n "$NEO4J_PASSWORD" | base64`
export REDIS_PASSWORD=`echo -n "$REDIS_PASSWORD" | base64`

cat dug-secrets-template.yaml | envsubst | kubectl apply -n $NAMESPACE -f -
