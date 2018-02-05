import statsd
import time
import psutil
import multiprocessing
import socket
import os
import subprocess

STATSD_HOST='10.20.2.108'
PREFIX='%s.' % socket.gethostname()
GRANULARITY = 10  # seconds
PATHS = [('/', 'root'), ('/data', 'data')]


def connections():
    c = statsd.StatsClient(STATSD_HOST, 8125, prefix=PREFIX + 'system.network')
    while True:
        try:
            process = subprocess.Popen(['count_waiting_conn.sh'], stdout=subprocess.PIPE)
            out, _ = process.communicate()
            n_waiting = int(float(str(out, 'utf-8').strip()))
            c.gauge('conn_wait', n_waiting)
        except Exception as e:
            print('error: %s' % str(e))
        time.sleep(GRANULARITY * 3)


def disk():
    c = statsd.StatsClient(STATSD_HOST, 8125, prefix=PREFIX + 'system.disk')
    while True:
        for path, label in PATHS:
            disk_usage = psutil.disk_usage(path)

            st = os.statvfs(path)
            total_inode = st.f_files
            free_inode = st.f_ffree
            inode_percentage = int(100*(float(total_inode - free_inode) / total_inode))

            c.gauge('%s.inodes.percent' % label, inode_percentage)
            c.gauge('%s.total' % label, disk_usage.total)
            c.gauge('%s.used' % label, disk_usage.used)
            c.gauge('%s.free' % label, disk_usage.free)
            c.gauge('%s.percent' % label, disk_usage.percent)
        time.sleep(GRANULARITY)


def network():
    c = statsd.StatsClient(STATSD_HOST, 8125, prefix=PREFIX + 'system.network')
    t0 = time.time()
    counters = psutil.net_io_counters(pernic=True)

    last_totals = dict()
    totals = dict()
    interfaces = set([key for key in counters.keys() if key != 'lo'])
    for interface in interfaces:
        totals[interface] = (counters[interface].bytes_sent, counters[interface].bytes_recv)
        last_totals[interface] = (counters[interface].bytes_sent, counters[interface].bytes_recv)

    while True:
        for interface in interfaces:
            counter = psutil.net_io_counters(pernic=True)[interface]
            t1 = time.time()
            totals[interface] = (counter.bytes_sent, counter.bytes_recv)

            ul, dl = [(now - last) / (t1 - t0) / 1000.0
                      for now, last in zip(totals[interface], last_totals[interface])]

            t0 = time.time()
            c.gauge('%s.upload.kbps' % interface, ul)
            c.gauge('%s.download.kbps' % interface, dl)
            last_totals[interface] = totals[interface]

        time.sleep(GRANULARITY)


def cpu_times():
    c = statsd.StatsClient(STATSD_HOST, 8125, prefix=PREFIX + 'system.cpu')
    while True:
        cpu_t = psutil.cpu_times()
        c.gauge('system_wide.times.user', cpu_t.user)
        c.gauge('system_wide.times.nice', cpu_t.nice)
        c.gauge('system_wide.times.system', cpu_t.system)
        c.gauge('system_wide.times.idle', cpu_t.idle)
        c.gauge('system_wide.times.iowait', cpu_t.iowait)
        c.gauge('system_wide.times.irq', cpu_t.irq)
        c.gauge('system_wide.times.softirq', cpu_t.softirq)
        c.gauge('system_wide.times.steal', cpu_t.steal)
        c.gauge('system_wide.times.guest', cpu_t.guest)
        c.gauge('system_wide.times.guest_nice', cpu_t.guest_nice)
        time.sleep(GRANULARITY)


def cpu_times_percent():
    c = statsd.StatsClient(STATSD_HOST, 8125, prefix=PREFIX + 'system.cpu')
    while True:
        value = psutil.cpu_percent(interval=1)
        c.gauge('system_wide.percent', value)

        cpu_t_percent = psutil.cpu_times_percent(interval=1)
        c.gauge('system_wide.times_percent.user', cpu_t_percent.user)
        c.gauge('system_wide.times_percent.nice', cpu_t_percent.nice)
        c.gauge('system_wide.times_percent.system', cpu_t_percent.system)
        c.gauge('system_wide.times_percent.idle', cpu_t_percent.idle)
        c.gauge('system_wide.times_percent.iowait', cpu_t_percent.iowait)
        c.gauge('system_wide.times_percent.irq', cpu_t_percent.irq)
        c.gauge('system_wide.times_percent.softirq', cpu_t_percent.softirq)
        c.gauge('system_wide.times_percent.steal', cpu_t_percent.steal)
        c.gauge('system_wide.times_percent.guest', cpu_t_percent.guest)
        c.gauge('system_wide.times_percent.guest_nice', cpu_t_percent.guest_nice)
        time.sleep(GRANULARITY)


def memory():
    c = statsd.StatsClient(STATSD_HOST, 8125, prefix=PREFIX + 'system.memory')
    while True:
        swap = psutil.swap_memory()
        c.gauge('swap.total', swap.total)
        c.gauge('swap.used', swap.used)
        c.gauge('swap.free', swap.free)
        c.gauge('swap.percent', swap.percent)

        virtual = psutil.virtual_memory()
        c.gauge('virtual.total', virtual.total)
        c.gauge('virtual.available', virtual.available)
        c.gauge('virtual.used', virtual.used)
        c.gauge('virtual.free', virtual.free)
        c.gauge('virtual.percent', virtual.percent)
        c.gauge('virtual.active', virtual.active)
        c.gauge('virtual.inactive', virtual.inactive)
        c.gauge('virtual.buffers', virtual.buffers)
        c.gauge('virtual.cached', virtual.cached)
        time.sleep(GRANULARITY)


if __name__ == '__main__':
    multiprocessing.Process(target=disk).start()
    multiprocessing.Process(target=cpu_times).start()
    multiprocessing.Process(target=cpu_times_percent).start()
    multiprocessing.Process(target=memory).start()
    multiprocessing.Process(target=network).start()
