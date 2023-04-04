import getpass
import os
import stat
import subprocess
import sys
import time
import uuid

import requests

import scheduler
from log import get_logger

log = get_logger()
workers_scheduler = scheduler.Scheduler()
config = {}


class CheckError(Exception):
    pass


class Check():
    def __init__(self, config):
        self.__config = config
        self.__name = config["name"]
        self.__retries = config["retries"]
        self.__process = ["./scripts/" + config["check"]]
        self.__process.extend(config["args"].split(" "))

        self.__download()
        self.result = self.__start()

    def __download(self):
        check = [self.__config["check"]][0]
        filename = "scripts/" + check
        url = sys.argv[1] + "/checks/" + check

        if not os.path.exists(check):
            try:
                res = requests.get(url)
                with open(filename, "wb") as fd:
                    fd.write(res.content)
                os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            except requests.exceptions.ConnectionError:
                log.error("Failed to download check from " + url)
            except Exception as e:
                log.error("Failed to write new check: " + e)

    def __start(self):
        fail = True
        for retry in range(self.__retries):
            res = subprocess.run(
                self.__process, shell=True, capture_output=True)
            if res.returncode == 0:
                fail = False
                break
            time.sleep(3)

        if fail:
            raise CheckError(
                f"Check {self.__name} failed after {self.__retries} retries")

        return res.stdout


def get_uuid():
    username = getpass.getuser()
    node = hex(uuid.getnode())
    urn = 'urn:node:%s:user:%s' % (node, username)
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, urn))


def read_config(url):
    config = {}

    try:
        res = requests.get(url + "?uuid=" + get_uuid())

        if "data" in res.json():
            config = res.json()["data"]
        elif "error" in res.json():
            log.error("Configuration not found for client")
    except requests.exceptions.ConnectionError:
        log.error("Could not reach endpoint " + url)

    return config


def callhome(result):
    url = sys.argv[1]

    try:
        requests.post(url + "/callhome?uuid=" + get_uuid(), json=result)
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

        workers_scheduler.add(
            Check, name, interval=interval, maxruns=-1, config=test)

        workers_scheduler.add_error_listener(check_error)
        workers_scheduler.add_success_listener(check_success)
        workers_scheduler.start()


def stop_checks():
    for job in workers_scheduler.get_jobs():
        workers_scheduler.delete_job(job)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        log.info(f"{sys.argv[0]} <Configuration URL>")
        sys.exit(1)

    old_config = {}
    endpoint = sys.argv[1] + "/config"

    while True:
        config = read_config(endpoint)

        if config == {}:
            time.sleep(5)
            continue

        if config != old_config:
            log.info("Configuration change!")
            stop_checks()
            start_checks(config)
            old_config = config.copy()

        time.sleep(1)
