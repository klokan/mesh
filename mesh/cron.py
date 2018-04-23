import re

from schedule import Scheduler as BaseScheduler
from signal import signal, SIGINT, SIGTERM
from time import sleep


class CRON:

    pattern = re.compile(r'every (\d+ )?(\w+)(?: at (\d\d:\d\d))?$')

    def __init__(self, mesh):
        self.scheduler = Scheduler(mesh)
        self.logger = mesh.init_logger()
        self.running = False

    def task(self, when):
        def decorator(func):
            match = self.pattern.match(when)
            interval = match.group(1)
            if interval is not None:
                job = self.scheduler.every(int(interval))
            else:
                job = self.scheduler.every()
            getattr(job, match.group(2))
            time_str = match.group(3)
            if time_str is not None:
                job.at(time_str)
            job.do(func)
            return func
        return decorator

    def run(self):
        self.running = True
        signal(SIGINT, self.stop)
        signal(SIGTERM, self.stop)

        while self.running:
            self.scheduler.run_pending()
            sleep(self.scheduler.idle_seconds)

    def stop(self, signo=None, frame=None):
        self.running = False


class Scheduler(BaseScheduler):

    def __init__(self, mesh):
        super().__init__()
        self.mesh = mesh

    def _run_job(self, job):
        context = self.mesh.make_context(
            method='CRON',
            path=job.job_func.__name__)
        with context:
            try:
                super()._run_job(job)
            except Exception:
                self.logger.exception('Exception occured')
