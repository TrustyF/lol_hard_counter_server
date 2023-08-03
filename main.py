from flask import Flask
from flask_cors import CORS
from flask_components.player_bp import player_bp
import os
import cassiopeia as cass
from dotenv import load_dotenv
import sys

# cassio settings
env_path = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(env_path)
RIOT_KEY = os.environ.get("RIOT_API_KEY")
cass.set_riot_api_key(RIOT_KEY)
cass.apply_settings({
    "logging": {
        "print_calls": False,
        "print_riot_api_key": False,
        "default": "WARNING",
        "core": "WARNING"
    }
})

app = Flask(__name__)
CORS(app)

app.register_blueprint(player_bp, url_prefix='/player')
