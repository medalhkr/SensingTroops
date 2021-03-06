from flask import Flask
from flask_cors import CORS
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)


class RecruiterServer:
    @staticmethod
    def set_model(model):
        import controller.recruiter as rec
        rec.recruiter = model

    @staticmethod
    def generate_server(url_prefix):
        import controller.recruiter as rec
        server = Flask(__name__, static_url_path=url_prefix + "/static")
        server.register_blueprint(rec.server, url_prefix=url_prefix)
        CORS(server, resources={r"/*": {"origins": "*"}})
        return server


class CommanderServer:
    @staticmethod
    def set_model(model):
        import controller.commander as com
        com.commander = model

    @staticmethod
    def generate_server(url_prefix):
        import controller.commander as com
        server = Flask(__name__, static_url_path=url_prefix + "/static")
        server.register_blueprint(com.server, url_prefix=url_prefix)
        CORS(server, resources={r"/*": {"origins": "*"}})
        return server


class LeaderServer:
    @staticmethod
    def set_model(model):
        import controller.leader as lea
        lea.leader = model

    @staticmethod
    def generate_server(url_prefix):
        import controller.leader as lea
        server = Flask(__name__, static_url_path=url_prefix + "/static")
        server.register_blueprint(lea.server, url_prefix=url_prefix)
        CORS(server, resources={r"/*": {"origins": "*"}})
        return server
