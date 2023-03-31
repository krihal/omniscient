import os
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests
import yaml

import scheduler

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

        if not os.path.exists(check):
            try:
                res = requests.get(sys.argv[1] + "/checks/" + check)
                with open(filename, "wb") as fd:
                    fd.write(res.content)
                os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            except Exception as e:
                print("Failed to write new check: " + e)

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


def read_config(url):
    res = requests.get(url)

    try:
        config = yaml.safe_load(res.json()["yaml"])
    except yaml.YAMLError as e:
        print(e)
    except yaml.parser.ParserError as e:
        print(e)

    return config


def callhome(result):
    url = config["callhome"]["url"]
    token = config["callhome"]["token"]

    try:
        requests.post(url, json=result)
    except Exception as e:
        print(f"Failed to post result to {url}: {e}")


def check_error(event):
    result = [{
        "measurement": event.job_id,
        "tags": {
            "hostname": os.uname().nodename
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
            "hostname": os.uname().nodename
        },
        "fields": {
            "success": True,
            "result": resultdata
        }
    }]

    callhome(result)


def start_checks(config):
    for check in config["checks"]:
        check_config = config["checks"][check]
        interval = check_config["interval"]
        name = check_config["name"]

        workers_scheduler.add(
            Check, name, interval=interval, maxruns=-1, config=check_config)

    workers_scheduler.add_error_listener(check_error)
    workers_scheduler.add_success_listener(check_success)
    workers_scheduler.start()


def stop_checks():
    for job in workers_scheduler.get_jobs():
        workers_scheduler.delete_job(job)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]} <Configuration URL>")
        sys.exit(1)

    old_config = {}

    while True:
        config = read_config(sys.argv[1] + "/config")

        if config != old_config:
            stop_checks()
            start_checks(config)

            old_config = config.copy()

        time.sleep(1)
