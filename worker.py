import getopt
import getpass
import hashlib
import json
import logging
import os
import signal
import stat
import subprocess
import sys
import time
import uuid

import requests
from daemonize import Daemonize

from omniscient import scheduler
from omniscient.check import Check
from omniscient.log import get_logger
from omniscient.signher import verify_file

log = get_logger()
workers_scheduler = scheduler.Scheduler()
config = {}
url = ""


def get_uuid():
    username = getpass.getuser()
    node = hex(uuid.getnode())
    urn = 'urn:node:%s:user:%s' % (node, username)
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, urn))


def read_config(url):
    config = {}
    my_uuid = get_uuid()

    log.debug(f"Worker have UUID={my_uuid}")

    try:
        res = requests.get(url + "?uuid=" + my_uuid)

        if "data" in res.json():
            config = res.json()["data"]
        elif "error" in res.json():
            log.error("Configuration not found for client")
    except requests.exceptions.ConnectionError:
        log.error("Could not reach endpoint " + url)

    return config


def callhome(result):
    try:
        res = requests.post(url + "/callhome?uuid=" + get_uuid(), json=result)
        log.debug("Sent result to server:")
        indented = json.dumps(result, indent=4)
        log.debug("\n" + indented)
        log.debug(f"Server responded with {res.status_code}")
    except Exception as e:
        log.error(f"Failed to post result to {url}: {e}")


def check_error(event):
    result = [{
        "measurement": event.job_id,
        "tags": {
            "uuid": get_uuid()
        },
        "fields": {
            "success": False
        }
    }]

    callhome(result)


def check_success(event):
    resultdata = event.retval.result.decode().rstrip()

    try:
        float(resultdata)
    except ValueError:
        pass
    else:
        resultdata = float(resultdata)

    result = [{
        "measurement": event.job_id,
        "tags": {
            "uuid": get_uuid()
        },
        "fields": {
            "success": True,
            "result": resultdata
        }
    }]

    callhome(result)


def start_checks(config):
    for test in config:
        interval = test["interval"]
        name = test["name"]
        test["url"] = url

        log.debug(f"Starting new job {name} with interval {interval}")

        workers_scheduler.add(
            Check, name, interval=interval, maxruns=-1, config=test)

        workers_scheduler.add_error_listener(check_error)
        workers_scheduler.add_success_listener(check_success)
        workers_scheduler.start()


def stop_checks():
    for job in workers_scheduler.get_jobs():
        log.debug(f"Stopping job {job}")
        workers_scheduler.delete_job(job)


def main():
    old_config = {}
    endpoint = url + "/config"
    callhome_interval = 30

    while True:
        config = read_config(endpoint)

        if config == {}:
            log.debug("Didn't receive a configuration")
            time.sleep(5)
            continue

        if config != old_config:
            for test in config:
                log.info("Scheduling test:")
                log.info("  Name:     " + test["name"])
                log.info("  Interval: " + str(test["interval"]))
                log.info("  Retries:  " + str(test["retries"]))
                log.info("  Check:    " + test["check"])
                log.info("")

            log.info("Configuration change!")
            stop_checks()
            start_checks(config)
            old_config = config.copy()

        log.info(f"Will call home again in {callhome_interval} seconds")

        time.sleep(callhome_interval)


def kill(pidfile):
    try:
        with open(pidfile) as fd:
            pid = int(fd.read())
            log.info(f"Killing daemon with pid {pid}")
            os.kill(pid, signal.SIGTERM)
    except Exception as e:
        log.error(f"Failed to kill daemon: {e}")


def usage(err=""):
    name = sys.argv[0]

    if err != "":
        print(f"{name}: {err}")
        print("")
        sys.exit(0)

    print()
    print(f"Client UUID: {get_uuid()}")
    print()
    print(f"{name} -p <pidfile> -d -F")
    print("  -U              Print UUID and quit")
    print("  -u              URL to server")
    print("  -d              Enable debug")
    print("  -p <pidfile>    Path to pid file")
    print("  -f              Stay in foreground")
    print("  -z              Kill running instance")

    sys.exit(0)


if __name__ == "__main__":
    foreground = False
    pidfile = "/tmp/worker.pid"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:dfzu:hU")
    except getopt.GetoptError as e:
        usage(err=e)

    for opt, arg in opts:
        if opt == "-d":
            log.setLevel(logging.DEBUG)
        elif opt == "-p":
            pidfile = arg
        elif opt == "-f":
            foreground = True
        elif opt == "-u":
            url = arg
        elif opt == "-z":
            kill(pidfile)
        elif opt == "-U":
            print(get_uuid())
            sys.exit(0)
        elif "-h":
            usage()
        else:
            usage()

    if "http" not in url:
        usage()

    daemon = Daemonize(app=__name__, pid=pidfile, action=main,
                       logger=log,
                       foreground=foreground,
                       verbose=True,
                       chdir=os.getcwd())
    daemon.start()
