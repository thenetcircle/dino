# Dino

Dino is a distributed notification service intended to push events to groups of clients. Example use cases are chat 
server, real-time notifications for websites, push notifications for mobile apps, multi-player browser games, and more. 
Dino is un-opinionated and any kind of events can be sent, meaning Dino only acts as the router of events between 
clients.

Any number of nodes can be started on different machines or same machine on different port. Flask will handle connection
 routing using either Redis or RabbitMQ as a message queue internally. An nginx reverse proxy needs to sit in-front of
 all these nodes with sticky sessions (`ip_hash`). Fail-over can be configured in nginx for high availability.

[![Dino Architecture](https://raw.githubusercontent.com/thenetcircle/dino/master/docs/dino-arch.png)](https://raw.githubusercontent.com/thenetcircle/dino/master/docs/dino-arch.svg)
