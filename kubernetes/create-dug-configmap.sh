#!/bin/bash

kubectl delete configmap dug-configmap
kubectl create configmap dug-configmap --from-env-file=dug-configmap.properties
