#!/usr/bin/env python3

import getopt
import getpass
import json
import logging
import os
import signal
import sys
import time
import uuid
from typing import Optional

import requests
from apscheduler.events import JobEvent

from omniscient import scheduler
from omniscient.check import Check
from omniscient.log import get_logger

log = get_logger()
workers_scheduler = scheduler.Scheduler()

config = {}
url = ""


def get_uuid() -> str:
    """
    Generate a UUID for this client
    """

    username = getpass.getuser()
    node = hex(uuid.getnode())
    urn = f"urn:node:{node}:user:{username}"

    return str(uuid.uuid3(uuid.NAMESPACE_DNS, urn))


def read_config(url: str) -> dict:
    """
    Read configuration from server.
    """

    config = {}
    my_uuid = get_uuid()

    log.debug(f"Worker have UUID {my_uuid}")

    try:
        log.debug("Fetching configuration from " + url + "?uuid=" + my_uuid)
        res = requests.get(url + "?uuid=" + my_uuid)
    except Exception:
        log.error("Could not reach endpoint " + url)
        return config

    if res.status_code != 200:
        log.debug(f"Server responded with {res.status_code}:\n" + res.text)
        return config

    try:
        if "data" in res.json():
            config = res.json()["data"]
        elif "error" in res.json():
            log.error("Configuration not found for client")
        else:
            log.error("Unknown error when fetching configuration")
    except Exception:
        log.error("Failed to parse JSON from server")

    return config


def callhome(result: dict) -> None:
    """
    Send result to server.
    """

    try:
        res = requests.post(url + "/callhome?uuid=" + get_uuid(), json=result)
        log.debug("Sent result to server:")
        indented = json.dumps(result, indent=4)
        log.debug("\n" + indented)

        if res.status_code != 200:
            log.error(f"Server responded with {res.status_code}")
        else:
            log.debug("Server responded with 200 OK")
    except Exception as e:
        log.error(f"Failed to post result to {url}: {e}")


def check_error(event: JobEvent) -> None:
    """
    Send error to server.
    """

    result = [
        {
            "measurement": event.job_id,
            "tags": {"uuid": get_uuid()},
            "fields": {"success": False},
        }
    ]

    callhome(result)


def check_success(event: JobEvent) -> None:
    """
    Send result to server.
    """

    try:
        resultdata = event.retval.result.decode().rstrip()
    except AttributeError:
        return

    try:
        float(resultdata)
    except ValueError:
        pass
    else:
        resultdata = float(resultdata)

    result = [
        {
            "measurement": event.job_id,
            "tags": {"uuid": get_uuid()},
            "fields": {"success": True, "result": resultdata},
        }
    ]

    callhome(result)


def start_checks(config: dict) -> None:
    """
    Start all checks in configuration.
    """

    for test in config:
        interval = test["interval"]
        name = test["name"]
        test["url"] = url

        print(f"Started check {name} with interval {interval}")

        log.debug(f"Starting new job {name} with interval {interval}")

        workers_scheduler.add(Check, name, interval=interval, maxruns=-1, config=test)

    workers_scheduler.start()


def stop_checks() -> None:
    """
    Stop all checks.
    """

    for job in workers_scheduler.get_jobs():
        log.debug(f"Stopping job {job}")
        workers_scheduler.delete_job(job)


def main() -> None:
    """
    Main function.
    """

    old_config = {}
    endpoint = url + "/config"
    callhome_interval = 30

    workers_scheduler.add_error_listener(check_error)
    workers_scheduler.add_success_listener(check_success)

    while True:
        config = read_config(endpoint)

        if config == {}:
            log.debug("Didn't receive a configuration")
            time.sleep(5)
            continue

        for item in old_config:
            if "url" in item:
                del item["url"]

        for item in config:
            if "url" in item:
                del item["url"]

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


def kill(pidfile: str) -> None:
    """
    Kill daemon.
    """

    try:
        with open(pidfile) as fd:
            pid = int(fd.read())
            log.info(f"Killing daemon with pid {pid}")
            os.kill(pid, signal.SIGTERM)
    except Exception as e:
        log.error(f"Failed to kill daemon: {e}")


def usage(err: Optional[str] = "") -> None:
    """
    Print usage.
    """

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

    sys.exit(0)


if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "du:hU")
    except getopt.GetoptError as e:
        usage(err=e)

    for opt, arg in opts:
        if opt == "-d":
            log.setLevel(logging.DEBUG)
        elif opt == "-u":
            url = arg
        elif opt == "-U":
            print(get_uuid())
            sys.exit(0)
        elif "-h":
            usage()
        else:
            usage()

    if "http" not in url:
        usage()

    main()
