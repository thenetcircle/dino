# Storage

All events can be stored in four different storage types:

* Cassandra,
* Riak,
* Redis,
* Any RDBMS supported by SqlAlchemy.

## [Cassandra](http://cassandra.apache.org/)

_"The Apache Cassandra database is the right choice when you need scalability and high availability without compromising performance. Linear scalability and proven fault-tolerance on commodity hardware or cloud infrastructure make it the perfect platform for mission-critical data.Cassandra's support for replicating across multiple datacenters is best-in-class, providing lower latency for your users and the peace of mind of knowing that you can survive regional outages."_

## [Riak KV](http://basho.com/products/riak-kv/)

Riak KV with LevelDB backend.

_"Riak KV is a distributed NoSQL key-value database with advanced local and multi-cluster replication that guarantees reads and writes even in the event of hardware failures or network partitions."_


## [Redis](https://redis.io/)

_"Redis is an open source (BSD licensed), in-memory data structure store, used as a database, cache and message broker. It supports data structures such as strings, hashes, lists, sets, sorted sets with range queries, bitmaps, hyperloglogs and geospatial indexes with radius queries. Redis has built-in replication, Lua scripting, LRU eviction, transactions and different levels of on-disk persistence, and provides high availability via Redis Sentinel and automatic partitioning with Redis Cluster."_

## [SqlAlchemy](https://www.sqlalchemy.org/)

The following dialects are supports out-of-the-box by SqlAlchemy:

* Firebird,
* Microsoft SQL Server,
* MySQL,
* Oracle,
* PostgreSQL,
* SQLite,
* Sybase.

External production ready dialects:

* IBM DB2,
* Amazon Redshift,
* EXASolution,
* SAP Sybase SQL Anywhere,
* MonetDB,
* Snowflake,
* CrateDB.
