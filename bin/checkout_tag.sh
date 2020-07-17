#!/usr/bin/env bash

TAG_NAME=$1

if [ ! -f .dino.yaml ]; then
    echo "error: you need to copy your dino.yaml settings to '.dino.yaml' before upgrading dino"
    exit 1
fi

echo "fetching new tags from git... "
if ! git fetch; then
    echo "error: could not fetch from git"
    exit 1
fi

if ! git checkout -- dino.yaml; then
    echo "error: could not clear changes to dino.yaml settings file"
    exit 1
fi

echo "switching to tag $TAG_NAME... "
if ! git checkout $TAG_NAME; then
    echo "error: could not switch to specified dino tag $TAG_NAME"
    exit 1
fi

if ! cp .dino.yaml dino.yaml; then
    echo "error: after switching tag, could not copy .dino.yaml to dino.yaml"
    exit 1
fi
