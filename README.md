# Dino

[![Build Status](https://travis-ci.org/thenetcircle/dino.svg?branch=master)](https://travis-ci.org/thenetcircle/dino)
[![coverage](https://codecov.io/gh/thenetcircle/dino/branch/master/graph/badge.svg)](https://codecov.io/gh/thenetcircle/dino)
[![Code Climate](https://codeclimate.com/github/thenetcircle/dino/badges/gpa.svg)](https://codeclimate.com/github/thenetcircle/dino)
[![License](https://img.shields.io/github/license/thenetcircle/dino.svg)](LICENSE)

Distributed websocket routing for notifications and chat.

* [Getting started](docs/md/getting_started.md)
* [API documentation](docs/md/api.md)
* [Who Is Online documentation](docs/md/wio.md)
* [Events documentation](docs/md/events.md)
* [Rest documentation](docs/md/rest.md)
* [Generated documentation](https://thenetcircle.github.io/dino/)

[![Dino Architecture](https://raw.githubusercontent.com/thenetcircle/dino/master/docs/dino-arch.png)](https://raw.githubusercontent.com/thenetcircle/dino/master/docs/dino-arch.svg)

Any number of nodes can be started on different machines or same machine on different port. Flask will handle connection
 routing using either Redis or RabbitMQ as a message queue internally. An nginx reverse proxy needs to sit in-front of
 all these nodes with sticky sessions (ip_hash). Fail-over can be configured in nginx for high availability.

## Future features

* The socket.io flask cluster only acs as the router of events,
* Flask nodes sends events to kafka cluster,
* Kafka cluster enriches streams with a timestamp and sequence id,
* Flask nodes subscribe on certain streams, such as events to be broadcasted (e.g. messages in a chat room),
* For other streams such as updating acls, managing rooms, user info, another application will subscribe and store maybe in a relational db,
* An application will subscribe to the e.g. message streams to store data in cassandra.
