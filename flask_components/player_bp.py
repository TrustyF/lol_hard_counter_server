from pprint import pprint

from flask import Blueprint, render_template, redirect
from player_storage import summ_manager
from flask_apscheduler import APScheduler
import time

player_bp = Blueprint('player', __name__)
scheduler = APScheduler()

# schedule rank update every day
scheduler.add_job(id='test', func=summ_manager.add_rank_to_history, trigger='interval', hours=12)
scheduler.start()


@player_bp.route("/get_all", methods=["GET"])
def get_all():
    return summ_manager.get_all()


@player_bp.route("/get_date_range", methods=["GET"])
def get_date_range():
    return summ_manager.get_date_range()
