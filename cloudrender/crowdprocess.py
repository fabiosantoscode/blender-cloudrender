import requests
import json
from base64 import b64encode
from collections import namedtuple
from threading import Thread
from time import time, sleep
try:
    import queue
except ImportError:
    import Queue as queue
import select
import socket

baseAPIUrl = "https://api.crowdprocess.com/jobs/"


class CrowdProcess(object):

    def __init__(self, username=None, password=None, token=None):
        super(CrowdProcess, self).__init__()
        if (username is None or password is None) and token is None:
            raise Exception("Needs either username and password or token")

        if (username is not None and password is not None):
            c = b64encode(('%s:%s' % (username, password))
                          .encode('latin1')).strip().decode('latin1')
            self._headers = {
                "Authorization": "Basic " + c
            }

        if (token is not None):
            self._headers = {"Authorization": "Token " + token}

    def list_jobs(self):
        res = requests.get(baseAPIUrl, headers=self._headers)
        if res.status_code == requests.codes.ok:
            return res.json()
        else:
            res.raise_for_status()

    def delete_jobs(self):
        res = requests.delete(baseAPIUrl,
                              headers=self._headers)

        if res.status_code != requests.codes.no_content:
            res.raise_for_status()

    def job(self, program=None, bid=1.0, group=None, id=None):
        return Job(self, program=program, bid=bid, group=group, id=id)


class Job(object):

    def __init__(self, CrowdProcess, program=None,
                 bid=1.0, group=None, id=None):
        super(Job, self).__init__()
        self._headers = CrowdProcess._headers
        self._batch_out = {}

        if id is not None:
            self.id = id
        elif program is not None:
            self._create(program, bid, group)
        else:
            raise Exception("needs either a program or a job id as arguments")

    def _create(self, program, bid=1.0, group=None):
        payload = {
            "program": program,
            "bid": bid,
            "group": group
        }

        res = requests.post(baseAPIUrl,
                            data=json.dumps(payload),
                            headers=self._headers)

        if res.status_code != requests.codes.created:
            res.raise_for_status()

        self.id = res.json()["id"]

    def show(self):
        res = requests.get(baseAPIUrl + self.id,
                           headers=self._headers)

        if res.status_code != requests.codes.ok:
            res.raise_for_status()

        return res.json()

    def delete(self):
        res = requests.delete(baseAPIUrl + self.id,
                              headers=self._headers)

        if res.status_code != requests.codes.no_content:
            res.raise_for_status()

    def submit_tasks(self, iterable):
        def genwrapper():
            for n in iterable:
                yield json.dumps(n).encode() + b"\n"

        res = requests.post(baseAPIUrl + self.id + "/tasks",
                            data=genwrapper(),
                            headers=self._headers)

        if res.status_code != requests.codes.created:
            res.raise_for_status()

    def get_results(self):
        res = requests.get(baseAPIUrl + self.id + "/results",
                           stream=True,
                           headers=self._headers)

        if res.status_code != requests.codes.ok:
            res.raise_for_status()

        def gen(iter):
            while True:
                line = res.raw.readline()
                if len(line) == 0:
                    break

                yield json.loads(line.decode())

        return gen(res)

    def get_results_stream(self):
        res = requests.get(baseAPIUrl + self.id + "/results?stream",
                           stream=True,
                           headers=self._headers)

        if res.status_code != requests.codes.ok:
            res.raise_for_status()

        def gen(iter):
            while True:
                line = res.raw.readline()
                if len(line) == 0:
                    break
                yield json.loads(line.decode())

        return gen(res)

    def get_errors(self):
        res = requests.get(baseAPIUrl + self.id + "/errors",
                           stream=True,
                           headers=self._headers)

        if res.status_code != requests.codes.ok:
            res.raise_for_status()

        def gen(iter):
            while True:
                line = res.raw.readline()
                if len(line) is 0:
                    break
                yield json.loads(line.decode())

        return gen(res)

    def get_errors_stream(self):
        res = requests.get(baseAPIUrl + self.id + "/errors?stream",
                           stream=True,
                           headers=self._headers)

        if res.status_code != requests.codes.ok:
            res.raise_for_status()

        def gen(iter):
            while True:
                line = res.raw.readline()
                if len(line) is 0:
                    break
                yield json.loads(line.decode())

        return gen(res)

    def __call__(self, iterable):
        batch = str(time())
        self._batch_out[batch] = 0

        def genwrapper():
            for n in iterable:
                yield n
                self._batch_out[batch] += 1

        results_req = requests.get(baseAPIUrl + self.id + "/results?stream",
                                   stream=True,
                                   headers=self._headers)

        errors_req = requests.get(baseAPIUrl + self.id + "/errors?stream",
                                  stream=True,
                                  headers=self._headers)

        if results_req.status_code != requests.codes.ok:
            results_req.raise_for_status()

        if errors_req.status_code != requests.codes.ok:
            errors_req.raise_for_status()

        results_raw_req = results_req.raw
        errors_raw_req = errors_req.raw
        inputs = [results_raw_req, errors_raw_req]

        results_queue = queue.Queue()

        tasks = Thread(target=self.submit_tasks, args=(genwrapper(),))
        tasks.daemon = True
        tasks.start()

        def get_results_and_errors():
            while True:
                inputready = []
                try:
                    inputready, _,_ = select.select(inputs, [], [], 0.01)
                except select.error:
                    break
                except socket.error:
                    break
                except AttributeError:
                    if results_raw_req.closed:
                        if results_raw_req in inputs:
                            inputs.remove(results_raw_req)
                    if errors_raw_req.closed:
                        if errors_raw_req in inputs:
                            inputs.remove(errors_raw_req)
                    if len(inputs) == 0:
                        raise Exception("results and errors connections were closed unexpectedly")

                for s in inputready:
                    if s == results_raw_req:
                        line = results_raw_req.readline()
                        if len(line) == 0:
                            continue
                        results_queue.put(json.loads(line.decode()))
                        self._batch_out[batch] -= 1

                    if s == errors_raw_req:
                        line = errors_raw_req.readline()
                        if len(line) == 0:
                            continue
                        self._batch_out[batch] -= 1

                if not tasks.is_alive() and self._batch_out[batch] == 0:
                    break


        results_and_errors = Thread(target=get_results_and_errors)
        results_and_errors.daemon = True
        results_and_errors.start()

        def results_gen():
            while results_and_errors.is_alive() or not results_queue.empty():
                sleep(0)
                try:
                    yield results_queue.get(True, 2.5)
                except queue.Empty:
                    continue
                results_queue.task_done()

        Data = namedtuple('Data', 'results, errors')

        return Data(results_gen(), None)
