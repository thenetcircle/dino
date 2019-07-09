import statsd
import time
import multiprocessing
import socket
import yaml

from redis import Redis

STATSD_HOST = '10.20.2.108'
PREFIX = '%s.' % socket.gethostname()
GRANULARITY = 2  # seconds


hosts = yaml.safe_load(open('statsd-online-count.yaml'))

r_servers = dict()
for host, port, community, db in hosts:
    r_servers[community] = Redis(host=host, port=port, db=db)


def online_count():
    c = statsd.StatsClient(STATSD_HOST, 8125, prefix=PREFIX + 'online')
    while True:
        for _, _, community, db_num in hosts:
            count = r_servers[community].scard('users:multicast')
            c.gauge('%s.count' % community, count)

            sessions = r_servers[community].hgetall('session:count')
            session_count = 0

            for _, value in sessions.items():
                session_count += int(float(str(value, 'utf-8')))

            c.gauge('%s.count' % community, count)
            c.gauge('%s.sessions' % community, session_count)
        time.sleep(GRANULARITY)


if __name__ == '__main__':
    multiprocessing.Process(target=online_count).start()
