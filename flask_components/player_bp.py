from flask import Blueprint, request
from stores.manager import summ_manager

player_bp = Blueprint('player', __name__)


@player_bp.route("/get_all", methods=["GET"])
def get_all():
    return summ_manager.all()


@player_bp.route("/add_rank_to_history", methods=["GET"])
def add_rank_to_history():
    summ_manager.add_rank_to_history()
    return {}, 200


@player_bp.route("/profile_icon", methods=["GET"])
def get_profile_icon():
    player = request.args.get('player')
    return summ_manager.get_profile_icon(player)
