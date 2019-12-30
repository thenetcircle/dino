#!/usr/bin/env bash

CONDA_ENVIRONMENT=$1
DINO_ENVIRONMENT=$2
DINO_HOME=$3

source ~/bin/.bashrc
source activate ${CONDA_ENVIRONMENT}
python /usr/local/bin/count_users_in_rooms.py ${DINO_ENVIRONMENT} ${DINO_HOME}
