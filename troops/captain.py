#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import requests
import json
import copy
from functools import wraps
from flask_cors import cross_origin
from common import json_input, generate_info, SergeantInfo, CaptainInfo
from flask import Flask, jsonify, render_template, request
from flask_swagger import swagger
from logging import getLogger, StreamHandler, DEBUG
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)

# client = pymongo.MongoClient(host='192.168.0.21', port=27017)
# self.coll = client.test.tmp
# self.coll.insert_many(data)


class Captain(object):
    
    def __init__(self, name, addr, port):
        self.info = generate_info(CaptainInfo, name=name, addr=addr, port=port)
        self._cache = []
        self._sgt_list = {}

    def check_sgt_exist(self, sgt_id):
        return sgt_id in self._sgt_list

    def accept_report(self, sgt_id, report):
        if sgt_id not in self._sgt_list:
            raise KeyError
        self._cache.append({'sgt_id': sgt_id, 'report': report})
        logger.info('accept work from pvt: {0}'.format(sgt_id))

    def accept_sgt(self, info):
        id = info['id']

        self._sgt_list[id] = info
        logger.info('accept a new sergeant: {0}, {1}'.format(info['name'], id))
        return info

    def get_sgt_info(self, sgt_id):
        info = self._sgt_list[sgt_id]  # this may raise KeyError
        info['id'] = sgt_id
        return info

    def get_sgt_list(self):
        return list(self._sgt_list.keys())

    def generate_troops_info(self):
        cpt = self.info._asdict()

        # generate sgt list
        sgt_list = []
        for sgt in self._sgt_list.values():
            # get pvt id list
            ep = 'http://{0}:{1}/pvt/list'.format(sgt['addr'], sgt['port'])
            id_list = requests.get(ep).json()['pvt_list']

            # get pvt detail
            pvt_list = []
            for pvt_id in id_list:
                ep = 'http://{0}:{1}/pvt/{2}/info'.format(sgt['addr'], sgt['port'], pvt_id)
                pvt_info = requests.get(ep).json()
                pvt_list.append(pvt_info)

            # get sgt's cache
            ep = 'http://{0}:{1}/dev/cache'.format(sgt['addr'], sgt['port'])
            cache_list = [str(c) for c in requests.get(ep).json()['cache']]
            cache_text = json.dumps(cache_list, indent=4, separators=(',', ': '))

            # append sgt info
            sgt['pvt_list'] = pvt_list
            sgt['cache_text'] = cache_text
            sgt_list.append(sgt.copy())
        cpt['sgt_list'] = sgt_list

        # generate cpt's cache
        cache_list = copy.deepcopy(self._cache)
        for report in cache_list:
            report['report'] = [str(work) for work in report['report']]
        cpt['cache_text'] = json.dumps(cache_list, indent=4, separators=(',', ': '))
        return cpt


# REST interface ---------------------------------------------------------------

server = Flask(__name__)
url_prefix = '/captain'

# 自身の情報を返す
@server.route(url_prefix, methods=['GET'])
def get_info():
    """
    Get this captain's information
    ---
    tags:
      - info
    definitions:
      - schema:
          id: CaptainInfo
          properties:
            id:
              type: string
            name:
              type: string
            addr:
              type: string
            port:
              type: int
    parameters: []
    responses:
      200:
        description: Captain's information
        schema:
          $ref: '#/definitions/CaptainInfo'
    """
    info = app.info
    return jsonify(result='success', info=info), 200


@server.route(url_prefix + '/cache', methods=['GET'])
def dev_cache():
    """
    Get current cached report data
    ---
    tags:
      - cache
    definitions:
      - schema:
          id: ReportList
          description: 'a list of report'
          type: 'array'
          items:
            $ref: '#/definitions/Report'
    parameters: []
    responses:
      200:
        description: Captain's current cache data
        schema:
          $ref: '#/definitions/ReportList'
    """
    return jsonify(result='success', cache=app._cache)


@server.route(url_prefix + '/ui/status', methods=['GET'])
def show_status():
    """
    show status UI
    ---
    tags:
      - UI
    parameters: []
    responses:
      200:
        description: Captain's status UI
    """
    return render_template("captain_ui.html", cpt = app.generate_troops_info())


@server.route(url_prefix + '/soldiers', methods=['GET', 'POST'])
@json_input
def pvt_list():
    if request.method == 'GET':
        res = app.get_sgt_list()
        return jsonify(result='success', sgt_list=res)
    elif request.method == 'POST':
        res = app.accept_sgt(request.json)
        return jsonify(result='success', accepted=res)


# TODO: このデコレータが正しく動作しているかチェック
def access_sergeant(f):
    """
    個別のsgtにアクセスするための存在チェック用デコレータ
    """
    @wraps(f)
    def check_sgt(sgt_id, *args, **kwargs):
        if not app.check_sgt_exist(sgt_id):
            return jsonify(result='failed',
                           msg='the pvt is not my soldier'), 404
        return f(sgt_id, *args, **kwargs)
    return check_sgt


@server.route(url_prefix + '/soldiers/<sgt_id>', methods=['GET'])
@access_sergeant
def sgt_info(sgt_id):
    res = app.get_sgt_info(sgt_id)
    return jsonify(res)


@server.route(url_prefix + '/soldiers/<sgt_id>/report', methods=['POST'])
@access_sergeant
@json_input
def sgt_report(sgt_id):
    app.accept_report(sgt_id, request.json)
    return jsonify(result='success')


@server.route(url_prefix + '/spec')
@cross_origin()
def spec():
    return jsonify(swagger(server))

# entry point ------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) == 2:
        self_port = int(sys.argv[1])
    else:
        self_port = 52000

    app = Captain('cpt-http', 'localhost', self_port)
    server.debug = True
    server.run(host='0.0.0.0', port=self_port, 
                use_debugger = True, use_reloader = False)
