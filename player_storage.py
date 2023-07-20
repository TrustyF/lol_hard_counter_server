import logging
import cassiopeia
from tinydb import TinyDB, Query
import os
import cassiopeia as cass
from dotenv import load_dotenv
from pprint import pprint
import time
from datetime import datetime, date

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

cass.set_riot_api_key(os.environ.get("RIOT_API_KEY"))


def format_rank(f_data):
    rank_values = ['iron', 'bronze', 'silver', 'gold', 'platinum', 'emerald',
                   'diamond', 'master', 'grandmaster', 'challenger']
    extra_rank_value = rank_values.index(f_data['tier'].lower())
    return f"{f_data['tier']} {f_data['division']} {extra_rank_value} {f_data['leaguePoints']}"


class Manager:
    def __init__(self):

        self.base_path = os.path.dirname(__file__)
        self.db_path = os.path.join(self.base_path, f'database/players_db.json')

        self.db = TinyDB(self.db_path)

        self.usernames = ['TURBO Trusty', 'Ckwaceupoulet', 'TURBO OLINGO', 'ATM Kryder', 'Raz0xx', 'FRANZIZKUZ',
                          'TheRedAquaman', 'TURBO ALUCO', 'Welisilmanan']

        self.check_new_players()
        self.add_rank_to_history()

    # flask funcs
    def get_all(self):
        return self.db.all()

    # Class funcs
    def check_new_players(self):
        """Check if new players have been added to the list and register them in the database if not"""
        for user in self.usernames:
            data = {}

            # Check if already in db
            if self.db.search(Query().username == user):
                continue

            logging.warning(f'{user} found, adding')
            rank_info = self.get_current_rank(user)

            data['username'] = user
            data['rank'] = rank_info

            pprint(data)
            self.db.insert(data)

    def add_rank_to_history(self):
        """Add current rank info to rank history database"""
        for user in self.usernames:
            data = {}
            username_query = Query().username == user
            db_entry = self.db.get(username_query)
            curr_date = date.today().strftime("%d/%m/%y")

            # Check if user in db
            if not db_entry:
                logging.warning(f'{user} not found!')
                continue

            # Check if user has any rank
            if not db_entry['rank']:
                logging.warning(f'{user} no rank!')
                continue

            # Check if user has rank history, if not add it
            if 'rank_history' not in db_entry:
                logging.warning(f'{user} no history, making one!')
                db_entry['rank_history'] = {}

            # Check if data has already been updated
            if curr_date in db_entry['rank_history']:
                logging.warning(f'{user} history already added!')
                continue

            # Concat info to shorter
            formatted_rank = {}
            for queue in db_entry['rank']:
                data = db_entry['rank'][queue]
                formatted_rank[queue] = format_rank(data)

                # Date the entry
            dated_rank = {}
            dated_rank[curr_date] = formatted_rank
            db_entry['rank_history'] = dated_rank

            # Update
            logging.warning(f'{user} updated today rank!')
            self.db.update(db_entry, username_query)

    def get_current_rank(self, f_username):
        """Get the current ranked info for summoner"""
        player = cass.Summoner(name=f_username, region='EUW')
        entries = player.league_entries

        out = {}
        for entry in entries:
            values = entry.to_dict()
            out[values['queue']] = {
                'division': values['division'],
                'hotStreak': values['hotStreak'],
                'leaguePoints': values['leaguePoints'],
                'losses': values['losses'],
                'wins': values['wins'],
                'tier': values['tier'],
            }
        pprint(out)
        return out


summ_manager = Manager()
# good_with = player.champion_masteries.filter(lambda cm: cm.level >= 6)
# print([cm.champion.name for cm in good_with])
