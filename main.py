from flask import Flask
from flask_cors import CORS
from flask_components.champion_bp import champion_bp
from flask_components.player_bp import player_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(champion_bp, url_prefix='/champion')
app.register_blueprint(player_bp, url_prefix='/player')

if __name__ == '__main__':
    app.run()
