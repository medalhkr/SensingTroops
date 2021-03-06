import argparse
import xmlrpc.client as xmlrpc_client
from logging import getLogger, StreamHandler, DEBUG
from utils.utils import trace_error, run_rpc
import yaml

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)

# 全体的に検索がゴリ押しで効率悪いが、検索が実行される回数自体が少ないので
# 問題ないと判断。ただ、時間があるならORMしたほうがいい。


class Recruiter(object):

    def __init__(self):
        raw = []
        with open('recruit.yml', 'r') as file:
            raw = yaml.load(file)['troops']

        # 入力ファイルのフォーマット確認などしてないので、重複IDなどあると
        # 無警告に上書きされる
        self.recruit = {}
        for com in raw:
            self.recruit[com['id']] = com
            leas = com['subs']
            com['subs'] = {}
            for lea in leas:
                com['subs'][lea['id']] = lea
                sols = lea['subs']
                lea['subs'] = {}
                for sol in sols:
                    lea['subs'][sol['id']] = sol

    @trace_error
    def register_commander(self, c_id, endpoint):
        """register_commander(c_id: str, endpoint: str) => bool"""
        if c_id not in self.recruit:
            return False
        client = xmlrpc_client.ServerProxy(endpoint)
        self.recruit[c_id]['rpcc'] = client
        self.recruit[c_id]['endpoint'] = endpoint
        return True

    @trace_error
    def get_commander(self, c_id):
        """get_commander(c_id: str) => {commander info}"""
        if c_id in self.recruit:
            raw = self.recruit[c_id]
            return {
                'id': raw['id'],
                'name': raw['commander'],
                'place': raw['place'],
            }
        return None

    @trace_error
    def get_leader(self, l_id):
        """get_leader(l_id: str) => {leader info}"""
        for com in self.recruit.values():
            if l_id in com['subs']:
                raw = com['subs'][l_id]
                ep = com['endpoint'] if 'endpoint' in com else ''
                return {
                    'id': raw['id'],
                    'name': raw['leader'],
                    'place': raw['place'],
                    'superior_ep': ep
                }
        return None

    @trace_error
    def get_soldier(self, s_id):
        """get_solier(s_id: str) => {soldier info}"""
        for com in self.recruit.values():
            for lea in com['subs'].values():
                if s_id in lea['subs']:
                    raw = lea['subs'][s_id]
                    l_data = self._resolve_leader(lea['id'])
                    ep = l_data['endpoint'] if l_data is not None else ''
                    return {
                        'id': raw['id'],
                        'name': raw['soldier'],
                        'place': raw['place'],
                        'superior_ep': ep
                    }
        return None

    @trace_error
    def resolve_superior(self, sub_id):
        """resolve_superior(sub_id: str) => {superior info}"""
        for com in self.recruit.values():
            if sub_id in com['subs']:
                return com
            for lea in com['subs'].values():
                if sub_id in lea['subs']:
                    leader_info = self._resolve_leader(lea['id'])
                    if leader_info is None:
                        return lea
                    lea['endpoint'] = leader_info['endpoint']
                    return lea
        return None

    @trace_error
    def _resolve_leader(self, l_id):
        com = self.resolve_superior(l_id)
        if com is None or 'rpcc' not in com:
            return None
        leader = com['rpcc'].get_subordinate(l_id)
        if leader is not None:
            return leader
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-P', '--port', type=int, default=50000, help="rpc-server's port num")
    params = parser.parse_args()
    port = params.port

    recruiter = Recruiter()
    if not run_rpc('127.0.0.1', port, recruiter):
        logger.info('Address already in use')
        return

    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
