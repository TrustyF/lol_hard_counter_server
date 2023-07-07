from flask import Flask
from flask_cors import CORS
from flask_components.champion_bp import champion_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(champion_bp, url_prefix='/champion')

if __name__ == '__main__':
    app.run(debug=True)
