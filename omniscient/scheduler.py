import fcntl
from datetime import datetime
from typing import Callable, Optional

import flock
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

from omniscient.log import get_logger

log = get_logger()


class JobError(Exception):
    def __init__(self, message):
        log.error(message)


class Scheduler(object):
    def __init__(self, nr_threads: Optional[int] = 100,
                 lockfile: Optional[str] = "/tmp/scheduler.lock") -> None:
        self.__scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(nr_threads)},
            jobstores={"default": MemoryJobStore()},
            job_defaults={},
            timezone=utc,
        )

        self.lockfile = lockfile
        self.started = False
        self.job_id = 0
        self.jobstore = dict()
        self.jobs = []

    def __lock(self) -> Optional[bool]:
        """
        Locks the scheduler to prevent multiple instances from running.
        """

        try:
            self.lockfp = open(self.lockfile, "w")
            fcntl.lockf(self.lockfp, flock.LOCK_EX)
        except IOError:
            return None

        return True

    def __unlock(self) -> bool:
        """
        Unlocks the scheduler.
        """

        if self.lockfp.writable():
            try:
                fcntl.lockf(self.lockfp, fcntl.LOCK_UN)
            except IOError:
                return False
            return True

        return False

    def __launcher(self, func: Callable, **kwargs: dict) -> None:
        """
        Launches the function with the given arguments.
        """

        job_id = kwargs["job_id"]
        retval = None
        self.jobstore[job_id]["nr_runs"] += 1

        if "maxruns" in kwargs:
            if self.jobstore[job_id]["nr_runs"] >= kwargs["maxruns"]:
                if kwargs["maxruns"] != 0:
                    log.info(f"Reached max runs, removing job {job_id}.")
                    self.__scheduler.remove_job(job_id)
            del kwargs["maxruns"]
        del kwargs["job_id"]
        retval = func(**kwargs)

        return retval

    def start(self) -> Optional[bool]:
        """
        Starts the scheduler.
        """

        if not self.__lock():
            log.error("Could not acquire lock")
            return None

        if self.started:
            log.debug("Scheduler already started")
            return None

        self.started = True

        log.info("Starting scheduler")

        return self.__scheduler.start()

    def stop(self) -> Optional[bool]:
        """
        Stops the scheduler.
        """

        if self.started:
            self.started = False
        return self.__scheduler.shutdown()

    def add(self, func: Callable, job_id: Optional[str] = "",
            comment: Optional[str] = "",
            timeout: Optional[int] = 120,
            interval: Optional[int] = 60,
            maxruns: Optional[int] = 1,
            starttime: Optional[str] = None, **kwargs: dict) -> str:
        """
        Adds a job to the scheduler.
        """

        log.info(f"Scheduling recurrent job {job_id}")

        if job_id == "":
            self.job_id += 1
            kwargs["job_id"] = str(self.job_id)
        else:
            job_id = job_id.replace("-", "_")
            job_id = job_id.replace(".", "_")
            job_id = job_id.replace(":", "_")
            job_id = job_id.replace(" ", "_")

            if job_id in self.jobstore:
                raise JobError("Job already exists")
            kwargs["job_id"] = str(job_id)

        kwargs["func"] = func
        kwargs["maxruns"] = maxruns + 1
        job_id = kwargs["job_id"]

        if not starttime:
            starttime = datetime.utcnow()

        self.jobstore[job_id] = {"nr_runs": 0}
        self.__scheduler.add_job(self.__launcher, id=job_id,
                                 trigger="interval",
                                 misfire_grace_time=timeout,
                                 seconds=interval,
                                 next_run_time=starttime,
                                 kwargs=kwargs)

        return job_id

    def add_error_listener(self, func: Callable) -> None:
        """
        Adds a listener for job errors.
        """

        self.__scheduler.add_listener(func, EVENT_JOB_ERROR)

    def add_success_listener(self, func: Callable) -> None:
        """
        Adds a listener for job success.
        """

        self.__scheduler.add_listener(func, EVENT_JOB_EXECUTED)

    def delete_job(self, job_id: str) -> None:
        """
        Deletes a job from the scheduler.
        """

        self.__scheduler.remove_job(job_id)
        del self.jobstore[job_id]
        log.info(f"Job {job_id} removed from scheduler.")

    def get_jobs(self) -> list:
        """
        Returns a list of jobs.
        """

        jobs = list()
        for key in self.jobstore.keys():
            jobs.append(key)
        return jobs


def test_job(**kwargs):
    print(kwargs)


if __name__ == "__main__":
    s = Scheduler()
    s.add(test_job, "test_1", interval=2, maxruns=20, jobb="test_1")
    s.add(test_job, "test_2", interval=2, maxruns=20, jobb="test_2")

    s.start()

    for job in s.get_jobs():
        s.delete_job(job)

    s.add(test_job, "test_1", interval=2, maxruns=20, jobb="test_1")
    s.add(test_job, "test_2", interval=2, maxruns=20, jobb="test_2")

    while True:
        pass
