#!/bin/bash

set -x

docker compose pull

docker compose build

docker compose up
