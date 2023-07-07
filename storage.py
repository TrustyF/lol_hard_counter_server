from tinydb import TinyDB, Query
import os


class Champion:
    def __init__(self):
        self.base_path = os.path.dirname(__file__)
        self.db_path = os.path.join(self.base_path, f'database/champions_db.json')

        self.db = TinyDB(self.db_path)
        self.storage_lock = False

    def get_all(self):
        return self.db.all()


champ_storage = Champion()
