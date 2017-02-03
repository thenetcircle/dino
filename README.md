# Dino

[![Build Status](https://travis-ci.org/thenetcircle/dino.svg?branch=master)](https://travis-ci.org/thenetcircle/dino)
[![coverage](https://codecov.io/gh/thenetcircle/dino/branch/master/graph/badge.svg)](https://codecov.io/gh/thenetcircle/dino)
[![Code Climate](https://codeclimate.com/github/thenetcircle/dino/badges/gpa.svg)](https://codeclimate.com/github/thenetcircle/dino)
[![License](https://img.shields.io/github/license/thenetcircle/dino.svg)](LICENSE)

Dino is a distributed notification service intended to push events to groups of clients. Example use cases are chat 
server, real-time notifications for websites, push notifications for mobile apps, multi-player browser games, and more. 
Dino is un-opinionated and any kind of events can be sent, meaning Dino only acts as the router of events between 
clients.

Any number of nodes can be started on different machines or same machine on different port. Flask will handle connection
 routing using either Redis or RabbitMQ as a message queue internally. An nginx reverse proxy needs to sit in-front of
 all these nodes with sticky sessions (`ip_hash`). Fail-over can be configured in nginx for high availability.

Documentation is hosed on [GitHub Pages](https://thenetcircle.github.io/dino/).

[![Dino Architecture](https://raw.githubusercontent.com/thenetcircle/dino/master/docs/dino-arch.png)](https://raw.githubusercontent.com/thenetcircle/dino/master/docs/dino-arch.svg)

## Future features

* The socket.io flask cluster only acts as the router of events,
* Flask nodes sends events to kafka cluster,
* Kafka cluster enriches streams with a timestamp and sequence id,
* Flask nodes subscribe on certain streams, such as events to be broadcasted (e.g. messages in a chat room),
* For other streams such as updating acls, managing rooms, user info, another application will subscribe and store maybe in a relational db,
* An application will subscribe to the e.g. message streams to store data in cassandra.
