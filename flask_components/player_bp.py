from flask import Blueprint
from stores.manager import summ_manager

player_bp = Blueprint('player', __name__)


@player_bp.route("/get_all", methods=["GET"])
def get_all():
    return summ_manager.get_all()


@player_bp.route("/get_date_range", methods=["GET"])
def get_date_range():
    return summ_manager.get_date_range()


@player_bp.route("/add_rank_to_history", methods=["GET"])
def add_rank_to_history():
    summ_manager.add_rank_to_history()
    return {}, 200
