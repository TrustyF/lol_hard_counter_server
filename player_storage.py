import logging
import cassiopeia
from tinydb import TinyDB, Query
import os
import cassiopeia as cass
from dotenv import load_dotenv
from pprint import pprint
import time
from datetime import datetime, date
from collections import defaultdict

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

cass.set_riot_api_key(os.environ.get("RIOT_API_KEY"))
date_format = "%d/%m/%y"

COLOR_CODES = {
    logging.CRITICAL: "\033[1;35m",  # bright/bold magenta
    logging.ERROR: "\033[1;31m",  # bright/bold red
    logging.WARNING: "\033[1;33m",  # bright/bold yellow
    logging.INFO: "\033[0;37m",  # white / light gray
    logging.DEBUG: "\033[1;30m"  # bright/bold black / dark gray
}

log = logging.getLogger('my_logger')
log.setLevel(logging.INFO)


def convert_to_rank_val(f_data, f_mapping):
    formatted = int(str(f_mapping['rank_values'].index(f_data['tier'].lower())) +
                    str(f_mapping['division_values'].index(f_data['division'])) +
                    str(f_data['leaguePoints']).zfill(2))
    return formatted


def nearest_date(items, pivot):
    return datetime.strftime(min(items, key=lambda x: abs(x - pivot)), date_format)


class Manager:
    def __init__(self):

        self.base_path = os.path.dirname(__file__)
        self.db_path = os.path.join(self.base_path, f'database/players_db.json')

        self.db = TinyDB(self.db_path)

        self.usernames = ['TURBO Trusty', 'Ckwaceupoulet', 'TURBO OLINGO', 'ATM Kryder', 'Raz0xx', 'FRANZIZKUZ',
                          'TheRedAquaman', 'TURBO ALUCO', 'Welisilmanan', 'Grandoullf']

        self.rank_mappings = {
            'rank_values': ['iron', 'bronze', 'silver', 'gold', 'platinum', 'emerald',
                            'diamond', 'master', 'grandmaster', 'challenger'],
            'division_values': ['IV', 'III', 'II', 'I']
        }

        # self.usernames = ['ATM Kryder']

        self.check_new_players()
        self.add_rank_to_history()

        # self.sorted_by_rank = self.sort_by_rank()

    # flask funcs
    def get_all(self):
        return self.db.all()

    def sort_by_rank(self):
        unsorted = self.db.all()
        filtered = list(filter(lambda x: 'RANKED_SOLO_5x5' in x['rank'], unsorted))

        newlist = sorted(filtered, key=lambda d: d['rank']['RANKED_SOLO_5x5']['rank'])
        newlist.extend(list(filter(lambda x: 'RANKED_SOLO_5x5' not in x['rank'], unsorted)))

        return newlist

    # Class funcs
    def check_new_players(self):
        """Check if new players have been added to the list and register them in the database if not"""
        for user in self.usernames:
            data = {}

            # Check if already in db
            if self.db.search(Query().username == user):
                continue

            rank_info = self.get_current_rank(user)

            data['username'] = user
            data['rank'] = rank_info

            self.db.insert(data)

    def add_rank_to_history(self):
        """Add current rank info to rank history database"""
        log.info('Adding to rank history')
        for user in self.usernames:
            log.info(f'current username {user}')
            data = {}
            username_query = Query().username == user
            db_entry = self.db.get(username_query)

            curr_date = date.today().strftime(date_format)

            # Check if user in db
            if not db_entry:
                log.warning('user not in DB')
                continue

            # Check if user has rank history, if not add it
            if 'rank_history' not in db_entry:
                db_entry['rank_history'] = {}

            # Refresh current rank
            db_entry['rank'] = self.get_current_rank(db_entry['username'])

            formatted_rank = {}
            for queue in db_entry['rank']:
                data = db_entry['rank'][queue]

                # Check if rank is 0
                if db_entry['rank'][queue]['rank'] == 0:
                    log.warning('rank is 0')
                    continue

                # Check if date has already been added
                if curr_date in db_entry['rank_history'][queue]:
                    log.warning('current date found')
                    continue

                # Check if rank has changed
                # Find closest date
                all_dates = (db_entry['rank_history'][queue].keys())
                all_dates = [datetime.strptime(x, date_format) for x in all_dates]
                nearest_d = nearest_date(all_dates, datetime.strptime(curr_date, date_format))

                # Compare last rank
                if db_entry['rank'][queue]['rank'] == db_entry['rank_history'][queue][nearest_d]:
                    log.warning('rank unchanged')
                    continue

                # Create queue if none
                if queue not in db_entry['rank_history']:
                    db_entry['rank_history'][queue] = {}

                db_entry['rank_history'][queue][curr_date] = db_entry['rank'][queue]['rank']

                # Update
                self.db.update(db_entry, username_query)

    def get_current_rank(self, f_username):
        """Get the current ranked info for summoner"""
        player = cass.Summoner(name=f_username, region='EUW')
        entries = player.league_entries

        out = {
            'RANKED_SOLO_5x5': {
                'rank': 0,
                'winrate': [0, 0]
            },
            'RANKED_FLEX_SR': {
                'rank': 0,
                'winrate': [0, 0]
            },
        }
        for entry in entries:
            values = entry.to_dict()

            if values['queue'] not in out:
                log.warning(f'skipping queue {values["queue"]}')
                continue

            # check if any rank exists
            if 'tier' in values:
                out[values['queue']]['rank'] = convert_to_rank_val(values, self.rank_mappings)
                out[values['queue']]['winrate'] = (values['wins'], values['losses'])

        return out


summ_manager = Manager()
