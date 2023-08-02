import logging
import cassiopeia
from tinydb import TinyDB, Query
import os
import cassiopeia as cass
from dotenv import load_dotenv
from pprint import pprint
import time
from datetime import datetime, date, timedelta
from collections import defaultdict

env_path = os.path.join(os.path.dirname(__file__), '.env')
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
date_format = "%d/%m/%Y"

log = logging.getLogger('my_logger')
log.setLevel(logging.INFO)


def convert_to_rank_val(f_data):
    rank_mappings = {
        'rank_values': ['iron', 'bronze', 'silver', 'gold', 'platinum', 'emerald',
                        'diamond', 'master', 'grandmaster', 'challenger'],
        'division_values': ['IV', 'III', 'II', 'I']
    }

    lp = f_data['leaguePoints']
    division = rank_mappings['division_values'].index(f_data['division'])
    tier = rank_mappings['rank_values'].index(f_data['tier'].lower())

    formatted = lp + (division * 100) + (tier * 400)

    # print(f"{f_data['tier']} {f_data['division']} {f_data['leaguePoints']},", formatted, ",", lp, division * 100,
    #       tier * 400)
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
        # self.usernames = ['Grandoullf']

        self.queues = ['RANKED_SOLO_5x5', 'RANKED_FLEX_SR']
        self.curr_date = date.today().strftime(date_format)

        self.check_new_players()
        self.update_latest_rank_date()

    # flask funcs
    def get_all(self):
        return self.db.all()

    def sort_by_rank(self):
        unsorted = self.db.all()
        filtered = list(filter(lambda x: 'RANKED_SOLO_5x5' in x['rank'], unsorted))

        newlist = sorted(filtered, key=lambda d: d['rank']['RANKED_SOLO_5x5']['rank'])
        newlist.extend(list(filter(lambda x: 'RANKED_SOLO_5x5' not in x['rank'], unsorted)))

        return newlist

    def get_date_range(self):

        all_dates = []
        for player in self.db.all():
            for queue in self.queues:
                hist = player['rank_history'][queue]

                if hist == {}:
                    continue

                hist_keys = list(hist.keys())

                for h_key in hist_keys:
                    if h_key in all_dates:
                        continue

                    all_dates.append(h_key)

        # keep in case date comparaison doesnt work anymore
        # date_list = [datetime.strptime(x, date_format) for x in all_dates]
        date_range = [min(all_dates), max(all_dates)]

        start = datetime.strptime(date_range[0], date_format)
        end = datetime.strptime(date_range[1], date_format)

        dates_generated = [start + timedelta(days=x) for x in range(0, (end - start).days)]
        dates_generated.append(end)

        return [datetime.strftime(x, date_format) for x in dates_generated]

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
            nearset_date = None

            db_entry = self.db.get(username_query)

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
                log.info(f'current queue {queue}')
                data = db_entry['rank'][queue]

                # Check if rank is 0
                if db_entry['rank'][queue]['rank'] == 0:
                    log.warning('rank is 0')
                    continue

                # Check if rank has changed
                # Find closest date
                all_dates = (db_entry['rank_history'][queue].keys())

                # Check if any dates exist
                if len(all_dates) > 0:
                    log.warning('comparing last day rank')

                    all_dates = [datetime.strptime(x, date_format) for x in all_dates]
                    nearset_date = nearest_date(all_dates, datetime.strptime(self.curr_date, date_format))

                    # Compare last rank
                    if db_entry['rank'][queue]['rank'] == db_entry['rank_history'][queue][nearset_date]:
                        log.warning('rank unchanged')
                        continue
                else:
                    log.warning('no last day rank gound')

                # Create queue if none
                if queue not in db_entry['rank_history']:
                    db_entry['rank_history'][queue] = {}

                db_entry['rank_history'][queue][self.curr_date] = db_entry['rank'][queue]['rank']

                # Update
                log.info('updated new rank')
                self.db.update(db_entry, username_query)

        self.update_latest_rank_date()

    def update_latest_rank_date(self):
        for user in self.usernames:

            username_query = Query().username == user
            db_entry = self.db.get(username_query)

            for queue in db_entry['rank_history']:

                all_dates = list(db_entry['rank_history'][queue].keys())

                #  skip if list is empty
                if len(all_dates) < 1:
                    continue

                #  remove current date
                if self.curr_date in all_dates:
                    all_dates.remove(self.curr_date)

                all_dates = [datetime.strptime(x, date_format) for x in all_dates]

                # skip if no other nearest date
                if len(all_dates) < 1:
                    continue

                nearset_date = nearest_date(all_dates, datetime.strptime(self.curr_date, date_format))

                # Create rank info if none
                if 'rank_info' not in db_entry:
                    db_entry['rank_info'] = {}
                if queue not in db_entry['rank_info']:
                    db_entry['rank_info'][queue] = {}

                db_entry['rank_info'][queue]['nearest_date'] = nearset_date

                log.info('updated latest rank date')
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
                out[values['queue']]['rank'] = convert_to_rank_val(values)
                out[values['queue']]['winrate'] = (values['wins'], values['losses'])

        return out

    # helpers
    def fix_ranks(self):
        for user in self.usernames:

            print(user)
            username_query = Query().username == user
            db_entry = self.db.get(username_query)

            # pprint(db_entry)

            for category in ['rank', 'rank_history']:
                for queue in db_entry[category]:
                    for date in db_entry[category][queue]:
                        rank = db_entry[category][queue][date]

                        if rank == 0:
                            continue

                        if date == 'winrate':
                            continue

                        # print(rank)

                        old_rank = {
                            'leaguePoints': int(str(rank)[-2:]),
                            'division': int(str(rank)[-3:-2]),
                            'tier': int(str(rank)[0])
                        }
                        db_entry[category][queue][date] = old_rank['leaguePoints'] + (old_rank['division'] * 100) + (
                                old_rank['tier'] * 400)

            self.db.update(db_entry, username_query)


summ_manager = Manager()
