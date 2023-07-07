from flask import Blueprint, render_template, redirect
from storage import champ_storage

champion_bp = Blueprint('champion', __name__)


@champion_bp.route("/get_all", methods=["GET"])
def get():
    return champ_storage.get_all()
