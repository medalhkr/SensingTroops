import copy
import datetime
from threading import Event, Thread
from model import SoldierInfo, LeaderInfo, Mission, Order, Report, Work
from typing import List, Dict
from utils.helpers import rest_get, rest_post
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)


class Leader(object):
    def __init__(self, leader_id, name, endpoint):
        self.id = leader_id
        self.name = name
        self.endpoint = endpoint
        self.subordinates = {}  # type:Dict[str, SoldierInfo]
        self.missions = {}  # type:Dict[str, Mission]
        self.work_cache = []  # type:List[Work]
        self.superior_ep = ""
        self.heartbeat_thread = HeartBeat(self, 0)
        self.working_threads = []  # type: List[WorkingThread]

    def awake(self, rec_ep: str, heartbeat_rate: int):
        from model import CommanderInfo

        # 上官を解決する
        url = rec_ep + 'department/troop/commander?leader_id=' + self.id
        res, err = rest_get(url)
        if err is not None:
            return False
        superior = CommanderInfo.make(res.json()['commander'])
        self.superior_ep = superior.endpoint
        logger.info("superior was resolved: id={0}".format(superior.id))

        # 部隊に加入する
        url = self.superior_ep + "subordinates"
        res, err = rest_post(url, json=self.generate_info().to_dict())
        if err is not None:
            return False
        logger.info("joined to squad: commander_id: {0}".format(superior.id))

        # missionを取得する
        self.start_heartbeat(heartbeat_rate)

    def generate_info(self) -> LeaderInfo:
        """
        自身のパラメータ群からLeaderInfoオブジェクトを生成する
        :return LeaderInfo: 生成したLeaderInfo
        """
        return LeaderInfo(
            id=self.id,
            name=self.name,
            endpoint=self.endpoint,
            subordinates=list(self.subordinates.keys()),
            missions=list(self.missions.values()))

    def check_subordinate(self, sub_id):
        """
        指定された兵隊が部下に存在するかを確認する
        :param str sub_id: 確認したい部下のID
        :return bool: 存在すればTrue
        """
        return sub_id in self.subordinates

    def start_heartbeat(self, interval):
        self.heartbeat_thread.interval = interval
        self.heartbeat_thread.start()

    def accept_mission(self, mission: Mission) -> Mission:
        # 部下のOrderを生成・割り当てる
        target_subs = []
        if mission.place == "All":
            target_subs = list(self.subordinates.keys())
        o_base = Order(author="",
                       values=mission.requirement.values,
                       trigger=mission.requirement.trigger,
                       purpose=mission.get_id())
        for t_id in target_subs:
            order = copy.deepcopy(o_base)
            order.author = t_id
            self.subordinates[t_id].orders.append(order)

        # 自身のデータ送信スレッドを生成する
        th = WorkingThread(self, mission)
        self.working_threads.append(th)
        th.start()

        self.missions[mission.purpose] = mission
        return mission

    def get_sub_info(self, sub_id):
        return self.subordinates[sub_id]

    def accept_subordinate(self, sub_info):
        """
        部下の入隊を受け入れる
        :param SoldierInfo sub_info: 受け入れるLeaderの情報
        :return bool:
        """
        logger.debug('In accept_subordinate:')
        logger.debug('> sub_info:{0}'.format(sub_info))
        if self.check_subordinate(sub_info.id):
            return False
        self.subordinates[sub_info.id] = sub_info
        return True

    def accept_work(self, sub_id, work):
        if not self.check_subordinate(sub_id):
            return False
        self.work_cache.append(work)
        return True


class WorkingThread(Thread):
    def __init__(self, leader: Leader, mission: Mission):
        super(WorkingThread, self).__init__(daemon=True)
        self.mission = mission
        self.leader = leader
        self.lock = Event()

    def run(self):
        if 'timer' in self.mission.trigger.keys():
            interval = self.mission.trigger['timer']
            while not self.lock.wait(timeout=interval):
                m_id = self.mission.get_id()
                works = [w for w in self.leader.work_cache if w.purpose == m_id]
                time = datetime.datetime.utcnow().isoformat()
                report = Report(time,
                                self.mission.purpose,
                                [{"time": w.time, "values": w.values}
                                 for w in works])

                url = "{0}{1}".format(
                    self.leader.superior_ep,
                    "subordinates/{0}/report".format(self.leader.id))
                rest_post(url, json=report.to_dict())
                # TODO: エラー処理

                self.leader.work_cache = \
                    [w for w in self.leader.work_cache if w.purpose != m_id]
        else:
            pass


class HeartBeat(Thread):
    def __init__(self, leader: Leader, interval: int):
        super(HeartBeat, self).__init__(daemon=True)
        self.lock = Event()
        self.leader = leader
        self.interval = interval
        self.etag = None

    def run(self):
        while not self.lock.wait(timeout=self.interval):
            url = self.leader.superior_ep + "subordinates/" + self.leader.id
            res, err = rest_get(url, etag=self.etag)
            if err is not None:
                return
            if res.status_code == 304:
                continue
            self.etag = res.headers['ETag']
            info = LeaderInfo.make(res.json()['info'])

            logger.info([str(m) for m in info.missions])
            for m in info.missions:
                self.leader.accept_mission(m)
