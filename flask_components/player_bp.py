from flask import Blueprint, request
from stores.manager import summ_manager
import time

player_bp = Blueprint('player', __name__)
add_history_busy = False


@player_bp.route("/get_all", methods=["GET"])
def get_all():
    return summ_manager.all()


@player_bp.route("/add_rank_to_history", methods=["GET"])
def add_rank_to_history():
    global add_history_busy
    if not add_history_busy:
        add_history_busy = True
        summ_manager.add_rank_to_history()
        # time.sleep(60)
        add_history_busy = False
        return {}, 200
    else:
        return {}, 404


@player_bp.route("/update", methods=["GET"])
def update():
    time.sleep(10)
    print('update')
    return {}, 200


@player_bp.route("/profile_icon", methods=["GET"])
def get_profile_icon():
    player = request.args.get('player')
    return summ_manager.get_profile_icon(player)
