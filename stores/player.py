from pprint import pprint
import cassiopeia as cass
from tinydb import Query
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv

from stores.constants import LOG, DATE_FORMAT
import stores.utils as utils

# cassio settings
env_path = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(env_path)
RIOT_KEY = os.environ.get("RIOT_API_KEY")
cass.set_riot_api_key(RIOT_KEY)
cass.apply_settings({
    "logging": {
        "print_calls": True,
        "print_riot_api_key": False,
        "default": "WARNING",
        "core": "WARNING"
    }
})


class Player:
    def __init__(self, username):
        # Inherent values
        self.username = username
        self.ranked = {
            "RANKED_SOLO_5x5": {
                "rank": None,
                "winrate": [None, None],
                "rank_history": {},
                "nearest_rank_date": None,
            },
            "RANKED_FLEX_SR": {
                "rank": None,
                "winrate": [None, None],
                "rank_history": {},
                "nearest_rank_date": None,
            },
        }
        self.match_history = []
        self.funny_stats = {
            'total_matches': 0,
            'kills': {
                'kda': [0, 0, 0],
                'first_blood': 0,
                'penta_kills': 0,
                'quadra_kills': 0,
                'triple_kills': 0,
                'double_kills': 0,
            },
            'vision': {
                'pinks': 0,
                'wards': 0,
                'vision_score': 0,
            },
            'monsters': {
                'dragon_kills': 0,
                'baron_kills': 0,

            },
            'objectives': {
                'objectives_stolen': 0,
                'first_tower_kill': 0,
                'tower_kills': 0,
            },
            'consumables': 0,
            'gold': 0,
            'time': {
                'time_spent_dead': 0,
                'time_spent_alive': 0,
                'time_cc_self': 0,
                'time_cc_other': 0,
            },

        }

        # dates
        self.curr_date = datetime.today().strftime(DATE_FORMAT)

        # Summoner
        self.region = 'EUW'
        self.cass_summoner = cass.Summoner(name=self.username, region=self.region)

    # Class functions

    # json functions
    def load_from_json(self, data):
        """Set class variables from data"""

        if data is not None:
            # deserialize username
            if 'username' in data:
                self.username = data['username']

            # deserialize queue
            if 'ranked' in data:
                self.ranked = data['ranked']

            # deserialize match history
            if 'match_history' in data:
                self.match_history = data['match_history']

            # deserialize match history
            if 'funny_stats' in data:
                self.funny_stats = data['funny_stats']

        # updates
        self.update_nearest_date()
        self.add_funny_to_stats()

    def save_to_json(self):
        """Return formatted values to be saved to json"""
        return {
            'username': self.username,
            'ranked': self.ranked,
            'match_history': self.match_history,
            'funny_stats': self.funny_stats,
        }

    # update functions
    def update_nearest_date(self):
        for queue in self.ranked:
            queue_entry = self.ranked[queue]

            all_dates = queue_entry['rank_history'].keys()

            # Check if any dates exist
            if len(all_dates) > 0:
                all_dates = [datetime.strptime(x, DATE_FORMAT) for x in all_dates]
                nearset_date = utils.nearest_date(all_dates, datetime.strptime(self.curr_date, DATE_FORMAT))
                self.ranked[queue]['nearest_rank_date'] = nearset_date

    # Cassio functions
    def update_current_rank(self):
        """Update the current ranked info for player"""
        LOG.warning(f'updating rank for {self.username}')

        cass_entries = self.cass_summoner.league_entries

        for entry in cass_entries:
            values = entry.to_dict()
            queue = values['queue']

            if queue not in self.ranked:
                continue

            # check if any rank exists
            if 'tier' in values:
                self.ranked[queue]['rank'] = utils.convert_to_rank_val(values)
                self.ranked[queue]['winrate'] = [values['wins'], values['losses']]

    def add_rank_to_history(self):
        """Add current rank info to rank history"""
        LOG.warning(f'adding rank to history for {self.username}')

        # Refresh current rank
        self.update_current_rank()

        for queue in self.ranked:
            LOG.warning(f'current queue {queue}')
            queue_entry = self.ranked[queue]

            # Skip if no dates exists prior
            if len(queue_entry['rank_history']) < 1:
                LOG.warning('no rank history')
                continue

            # Skip if last rank is the same
            if queue_entry['rank'] == queue_entry['rank_history'][queue_entry['nearest_rank_date']]:
                LOG.warning('rank unchanged')
                continue

            # Update
            LOG.info('updated new rank')
            self.ranked[queue]['rank_history'][self.curr_date] = self.ranked[queue]['rank']

    def add_funny_to_stats(self):

        def add_to_hist(f_id):
            LOG.warning(f'id {f_id} not found adding')
            self.match_history.append(f_id)

        # noinspection PyTypeChecker
        for match in self.cass_summoner.match_history[:30]:

            # skip if already seen
            if match.id in self.match_history:
                LOG.warning(f'match {match.id} found, not adding')
                continue

            # Exclude arena and other invalid game modes
            try:
                # skip if mode is not classic
                if match.mode.name != 'classic':
                    add_to_hist(match.id)
                    continue
            except ValueError:
                add_to_hist(match.id)
                continue

            # add to hist if found
            add_to_hist(match.id)

            # get current player stats from participants
            LOG.warning(f'{match.id} adding to funny stats')
            # pprint(dir(match.mode))
            player_index = [x.summoner.name for x in match.participants].index(self.username)
            player_stats = match.participants[player_index].stats

            # assign to funny stats
            self.funny_stats['total_matches'] += 1

            self.funny_stats['kills']['kda'][0] += player_stats.kills
            self.funny_stats['kills']['kda'][1] += player_stats.deaths
            self.funny_stats['kills']['kda'][2] += player_stats.assists
            self.funny_stats['kills']['first_blood'] += int(player_stats.first_blood_kill)
            self.funny_stats['kills']['double_kills'] += player_stats.double_kills
            self.funny_stats['kills']['triple_kills'] += player_stats.triple_kills
            self.funny_stats['kills']['quadra_kills'] += player_stats.quadra_kills
            self.funny_stats['kills']['penta_kills'] += player_stats.penta_kills

            self.funny_stats['vision']['pinks'] += player_stats.vision_wards_placed
            self.funny_stats['vision']['wards'] += player_stats.wards_placed
            self.funny_stats['vision']['vision_score'] += player_stats.vision_score

            self.funny_stats['monsters']['dragon_kills'] += player_stats.dragon_kills
            self.funny_stats['monsters']['baron_kills'] += player_stats.baron_kills

            self.funny_stats['objectives']['objectives_stolen'] += player_stats.objectives_stolen
            self.funny_stats['objectives']['first_tower_kill'] += int(player_stats.first_tower_kill)
            self.funny_stats['objectives']['tower_kills'] += player_stats.turret_kills

            self.funny_stats['time']['time_cc_self'] += player_stats.total_time_cc_dealt
            self.funny_stats['time']['time_cc_other'] += player_stats.time_CCing_others
            self.funny_stats['time']['time_spent_dead'] += player_stats.total_time_spent_dead
            self.funny_stats['time']['time_spent_alive'] += player_stats.longest_time_spent_living

            self.funny_stats['gold'] += player_stats.gold_earned

            self.funny_stats['consumables'] += player_stats.consumables_purchased
