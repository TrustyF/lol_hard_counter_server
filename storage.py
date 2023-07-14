import cassiopeia
from tinydb import TinyDB, Query
import os
from cassiopeia import Summoner
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)
cassiopeia.set_riot_api_key(os.environ.get("RIOT_API_KEY"))


class Champions:
    def __init__(self):
        self.base_path = os.path.dirname(__file__)
        self.db_path = os.path.join(self.base_path, f'database/champions_db.json')

        self.db = TinyDB(self.db_path)
        self.storage_lock = False

    def get_all(self):
        return self.db.all()


class Players:
    def __init__(self):
        self.usernames = ['TURBO Trusty','Ckwaceupoulet','TURBO OLINGO']

    def test(self):
        player = Summoner(name=self.usernames[0], region='EUW')
        print(player.leagues)
        # print([cm.champion.name for cm in good_with])


champ_storage = Champions()
player_storage = Players()
