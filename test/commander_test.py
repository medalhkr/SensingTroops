#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import unittest
import commander
import json
from flask import Flask
from logging import getLogger, StreamHandler, FileHandler, DEBUG
from objects import LeaderInfo, CommanderInfo, Report, Mission, Campaign

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)


class CommanderTestCase(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        del sys.modules['commander']
        import commander  # モジュールのリロードをしないと内部のappがリセットされないため
        commander.set_params("cxxx0", "cmd_http", "http://localhost:50000")
        app = Flask(__name__)
        app.register_blueprint(commander.server, url_prefix="/commander")
        self.app = app.test_client()

    def tearDown(self):
        pass

    def test_get_info(self):
        response = self.app.get('/commander', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))

        commander = CommanderInfo(id='cxxx0',
                                  name='cmd_http',
                                  endpoint='http://localhost:50000',
                                  subordinates=[],
                                  campaigns=[])
        expected = {"result": "success", "info": dict(commander._asdict())}

        self.assertEqual(actual, expected)

# [POST] /subordinates
    def test_add_subordinate(self):
        leader = LeaderInfo(id='lxxx0',
                            name='cmd_http',
                            endpoint='http://localhost:50000',
                            subordinates=[],
                            missions=[])
        response = self.app.post('/commander/subordinates',
                                 data=json.dumps(leader._asdict()),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))

        expected = {'result': 'success', "accepted": dict(leader._asdict())}
        self.assertEqual(actual, expected)

# [GET] /subordinates
    def test_get_subordinates_none(self):
        response = self.app.get('/commander/subordinates')
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))

        # assert
        expected = {'subordinates': []}
        self.assertEqual(actual, expected)

    def test_get_subordinates_single(self):
        # add a leader
        leader = LeaderInfo(id='lxxx0',
                            name='cmd_http',
                            endpoint='http://localhost:50000',
                            subordinates=[],
                            missions=[])
        self.app.post('/commander/subordinates',
                      data=json.dumps(leader._asdict()),
                      content_type='application/json')

        # get subordinates
        response = self.app.get('/commander/subordinates')
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))

        # assert
        expected = {'subordinates': [dict(leader._asdict())]}
        self.assertEqual(actual, expected)

    def test_get_subordinates_multi(self):
        # add some leader
        leader_base = LeaderInfo(id='lxxx0',
                                 name='cmd_http',
                                 endpoint='http://localhost:50000',
                                 subordinates=[],
                                 missions=[])
        leader_list = [
            leader_base._replace(id='lxxx0'),
            leader_base._replace(id='lxxx1'),
            leader_base._replace(id='lxxx2'),
            leader_base._replace(id='lxxx3'),
        ]
        for l in leader_list:
            self.app.post('/commander/subordinates',
                          data=json.dumps(l._asdict()),
                          content_type='application/json')

        # get subordinates
        response = self.app.get('/commander/subordinates')
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))
        actual_list = actual['subordinates']

        # assert
        expected_list = [dict(l._asdict()) for l in leader_list]
        self.assertEqual(len(actual_list), len(expected_list))
        for exp in expected_list:
            if exp not in actual_list:
                self.fail('{0} is not found.'.format(exp))

# [POST] /campaigns
    def test_add_campaign(self):
        # 各種パラメータの詳細が決まっていないため、暫定値を採用。
        # 最終的には、API自体に無効な入力パラメータをハネる機能を搭載したうえで
        # TODO: 無効値を確認する用のテストを作成すべき
        campaign = Campaign(author='cxxx0',
                            destination='mongoserv',
                            place='S101',
                            purpose='A great app',
                            requirements='brightness sound',
                            trigger='a trigger')
        response = self.app.post('/commander/campaigns',
                                 data=json.dumps(campaign._asdict()),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))

        expected = {'result': 'success', "accepted": dict(campaign._asdict())}
        self.assertEqual(actual, expected)

# [GET] /campaigns
    def test_get_campaigns_none(self):
        response = self.app.get('/commander/campaigns')
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))

        # assert
        expected = {'campaigns': []}
        self.assertEqual(actual, expected)

    def test_get_campaigns_single(self):
        # add a campaigns
        campaign = Campaign(author='cxxx0',
                            destination='mongoserv',
                            place='S101',
                            purpose='A great app',
                            requirements='brightness sound',
                            trigger='a trigger')
        response = self.app.post('/commander/campaigns',
                                 data=json.dumps(campaign._asdict()),
                                 content_type='application/json')

        # get subordinates
        response = self.app.get('/commander/subordinates')
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))

        # assert
        expected = {'subordinates': [dict(campaign._asdict())]}
        self.assertEqual(actual, expected)

    def test_get_campaigns_multi(self):
        # add some campaigns
        campaign_base = Campaign(author='cxxx0',
                                 destination='mongoserv',
                                 place='S101',
                                 purpose='A great app',
                                 requirements='brightness sound',
                                 trigger='a trigger')
        campaign_list = [
            campaign_base._replace(place='S101'),
            campaign_base._replace(place='S102'),
            campaign_base._replace(place='S103'),
            campaign_base._replace(place='S104'),
        ]
        for c in campaign_list:
            self.app.post('/commander/campaigns',
                          data=json.dumps(c._asdict()),
                          content_type='application/json')

        # get campaigns
        response = self.app.get('/commander/campaigns')
        self.assertEqual(response.status_code, 200)
        actual = json.loads(response.data.decode("utf-8"))
        actual_list = actual['campaigns']

        # assert
        expected_list = [dict(c._asdict()) for c in campaign_list]
        self.assertEqual(len(actual_list), len(expected_list))
        for exp in expected_list:
            if exp not in actual_list:
                self.fail('{0} is not found.'.format(exp))