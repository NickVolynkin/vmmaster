# coding: utf-8

import time
import ujson
import logging
from datetime import datetime
from core.exceptions import TimeoutException


log = logging.getLogger(__name__)


class FakeSession(object):
    user_id = 1
    endpoint_ip = ""
    endpoint_name = ""
    name = ""
    dc = ""
    selenium_session = "123qwe"
    take_screenshot = False
    run_script = ""
    created = time.time()
    modified = time.time()
    deleted = ""
    selenium_log = ""

    # State
    status = "waiting"
    reason = ""
    error = ""
    timeouted = False
    closed = False

    # Relationships
    session_steps = []

    def set_user(self, username):
        self.user = username

    def save(self):
        pass

    def add_session_step(self, *args, **kwargs):
        pass

    def __init__(self, name=None, dc=None, id=None):
        if not id:
            self.id = 1
        else:
            self.id = id

        if name:
            self.name = name

        if dc:
            self.dc = ujson.dumps(dc)
            if dc.get("name", None) and not self.name:
                self.name = dc["name"]
            if dc.get("user", None):
                self.set_user(dc["user"])
            if dc.get("takeScreenshot", None):
                self.take_screenshot = True
            if dc.get("runScript", None):
                self.run_script = ujson.dumps(dc["runScript"])
            if dc.get("platform", None):
                self.platform = dc.get('platform')

        if not self.name:
            self.name = "Unnamed session " + str(self.id)


class Session(FakeSession):
    endpoint = None
    current_log_step = None
    vnc_helper = None
    take_screencast = None
    is_active = True

    def __init__(self, name=None, dc=None, id=None):
        super(Session, self).__init__(name, dc, id)

    @property
    def inactivity(self):
        return (datetime.now() - self.modified).total_seconds()

    @property
    def duration(self):
        return (datetime.now() - self.created).total_seconds()

    @property
    def info(self):
        stat = {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "platform": self.platform,
            "duration": self.duration,
            "inactivity": self.inactivity,
        }

        if self.endpoint_name:
            stat["endpoint"] = {
                "ip": self.endpoint_ip,
                "name": self.endpoint_name
            }
        return stat

    async def close(self, reason=None):
        self.closed = True
        if reason:
            self.reason = "%s" % reason
        self.deleted = datetime.now()
        await self.save()

        log.info("Session %s closed. %s" % (self.id, self.reason))

    async def succeed(self):
        self.status = "succeed"
        await self.close()

    async def failed(self, tb=None, reason=None):
        if self.closed:
            log.warn("Session %s already closed with reason %s. "
                     "In this method call was tb='%s' and reason='%s'"
                     % (self.id, self.reason, tb, reason))
            return

        self.status = "failed"
        self.error = tb
        await self.close(reason)

    async def run(self):
        self.modified = datetime.now()
        self.status = "running"
        log.info("Session %s starting on %s (%s)." %
                 (self.id, self.endpoint_name, self.endpoint_ip))

    async def timeout(self):
        self.timeouted = True
        await self.failed(reason="Session timeout. No activity since %s" % str(self.modified))

    async def make_request(self, port, request, queue=None):
        headers = dict(request.headers)
        if request.headers.get("Host"):
            del headers["Host"]

        parameters = {
            "vmmaster_session": int(self.id),
            "platform": "ubuntu-14.04-x64",
            "method": request.method,
            "port": port,
            "url": request.path,
            "headers": dict(headers),
            "data": request.content
        }
        if not queue:
            queue = "vmmaster_session_%s" % self.id

        parameters = ujson.dumps(parameters)
        response = await request.app.queue_producer.add_msg_to_queue_with_response(queue, parameters)
        if response:
            response = ujson.loads(response)
            return response.get("status"), response.get("headers", "{}"), response.get("content", "{}")
        else:
            raise TimeoutException("Response is not received in %s seconds"
                                   % request.app.cfg.BACKEND_REQUEST_TIMEOUT)
