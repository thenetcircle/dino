Grid Notify
----

Scalable websocket routing for notifications and chat.

Any number of nodes can be started on different machines or same machine on different port. Flask will handle connection
 routing using either Redis or RabbitMQ as a message queue internally. An nginx reverse proxy needs to sit infront of
 all these nodes with sticky sessions (ip_hash). Failover can be configured in nginx for high availability.
 
Example nginx configuration:

    upstream gridnodes {
        ip_hash;
    
        server maggie-kafka-1:5210;
        server maggie-kafka-2:5210;
        server maggie-kafka-3:5210;
        server maggie-spark-1:5210;
        server maggie-spark-2:5210;
        server maggie-spark-3:5210;
        server maggie-zoo-1:5210;
        server maggie-zoo-2:5210;
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

### Requirements

Some package requirements (debian/ubuntu):

    $ sudo apt-get install libssl-dev libmysqlclient-dev
    TODO: more requirements...

Requires Python >=3.5. Download and install from source:

    $ wget https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz
    $ tar -xvf Python-3.5.2.tar.xz
    $ cd Python-3.5.2/
    $ ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
    $ make
    $ sudo make altinstall # VERY important to use 'altinstall' instead of 'install'
    $ sudo apt-get install virtualenv
    
TODO: check if docker could be useful: https://www.digitalocean.com/community/tutorials/docker-explained-how-to-containerize-python-web-applications

### Running the application

    $ cd grid-notify/
    $ virtualenv --python=python3.5 env
    $ source env/bin/activate
    (env) $ pip install --upgrade .
    (env) $ ENVIRONMENT=prod gunicorn \
                --error-logfile ~/gridnotify-gunicorn-error.log \
                --log-file ~/gridnotify-gunicorn.log \
                --worker-class eventlet \
                --threads 16 \
                --worker-connections 5000 \
                --workers 1 \
                app:app
