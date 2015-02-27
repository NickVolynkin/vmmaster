# coding: utf-8
from flask import current_app

from ..core.platforms import Platforms
from ..core.exceptions import SessionException
from ..core.session_queue import q
from ..core.virtual_machine.virtual_machines_pool import pool


def get_session(session_id):
    try:
        session = current_app.sessions.get_session(session_id)
    except SessionException:
        session = None
    return session


def get_sessions():
    sessions_list = list()
    for session_id, session in current_app.sessions:
        sessions_list.append(session.info)
    return sessions_list


def get_platforms():
    return list(Platforms.platforms.keys())


def get_queue():
    return [job.dc for job in q]


def get_pool():
    return pool.info