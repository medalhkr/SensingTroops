import argparse
import asyncio
import copy
import datetime
import random
import xmlrpc.client as xmlrpc_client
from time import sleep
from logging import getLogger, StreamHandler, DEBUG
from utils.utils import trace_error, run_rpc

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)

LOOP = asyncio.get_event_loop()


class SoldierBase(object):

    def __init__(self):
        self.id = ''
        self.name = ''
        self.place = ''
        self.endpoint = ''
        self.orders = {}
        self.weapons = {
            "zero": lambda: 0,
            "random": random.random
        }
        self.superior = None

    @trace_error
    def show_info(self):
        """show_info() => {soldier info}"""
        info = {
            'type': 'Soldier',
            'id': self.id,
            'name': self.name,
            'place': self.place,
            'endpoint': self.endpoint,
            'weapons': list(self.weapons.keys()),
            'orders': self.get_orders()
        }
        return info

    @trace_error
    def get_orders(self):
        res = copy.copy(self.orders)
        for o in res.values():
            o.pop('event')
        return res

    @trace_error
    def add_order(self, order):
        """add_order(order: {order}) => None"""
        print('got order: {0}'.format(order))
        if order['purpose'] in self.orders:
            self.orders[order['purpose']]['event'].set()
            del self.orders[order['purpose']]

        event = asyncio.Event(loop=LOOP)
        asyncio.ensure_future(self._working(
            event, order['requirements'], order['trigger']), loop=LOOP)
        order['event'] = event
        self.orders[order['purpose']] = order

    async def _working(self, event, reqs, interval):
        while not event.is_set():
            vals = []
            for k in reqs:
                time = datetime.datetime.now(datetime.timezone.utc).isoformat()
                vals.append({
                    'id': self.id,
                    'type': k,
                    'value': self.weapons[k](),
                    'time': time
                })
            self.superior['rpcc'].accept_data(vals)
            await asyncio.sleep(interval, loop=LOOP)


def get_self_info(recruiter_ep, self_id, retry_count):
    recruiter = xmlrpc_client.ServerProxy(recruiter_ep)
    resolved = None
    retry_sleep = 2
    for i in range(retry_count):
        try:
            resolved = recruiter.get_soldier(self_id)
        except ConnectionRefusedError:
            logger.info(
                "failed to connect to recruiter. retry %d sec after", retry_sleep)
            sleep(retry_sleep)
            retry_sleep = retry_sleep * 2
            continue
        break
    if retry_sleep == 2 * (2 ** retry_count):
        return "Couldn't connect to recruiter"

    if resolved is None:
        return "Soldier not found: ID = %s" % self_id
    if resolved['superior_ep'] == '':
        return "The superior's instance don't exist"
    return resolved


def main(soldier):
    # read args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-I', '--id', type=str, default='', help='Target id of app')
    parser.add_argument(
        '-P', '--port', type=int, default=53000, help="rpc-server's port num")
    parser.add_argument(
        '-R', '--rec_addr', type=str, help="recruiter url",
        default="http://localhost:50000/")
    params = parser.parse_args()

    # set params
    port = params.port
    self_id = params.id
    if self_id == '':
        self_id = 'S_' + str(port)
    ip = '127.0.0.1'
    endpoint = 'http://{0}:{1}'.format(ip, port)
    recruiter_ep = params.rec_addr

    if not run_rpc(ip, port, soldier):
        return "Address already in use"

    info = get_self_info(recruiter_ep, self_id, 3)
    if isinstance(info, str):
        return info
    soldier.id = info['id']
    soldier.name = info['name']
    soldier.place = info['place']
    soldier.endpoint = endpoint

    # join
    client = xmlrpc_client.ServerProxy(info['superior_ep'])
    retry_sleep = 2
    for i in range(5):
        try:
            client.add_subordinate(soldier.show_info())
        except ConnectionRefusedError:
            logger.info(
                "failed to connect to superior. retry %d sec after", retry_sleep)
            sleep(retry_sleep)
            retry_sleep = retry_sleep * 2
            continue
        break
    if retry_sleep == 2 * (2 ** 5):
        return "Couldn't connect to commander"

    soldier.superior = {
        'rpcc': client
    }

    try:
        LOOP.run_forever()
    except KeyboardInterrupt:
        pass
    return None


if __name__ == "__main__":
    soldier = SoldierBase()
    res = main(soldier)
    if res is not None:
        logger.error(res)
