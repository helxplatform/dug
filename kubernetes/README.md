# Deploy Dug to Kubernetes

## Commands
```
# Copy the secrets template file and modify or ignore this step and random
# passwords will be set.  Check "create-dug-secret-out.log" for generated
# passwords and delete the log to keep passwords (generated or set) safe.
cp dug-secrets-template.properties dug-secrets.properties
# Edit dug-secrets.properties and change passwords.

cp dug-configmap-template.properties dug-configmap.properties
# Edit dug-configmap.properties and change values if needed.

# Ensure kubectl is configured for Kubernetes cluster.

# Execute script to create configmap in cluster.
NAMESPACE="dug" ./create-dug-configmap.sh

# Execute script to create secrets in cluster.
NAMESPACE="dug" ./create-dug-secrets.sh

# Deploy the Dug stack to Kubernetes.
kubectl -n dug apply -f stack.yaml
```
