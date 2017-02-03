
# Installation and Running

## Requirements

Some package requirements (debian/ubuntu):
    
    $ sudo apt-get update
    $ sudo apt-get install tar git curl nano wget dialog net-tools build-essential
    $ sudo apt-get install libssl-dev libmysqlclient-dev libpq-dev virtualenv

Requires Python >=3.5. Download and install from source:

    $ wget https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz
    $ tar -xvf Python-3.5.2.tar.xz
    $ cd Python-3.5.2/
    $ ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
    $ make
    $ sudo make altinstall

If using redis, postgresql/mysql and cassandra, please see relevant documentation for how to install:

* [Redis](https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-redis-on-ubuntu-16-04)
* [PostgreSQL](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-16-04)
* [MySQL](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-14-04)
* [Apache Cassandra](https://www.digitalocean.com/community/tutorials/how-to-install-cassandra-and-run-a-single-node-cluster-on-ubuntu-14-04)

## Clustering

If clustering dino, install a reverse proxy that supports websockets, e.g. nginx. Here's an example configuration:

    upstream gridnodes {
        ip_hash;
    
        server some-ip-or-host-1:5210;
        server some-ip-or-host-2:5210;
        server some-ip-or-host-3:5210;
        server some-ip-or-host-4:5210;
        server some-ip-or-host-5:5210;
        server some-ip-or-host-6:5210;
        server some-ip-or-host-7:5210;
        server some-ip-or-host-8:5210;
    }
    
    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }
    
    server {
        listen 5200;
    
        location / {
            access_log on;
    
            proxy_pass http://gridnodes;
            proxy_next_upstream error timeout invalid_header http_500;
            proxy_connect_timeout 2;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    
            # WebSocket support (nginx 1.4)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }

## Running the application

    $ cd dino/
    $ virtualenv --python=python3.5 env
    $ source env/bin/activate
    (env) $ pip install --upgrade -r requirements.txt
    (env) $ pip install --upgrade --no-deps .
    (env) $ ENVIRONMENT=dev gunicorn \
                --error-logfile ~/dino-gunicorn-error.log \
                --log-file ~/dino-gunicorn.log \
                --worker-class eventlet \
                --threads 1 \
                --worker-connections 5000 \
                --workers 1 \
                --bind 0.0.0.0:5210 \
                app:app

### Running in Docker

First create the image:

    sudo docker build -t dino .

Then we can run it (create an environments file in secrets/ for your chosen environment (dev/prod/etc), e.g. 
`secrets/dev.env`. Check the `secrets/default.env` for an example. Then we can run the image:

    sudo docker run --env-file=secrets/dev.env --env DINO_PORT=5120 -t dino

Note that we didn't put the port in the `dev.env` file (though we could), because if starting multiple dino nodes they
need to use different ports.

### Running in Kubernetes

For running in Kubernetes we need to use Kubernetes `Secrets` instead of the `.env` files. Example configuration for 
some secret values for your pod:

    apiVersion: v1
    kind: Pod
    metadata:
      name: secret-env-pod
    spec:
      containers:
        - name: mycontainer
          image: redis
          env:
            - name: DINO_DB_HOST
              valueFrom:
                secretKeyRef:
                  name: dev-secrets
                  key: db-host
            - name: DINO_DB_USER
              valueFrom:
                secretKeyRef:
                  name: dev-secrets
                  key: db-user
      restartPolicy: Never

Read more on Kubernetes website on [how to create the secrets object](https://kubernetes.io/docs/user-guide/secrets/#creating-your-own-secrets) 
and then how to [configure your pod to use it](https://kubernetes.io/docs/user-guide/secrets/#using-secrets-as-environment-variables).

## Building the documentation

Viewing locally:

    $ mkdocs serve

Building the site (not necessary):

    $ mkdocs build
    
Deploy to gihub pages:

    $ mkdocs gh-deploy
