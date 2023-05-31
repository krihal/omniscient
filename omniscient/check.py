import hashlib
import os
import stat
import subprocess
import sys
import time

import requests

from omniscient.log import get_logger
from omniscient.signher import verify_file

log = get_logger()


class CheckError(Exception):
    pass


class Check():
    def __init__(self, config):
        self.__config = config
        self.__name = config["name"]
        self.__retries = config["retries"]
        self.__scripts_path = "/tmp/scripts/"

        if not os.path.exists(self.__scripts_path):
            log.debug("Scripts directory missing, creating")
            os.mkdir(self.__scripts_path)
        else:
            log.debug("Scripts directory exists")

        self.__filename = self.__scripts_path + config["check"]

        log.debug(f"Check filename: {self.__filename}")

        self.__rhash = self.__get_remote_hash()
        self.__lhash = self.__get_hash()

        if self.__lhash is None or self.__lhash != self.__rhash:
            log.info("File hash differ:")
            log.info(f"   local={self.__lhash}")
            log.info(f"   remote={self.__rhash}")

            if self.__download():
                log.info("Downloaded new check")
            else:
                log.info("Failed to download new check")
                self.__filename = None
                self.__process = None

        if self.__filename is not None:
            self.__process = [self.__filename]
        else:
            self.__process = []

        self.__process.extend(config["args"].split(" "))

        self.result = self.__start()

    def __get_remote_hash(self):
        return self.__config["hash"]

    def __get_hash(self):
        if not os.path.exists(self.__filename):
            return None
        with open(self.__filename, "rb") as fd:
            return hashlib.sha256(fd.read()).hexdigest()

    def __download(self):
        check = [self.__config["check"]][0]
        filename = self.__scripts_path + check
        downloadurl = self.__config["url"] + "/checks/" + check

        log.info(f"Downloading script {filename}")

        if not os.path.exists(check):
            try:
                res = requests.get(downloadurl)

                if not verify_file(res.content, filename, "certs/public.crt"):
                    log.error("File signature could not be verified")
                    return False
                else:
                    log.info(f"File signature of {filename} verified")
                os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            except requests.exceptions.ConnectionError:
                log.error("Failed to download check from " + downloadurl)
            except Exception as e:
                log.error("Failed to write new check: " + e)

        return True

    def __start(self):
        if self.__process == [] or self.__process == [''] or self.__process is None:
            raise CheckError("No process to run!")

        fail = True
        for retry in range(self.__retries):
            res = subprocess.run(
                self.__process, shell=False, capture_output=True)
            if res.returncode == 0:
                fail = False
                break
            time.sleep(3)

        if fail:
            raise CheckError(
                f"Check {self.__name} failed after {self.__retries} retries: {res.stdout}, {res.stderr}")

        return res.stdout
