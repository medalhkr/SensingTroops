import pymongo
import datetime


def get_collection(col):
    return pymongo.MongoClient("192.168.0.21")["troops"][col]
    # return pymongo.MongoClient("localhost")["troops"]["values"]


def get_values(purpose, place, type, max_count, days=1, hours=0, minutes=0):
    now = datetime.datetime.now(datetime.timezone.utc)
    limit_time = now - datetime.timedelta(
        days=days, hours=hours, minutes=minutes)

    col = get_collection(purpose.replace("sensing-", ""))
    s_purpose = {"purpose": purpose}
    s_place = {"place": place}
    s_type = {"data.type": type}
    s_time = {"time": {"$gt": limit_time}}
    search = {}
    search.update(s_purpose)
    search.update(s_place)
    search.update(s_type)
    search.update(s_time)

    filter = {"_id": 0}
    res = col.find(search, projection=filter).sort("time", pymongo.DESCENDING)
    res_list = list(res)
    if len(res_list) > max_count:
        res_list = res_list[::len(res_list) // max_count + 1]

    return [
        [i["time"], i["data"]["value"], i["data"]["unit"]]
        for i in res_list
    ]
