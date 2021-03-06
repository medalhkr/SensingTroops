import argparse
import json
import signal
from logging import getLogger, StreamHandler, DEBUG, ERROR
from flask import render_template, jsonify, request
from flask_swagger import swagger
from controller import CommanderServer
from model import definitions, Commander
from utils.helpers import get_ip, get_mac, DelegateHandler

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)


if __name__ == "__main__":
    # param setting
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--spec', action="store_true", help='output spec.json and exit')
    parser.add_argument(
        '-I', '--id', type=str, default='', help='Target id of app')
    parser.add_argument(
        '-N', '--name', type=str, default='', help='Target name of app')
    parser.add_argument(
        '-P', '--port', type=int, default=50001, help='port')
    parser.add_argument(
        '-F', '--prefix', type=str, default='/commander', help='url prefix')
    parser.add_argument(
        '-E', '--endpoint', type=str, default='', help='endpoint')
    parser.add_argument(
        '-T', '--token', type=str, default='', help='slack token')
    parser.add_argument(
        '-R', '--rec_addr', type=str, help="recruiter url",
        default="http://localhost:50000/recruiter/")
    params = parser.parse_args()

    # server setting
    server = CommanderServer.generate_server(params.prefix)

    if params.spec:
        spec_dict = swagger(server, template={'definitions': definitions})
        spec_dict['info']['title'] = 'SensingTroops'
        print(json.dumps(spec_dict, sort_keys=True, indent=2))
        exit()

    if params.id == "":
        params.id = get_mac()
    if params.name == "":
        params.name = "commander"
    if params.endpoint == "":
        host_addr = get_ip()
        ep = 'http://{0}:{1}{2}/'.format(host_addr, params.port, params.prefix)
    else:
        ep = params.endpoint

    commander = Commander(params.id, params.name, ep)
    commander.awake(params.rec_addr)
    commander.token = params.token
    CommanderServer.set_model(commander)

    @server.route(params.prefix + '/spec.json')
    def output_spec_json():
        spec_dict = swagger(server, template={'definitions': definitions})
        spec_dict['info']['title'] = 'SensingTroops'
        return jsonify(spec_dict)

    @server.route(params.prefix + '/spec.html')
    def spec_html():
        return render_template('swagger_ui.html')

    # エラーログ送信用ログハンドラ
    error_handler = DelegateHandler(commander.push_error)
    error_handler.setLevel(ERROR)
    getLogger("model").addHandler(error_handler)

    # 強制終了のハンドラ
    original_shutdown = signal.getsignal(signal.SIGINT)
    def shutdown(signum, frame):
        commander.shutdown()
        original_shutdown(signum, frame)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    server.debug = True
    server.run(host='0.0.0.0', port=params.port, use_reloader=False)
