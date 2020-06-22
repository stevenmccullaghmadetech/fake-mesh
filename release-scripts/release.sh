#!/bin/bash 

set -e

export BUILD_TAG=latest
export RELEASE_VERSION=0.1.6
export DOCKER_REGISTRY=local/
cd ..

docker-compose build

docker tag local/fake-mesh:latest nhsdev/fake-mesh:${RELEASE_VERSION}

if [ "$1" == "-y" ];
then
  echo "Tagging and pushing Docker image and git tag"
  docker push nhsdev/fake-mesh:${RELEASE_VERSION}
  git tag -a ${RELEASE_VERSION} -m "Release ${RELEASE_VERSION}"
  git push origin ${RELEASE_VERSION}
fi

