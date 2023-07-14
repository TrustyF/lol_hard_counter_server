from flask import Flask
from flask_cors import CORS
from flask_components.champion_bp import champion_bp

from storage import player_storage, champ_storage

app = Flask(__name__)
CORS(app)

app.register_blueprint(champion_bp, url_prefix='/champion')

if __name__ == '__main__':
    player_storage.test()
    # app.run(debug=True)
