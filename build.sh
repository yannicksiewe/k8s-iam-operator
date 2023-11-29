#!/bin/bash

VERSION="2.0.3-RC-alpine"

echo "======set minikube registry as default======"
# shellcheck disable=SC2046
eval $(minikube docker-env)

echo "======build and push to registry======"
docker build -t k8s-iam-operator:$VERSION .

echo "======logout to registry======"
# shellcheck disable=SC2046
eval $(minikube docker-env -u)

echo "======deploy new version======"

 echo "======set new version======"
 # shellcheck disable=SC2094
 sed -i "s/k8s-iam-operator:.*/k8s-iam-operator:$VERSION/g" 'deployment.yaml'

echo "======apply======"
kubectl apply -f ./crd
kubectl apply -f deployment.yaml