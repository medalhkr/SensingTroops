import argparse
import xmlrpc.client as xmlrpc_client
from flask import Flask, request, jsonify, render_template

server = Flask(__name__)


@server.route('/troop.html', methods=['GET'])
def show_troops():
    return render_template('troops_viewer.html')

@server.route('/troop.json', methods=['GET'])
def get_troops_json():
    """
    指定されたCommanderが保有する部隊情報をツリー用jsonで返す
    ---
    parameters:
      - name: endpoint
        in: query
        required: true
    """
    endpoint = request.args.get('endpoint', default='', type=str)
    if endpoint == '':
        return "lack of parameter", 400

    client = xmlrpc_client.ServerProxy(endpoint)
    com = client.retrieve_troop_info()

    root = {
        "text": "Commander: {0} at {1}".format(com['id'], com['place']),
        "icon": "troops commander",
        "href": com['endpoint'],
        "nodes": [
            { "text": 'missions', 'nodes': []},
            { "text": "subs", 'nodes': []},
        ]
    }
    for m in com['missions'].values():
        root['nodes'][0]['nodes'].append({
            'text': str(m)
        })
    for lid, leader in com['subs'].items():
        l_node = {
            "text": "Leader: {0} at {1}".format(lid, leader['place']),
            "icon": "troops leader",
            "href": leader['endpoint'],
            "nodes": [
                { "text": "operations", 'nodes': []},
                { "text": "subs", 'nodes': []},
            ]
        }
        for op in leader['operations'].values():
            l_node['nodes'][0]['nodes'].append({
                'text': str(op)
            })
        for sid, soldier in leader['subs'].items():
            s_node = {
                "text": "Soldier: {0} at {1}".format(sid, soldier['place']),
                "icon": "troops soldier",
                "href": soldier['endpoint'],
                "nodes": [
                    { "text": "orders", 'nodes': []},
                    { "text": 'weapons: {0}'.format(str(soldier['weapons']))},
                ]
            }
            for o in soldier['orders'].values():
                s_node['nodes'][0]['nodes'].append({
                    'text': str(o)
                })
            l_node['nodes'][1]['nodes'].append(s_node)
        root['nodes'][1]['nodes'].append(l_node)

    return jsonify([root])

@server.route('/xmlrpc/exec', methods=['GET', 'POST'])
def exec_rpc():
    """
    リモートホストの関数をxmlrpcで呼び出す
    ---
    parameters:
      - name: endpoint
        in: query
        required: true
      - name: method
        in: query
        required: true
      - name: param*
        description: リモートメソッドに渡すパラメータを指定する。param0=...&param1=...のようにする
        in: query
    """
    endpoint = ''
    method = ''
    params = []
    if request.method == 'GET':
        endpoint = request.args.get('endpoint', default='', type=str)
        method = request.args.get('method', default='', type=str)
        for i in range(1000):
            v = request.args.get('param%d' % i, default=None, type=str)
            if v is None:
                break
            # TODO: 必要に応じて数値へのキャスト
            params.append(v)
    elif request.method == 'POST':
        # TODO: impl
        pass
    if endpoint == '' or method == '':
        return "lack of parameter", 400

    client = xmlrpc_client.ServerProxy(endpoint)
    return jsonify(getattr(client, method)(*params))


@server.route('/xmlrpc/helps', methods=['GET'])
def exec_help():
    """
    endpointで指定したノードのrpc関数のヘルプを表示する
    ---
    parameters:
      - name: endpoint
        in: query
        required: true
    """
    endpoint = request.args.get('endpoint', default='', type=str)
    if endpoint == '':
        return "lack of parameter", 400

    client = xmlrpc_client.ServerProxy(endpoint)
    helps = {}
    for name in client.system.listMethods():
        if "system." in name:
            continue
        helps[name] = client.system.methodHelp(name)
    return jsonify(helps)


if __name__ == "__main__":
    # param setting
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-P', '--port', type=int, default=50001, help='port')
    args = parser.parse_args()
    port = args.port

    server.debug = True
    server.run(host='0.0.0.0', port=port)
