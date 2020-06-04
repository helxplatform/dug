#!/bin/bash

NAMESPACE=${NAMESPACE-"default"}

kubectl -n $NAMESPACE delete configmap dug-configmap
kubectl -n $NAMESPACE create configmap dug-configmap --from-env-file=dug-configmap.properties
