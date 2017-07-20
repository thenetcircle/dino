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

## Monitoring

Loads of metrics is by default being collected by Dino and sent to `statsd`. To enable `statsd` monitoring, configure the `statsd` block in `dino.yaml` to [point to your `statsd` instance](https://thenetcircle.github.io/dino/md/installation/#monitoring):

[![Dino Grafana](https://raw.githubusercontent.com/thenetcircle/dino/master/docs/dino-grafana.png)](https://raw.githubusercontent.com/thenetcircle/dino/master/docs/dino-grafana.png)

## Future features

* The socket.io flask cluster only acts as the router of events,
* Flask nodes sends events to kafka cluster,
* Kafka cluster enriches streams with a timestamp and sequence id,
* Flask nodes subscribe on certain streams, such as events to be broadcasted (e.g. messages in a chat room),
* For other streams such as updating acls, managing rooms, user info, another application will subscribe and store maybe in a relational db,
* An application will subscribe to the e.g. message streams to store data in cassandra.

## Requirements

The minimum required python version is 3.6.0. The reason for requiring 3.6 is because it added support for 
[variable annotations](https://www.python.org/dev/peps/pep-0526/) (type hinting for variables), which in of itself is
not that big of an addition, but before 
[variable annotations came argument annotations and return type annotations](https://www.python.org/dev/peps/pep-0484/) 
('type hinting'), which is quite valuable during development. Arguably if you follow the TDD
methodology and have a rigorous test suit for your project, type hinting won't warn you about things that the test suit
will (probably) fail for, but during API restructuring and sometimes architectural design changes (since dino is
currently not a stable product), strong typing is quite a valuable tool for preventing silly mistakes by developers.

The rationale for requiring version 3.6.x instead of 3.5.x is that for most systems that will install python 3.5, it
would be the same process to install 3.6, since for lots of production systems the 3.5 version is not available as 
package and would be installed from source anyway.

Those of you that don't have that legacy issue, I'm sorry, but install 3.6.x from source anyway. :) It's usually 
required anyway since some distros won't allow you to have multi-version installs of the same runtime. Happy compiling!
(p.s. remember `altinstall` and and `--prefix` and you'll likely breeze through it (no warranty!!).