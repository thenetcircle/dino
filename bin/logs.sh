#!/bin/bash

gunicorn --bind 0.0.0.0:4848 logs:app $1
