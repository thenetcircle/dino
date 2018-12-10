import statsd
import time
import multiprocessing
import socket
import yaml

from redis import Redis

STATSD_HOST = '10.20.2.108'
REDIS_HOST = '10.20.2.109'
PREFIX = '%s.' % socket.gethostname()
GRANULARITY = 2  # seconds


hosts = yaml.safe_load(open('statsd-online-count.yaml'))

r_servers = dict()
for host, db in hosts.items():
    r_servers[host] = Redis(host=REDIS_HOST, db=db)


def online_count():
    c = statsd.StatsClient(STATSD_HOST, 8125, prefix=PREFIX + 'online')
    while True:
        for community, db_num in hosts.items():
            count = r_servers[community].bitcount('users:online:bitmap')
            c.gauge('%s.count' % community, count)
        time.sleep(GRANULARITY)


if __name__ == '__main__':
    multiprocessing.Process(target=online_count).start()
