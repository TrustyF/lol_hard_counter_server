import cassiopeia as cass
from dotenv import load_dotenv
from tinydb import TinyDB, Query
import os
from pprint import pprint
import time
from datetime import datetime, date, timedelta
from collections import defaultdict
import io
from PIL import Image

from stores.constants import DATE_FORMAT, LOG, BASE_PATH
import stores.utils
from stores.player import Player

# cassio settings
env_path = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(env_path)
RIOT_KEY = os.environ.get("RIOT_API_KEY")

settings = cass.get_default_config()
settings['logging']['print_calls'] = False
cass.apply_settings(settings)


class Manager:
    def __init__(self):
        self.db_path = os.path.join(BASE_PATH, f'../database/players_db.json')
        self.db = TinyDB(self.db_path, indent=2)

        self.usernames = ['TURBO Trusty', 'Ckwaceupoulet', 'TURBO OLINGO', 'ATM Kryder', 'Raz0xx', 'FRANZIZKUZ',
                          'TheRedAquaman', 'TURBO ALUCO', 'Grandoullf', 'TURBO BERINGEI', 'Kertor']
        # self.usernames = ['TURBO Trusty', 'Raz0xx']

        # Prep players
        self.players = []

        #  Functions
        self.load_players()

        # todo remove this
        # self.add_rank_to_history()

    def load_players(self):
        for user in self.usernames:
            username_query = Query().username == user
            db_entry = self.db.get(username_query)

            object = Player(user, self.db)
            object.load_from_json(db_entry)

            self.players.append(object)

        # todo removed for performance but might cause issues
        # self.save_players()

    def all(self):
        return [x.save_to_json() for x in self.players]

    def save_players(self):
        for player in self.players:
            LOG.warning(f'saving {player.username} to DB')
            user_query = Query().username == player.username

            if self.db.get(user_query):
                self.db.update(player.save_to_json(), user_query)
            else:
                self.db.insert(player.save_to_json())

    # flask funcs
    def add_rank_to_history(self):
        for player in self.players:
            player.add_rank_to_history()
            player.add_match_to_history()

    def get_profile_icon(self, player):
        index = self.usernames.index(player)
        image_path = os.path.join(BASE_PATH, f'../assets/{player}.jpeg')

        # if not found download it
        if not os.path.exists(image_path):
            self.players[index].cass_summoner.profile_icon.image.save(image_path, format='JPEG')

        # open image bytes
        output = io.BytesIO()
        img = Image.open(image_path)
        img.save(output, format='JPEG')

        return output.getvalue()


summ_manager = Manager()
