############################################################
# Dockerfile to build a Dino Container
############################################################

FROM python:3.9.17-slim

WORKDIR /dino

COPY . .

RUN apt update && apt install -y build-essential libmariadb-dev-compat libmariadb-dev

RUN pip install --upgrade pip setuptools && \
        pip install --upgrade -r requirements.txt && \
        pip install --no-deps .

CMD gunicorn --worker-class eventlet -w 1 --threads 1 --worker-connections 1000 --timeout 120 -b 0.0.0.0:5120 --name dino-dev-test --no-sendfile rest:app