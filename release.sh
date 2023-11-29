#!/bin/bash

VERSION="1.2.0-alpine"

echo "======login to private repo======"
docker login -u="yannick_siewe" -p="HBTOgUjBE1cMCWZ+TfK5BEGSTURZ7XrDtwefLosCsmgP90gBK2D8OZGJh4qTeTMw" quay.io

echo "======build new version======"
docker buildx build -t k8s-iam-operator:2.6.0-alpine . --load

docker tag k8s-iam-operator:$VERSION quay.io/yannick_siewe/k8s-iam-operator:$VERSION

echo "======push to registry======"
docker push quay.io/yannick_siewe/k8s-iam-operator:$VERSION

echo "======deploy new version======"

echo "======set new version======"
yq eval '.spec.template.spec.containers[0].image = "quay.io/yannick_siewe/k8s-iam-operator:'$VERSION'"' -i deployment.yaml

echo "======apply======"
kubectl apply -f ./crd
kubectl apply -f deployment.yaml