import sys
import time
from collections import defaultdict

import arrow
import redis
import requests
from loguru import logger

the_time = int(arrow.utcnow().timestamp())
filename = f"online_status_{the_time}.log"

wio_to_str = defaultdict(lambda: 'unknown')
wio_to_str.update({
    '1': "online",
    '3': "invisible",
    '4': "offline",
    None: "offline"
})


def write_header():
    with open(filename, "w") as f:
        header = "time (utc) \t solr online \t solr visible \t wio online \t wio status \t wio_api (last 30m)".expandtabs(18)
        f.write(header + "\n")
        f.write("-" * len(header) + "\n")


def log_values(solr_online, solr_visible, wio_online, wio_status, wio_api_value):
    current_time = arrow.utcnow().strftime("%Y-%m-%d %H:%M:%S")[:-3]
    with open(filename, "a") as f:
        f.write(f"{current_time} \t {solr_online} \t {solr_visible} \t {wio_online} \t {wio_status} ({wio_to_str[wio_status]}) \t {wio_api_value}\n".expandtabs(18))


def check_solr(solr_url, user_id):
    response = requests.post(
        f"http://{solr_url}",
        headers={"accept": "application/json", "Content-Type": "application/json"},
        data=f'{{"q":"id:{user_id}"}}'
    )

    response.raise_for_status()
    data = response.json()

    return (
        data["docs"].get("1", dict()).get("is_online", "<missing>"),
        data["docs"].get("1", dict()).get("is_visible", "<missing>")
    )


def check_wio_api(wio_api_url, user_id):
    recently = int(arrow.utcnow().shift(minutes=-30).timestamp())
    response = requests.get(
        f"http://{wio_api_url}/api/v1/status-updates-since/{recently}",
        headers={"accept": "application/json", "Content-Type": "application/json"}
    )

    response.raise_for_status()
    data = response.json()

    for user in data:
        if str(user["user_id"]) == user_id:
            return user["status"]

    return "<missing>"


def check_wio(r_client, user_id):
    is_online = r_client.sismember("users:multicast", user_id)
    is_visible = r_client.get(f"user:status:{user_id}")

    return is_online, is_visible


def check_status(r_client, user_id, solr_url, wio_api_url):
    try:
        solr_online, solr_visible = check_solr(solr_url, user_id)
    except Exception as e:
        logger.error("could not check solr: {str(e)}")
        logger.exception(e)
        solr_online = "<error>"
        solr_visible = "<error>"

    try:
        wio_online, wio_status = check_wio(r_client, user_id)
    except Exception as e:
        logger.error("could not check wio: {str(e)}")
        logger.exception(e)
        wio_online = "<error>"
        wio_status = "<error>"

    try:
        wio_api_value = check_wio_api(wio_api_url, user_id)
    except Exception as e:
        logger.error("could not check wio api: {str(e)}")
        logger.exception(e)
        wio_api_value = "<error>"

    log_values(solr_online, solr_visible, wio_online, wio_status, wio_api_value)


def monitor(user_id, solr_url, wio_url, wio_api_url):
    r_host, r_port, r_db = wio_url.split(":")
    r_client = redis.StrictRedis(host=r_host, port=int(r_port), db=int(r_db), decode_responses=True)

    write_header()
    while True:
        try:
            check_status(r_client, user_id, solr_url, wio_api_url)
            time.sleep(5 * 60)
        except InterruptedError:
            break


def run():
    user_id = sys.argv[1]
    solr_url = sys.argv[2]
    wio_url = sys.argv[3]
    wio_api_url = sys.argv[4]

    monitor(user_id, solr_url, wio_url, wio_api_url)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 poll_online_status.py <user_id> <solr_url> <wio_url> <wio_api_url>")
        sys.exit(1)

    run()
