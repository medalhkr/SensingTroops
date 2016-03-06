#!/usr/bin/python3
# -*- coding: utf-8 -*-


import sys
import threading
import requests
import socket
from functools import wraps
from common import json_input, generate_info, SergeantInfo, PrivateInfo
from flask import Flask, jsonify, request
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)


class Sergeant(object):
    def __init__(self, name, addr, port):
        self.info = generate_info(SergeantInfo, name=name, addr=addr, port=port)
        self._superior_ep = ''

        self._cache = []
        self._pvt_list = {}
        self.job_list = {
            'report': None,
            'command': [],
        }
        self.job_wait_events = {
            'report': None,
            'command': [],
        }

    # soldier functions

    def join(self, addr, port):
        """
        指定された上官に入隊申請を行う
        :param str addr: 上官のIPアドレス
        :param str port: 上官のポート番号
        :rtype: str
        :return: id
        """
        self._superior_ep = addr + ':' + port
        logger.info('join into the captain: {0}'.format(self._superior_ep))

        path = 'http://{0}/captain/soldiers'.format(self._superior_ep)
        requests.post(path, json=self.info._asdict()).json()

        return True

    def set_report(self, report):
        # 既存のreportスレッドを消す
        if self.job_wait_events['report'] is not None:
            self.job_wait_events['report'].set()
        self.job_wait_events['report'] = None

        # TODO: reportが受理可能なものであるかのチェック
        event = threading.Event()
        t = threading.Thread(target=self._report_thread, args=(report, event))
        t.start()
        self.job_wait_events['report'] = event
        self.job_list['report'] = report

        logger.info('accepted new job: report')
        logger.debug('new job: {0}'.format(str(report)))
        return report

    def set_commands(self, command_list):
        if not isinstance(command_list, list):
            command_list = [command_list]

        # 既存のcommandスレッドを消す
        map(lambda w: w.set(), self.job_wait_events['command'])
        self.job_wait_events['command'] = []

        accepted = []
        for command in command_list:
            # TODO: commandが受理可能なものであるかのチェック
            event = threading.Event()
            t = threading.Thread(target=self._command_thread,
                                 args=(command, event))
            t.start()
            self.job_wait_events['command'].append(event)
            accepted.append(command)

        logger.info('accepted new jobs: command')
        logger.debug('new jobs: {0}'.format(str(accepted)))
        self.job_list['command'] = accepted
        return accepted

    def _command_thread(self, command, event):
        # oneshotなcommandのみ暫定実装. eventはスルー
        target = []
        if command['target'] == 'all':
            target = self.get_pvt_list()
        order = command['order']

        for pvt in [self._pvt_list[pvt_id] for pvt_id in target]:
            path = 'http://{0}:{1}/private/order'.\
                    format(pvt['addr'], pvt['port'])
            requests.put(path, json={'orders': order})

    def _report_thread(self, command, event):
        interval = command['interval']
        # filter = command['filter']
        # encoding = command['encoding']

        # if event is set, exit the loop
        while not event.wait(timeout=interval):
            path = 'http://{0}/captain/soldiers/{1}/report'.\
                    format(self._superior_ep, self.info.id)
            requests.post(path, json=self._cache)
            self._cache = []

    # superior functions

    def check_pvt_exist(self, pvt_id):
        return pvt_id in self._pvt_list

    def accept_work(self, pvt_id, work):
        if pvt_id not in self._pvt_list:
            raise KeyError
        self._cache.append({'pvt_id': pvt_id, 'work': work})
        logger.info('accept work from pvt: {0}'.format(pvt_id))

    def accept_pvt(self, info):
        self._pvt_list[info.id] = info
        logger.info('accept a new private: {0}, {1}'.format(info.name, info.id))
        return info

    def get_pvt_info(self, pvt_id):
        return self._pvt_list[pvt_id]

    def get_pvt_list(self):
        return list(self._pvt_list.keys())


# REST interface ---------------------------------------------------------------

server = Flask(__name__)
url_prefix = '/sergeant'


# 自身の情報を返す
@server.route(url_prefix, methods=['GET'])
def get_info():
    return jsonify(result='success', info=app.info._asdict()), 200


@server.route(url_prefix + '/cache', methods=['GET'])
def dev_cache():
    return jsonify(result='success', cache=app._cache)


@server.route(url_prefix + '/job/report', methods=['GET', 'PUT'])
@json_input
def setjob_report():
    report = None
    if request.method == 'GET':
        report = app.job_list['report']
    elif request.method == 'PUT':
        input = request.json['report_job']
        report = app.set_report(input)

    return jsonify(result='success', report_job=report), 200


@server.route(url_prefix + '/job/command', methods=['GET', 'PUT'])
@json_input
def setjob_command():
    commands = []
    if request.method == 'GET':
        commands = app.job_list['command']
    elif request.method == 'PUT':
        input = request.json['command_jobs']
        commands = app.set_commands(input)

    return jsonify(result='success', command_jobs=commands), 200


@server.route(url_prefix + '/soldiers', methods=['GET', 'POST'])
@json_input
def soldiers():
    if request.method == 'GET':
        res = app.get_pvt_list()
        return jsonify(result='success', pvt_list=res)
    elif request.method == 'POST':
        res = app.accept_pvt(PrivateInfo(**request.json))
        return jsonify(result='success', accepted=res._asdict())


def access_private(f):
    """
    個別のpvtにアクセスするための存在チェック用デコレータ
    """
    @wraps(f)
    def check_pvt(pvt_id, *args, **kwargs):
        if not app.check_pvt_exist(pvt_id):
            return jsonify(result='failed',
                           msg='the pvt is not my soldier'), 404
        return f(pvt_id, *args, **kwargs)
    return check_pvt


@server.route(url_prefix + '/soldiers/<pvt_id>', methods=['GET'])
@access_private
def pvt_info(pvt_id):
    res = app.get_pvt_info(pvt_id)
    return jsonify(res._asdict())


@server.route(url_prefix + '/soldiers/<pvt_id>/work', methods=['POST'])
@access_private
@json_input
def pvt_work(pvt_id):
    app.accept_work(pvt_id, request.json)
    return jsonify(result='success')


# entry point ------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) == 4:
        self_port = int(sys.argv[1])
        su_addr = sys.argv[2]
        su_port = sys.argv[3]
    else:
        logger.error('superior addr/port required')
        sys.exit()

    # FIXME: この方法だと環境によっては'127.0.0.1'が取得されるらしい
    addr = socket.gethostbyname(socket.gethostname())

    app = Sergeant('sgt-http', addr, self_port)
    app.join(su_addr, su_port)
    server.debug = True
    server.run(host='0.0.0.0', port=self_port,
                use_debugger=True, use_reloader=False)
