from pprint import pprint
import cassiopeia as cass
from tinydb import Query
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
import copy

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
        "default": "INFO",
        "core": "INFO"
    }
})


class Player:
    def __init__(self, username):
        # Inherent values
        self.username = username
        self.ranked = {
            "RANKED_SOLO_5x5": {
                "rank": 0,
                "winrate": [0, 0],
                "rank_history": {},
                "nearest_rank": ["", 0],
            },
            "RANKED_FLEX_SR": {
                "rank": 0,
                "winrate": [0, 0],
                "rank_history": {},
                "nearest_rank": ["", 0],
            },
        }
        self.funny_stats = []
        self.funny_stats_diff = {
            "date": "",
            "data": [],
        }
        self.match_history = {
            "total_matches": 0,
            "match_ids": []
        }

        # Data format
        self.funny_stats_template = {
            'match': {
                'match_time': 0,
                'match_id': 0,
                'add_date': ""
            },
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
                'creep_kills': 0,
            },
            'objectives': {
                'objectives_stolen': 0,
                'first_tower_kill': 0,
                'tower_kills': 0,
            },
            'gold': 0,
            'time': {
                'time_spent_dead': 0,
                'time_spent_alive': 0,
                'time_cc_self': 0,
                'time_cc_other': 0,
            },
            'pings': {
                'missing': 0,
                'bait': 0,
            },
            'other': {
                'skill_shots_dodged': 0
            },
        }

        # dates
        self.curr_date = datetime.today().strftime(DATE_FORMAT)

        # Summoner
        self.region = 'EUW'
        self.cass_summoner = cass.Summoner(name=self.username, region=self.region)

    # json functions
    def load_from_json(self, data):
        """Set class variables from data"""

        def verify_missing_keys(f_orig: dict, f_new: dict):
            """Recursive function to check for key differences between code and DB"""

            if not isinstance(f_orig, dict) or not isinstance(f_new, dict):
                return []

            key1 = f_orig.keys()
            key2 = f_new.keys()
            diff = [item for item in key1 if item not in key2]
            same = [item for item in key1 if item in key2]

            if len(diff) < 1:
                for key in same:
                    return verify_missing_keys(f_orig[key], f_new[key])
            else:
                return diff

        if data is not None:
            # deserialize username
            if 'username' in data:
                self.username = data['username']

            # deserialize ranked
            if 'ranked' in data:
                for queue in self.ranked:
                    for missing in verify_missing_keys(self.ranked[queue], data['ranked'][queue]):
                        data['ranked'][queue][missing] = self.ranked[queue][missing]

                self.ranked = data['ranked']

            # deserialize funny stats
            if 'funny_stats' in data:
                self.funny_stats = data['funny_stats']

            if 'funny_stats_diff' in data:
                self.funny_stats_diff = data['funny_stats_diff']

            # deserialize match hist
            if 'match_history' in data:
                self.match_history = data['match_history']

        # updates
        self.update_nearest_date()

    def save_to_json(self):
        """Return formatted values to be saved to json"""
        return {
            'username': self.username,
            'ranked': self.ranked,
            'match_history': self.match_history,
            'funny_stats': self.funny_stats,
            'funny_stats_diff': self.funny_stats_diff,
        }

    # update functions
    def update_nearest_date(self):
        # LOG.warning('(update_nearest_date) - updating nearest date')
        for queue in self.ranked:
            queue_entry = self.ranked[queue]

            all_dates = list(queue_entry['rank_history'].keys())

            # Check if any dates exist
            if len(all_dates) > 1:

                # remove today from possible picks
                if self.curr_date in all_dates:
                    all_dates.pop(all_dates.index(self.curr_date))

                all_dates = [datetime.strptime(x, DATE_FORMAT) for x in all_dates]
                nearset_date = utils.nearest_date(all_dates, datetime.strptime(self.curr_date, DATE_FORMAT))
                self.ranked[queue]['nearest_rank'] = [nearset_date, queue_entry['rank_history'][nearset_date]]
                LOG.warning('(update_nearest_date) - set nearest date')

    # Cassio functions
    def update_current_rank(self):
        """Update the current ranked info for player"""
        LOG.warning(f'(update_current_rank) - updating rank for {self.username}')

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
                LOG.warning(f'(update_current_rank) - setting new current rank for'
                            f' {self.username} to {self.ranked[queue]["rank"]} in'
                            f' {queue} with winrate {self.ranked[queue]["winrate"]}')

    def add_rank_to_history(self):
        """Add current rank info to rank history"""
        LOG.warning(f'(add_rank_to_history) - adding rank to history for {self.username}')

        # Refresh current rank
        self.update_current_rank()

        for queue in self.ranked:
            LOG.warning(f'(add_rank_to_history) - current queue {queue}')
            queue_entry = self.ranked[queue]

            # Skip if last rank is the same
            if queue_entry['rank'] == queue_entry['nearest_rank'][1]:
                LOG.warning('(add_rank_to_history) - rank unchanged')
                continue

            # Update
            LOG.info(f'(add_rank_to_history) - updated new rank to {self.ranked[queue]["rank"]}')
            self.ranked[queue]['rank_history'][self.curr_date] = self.ranked[queue]['rank']
            self.update_nearest_date()

    def add_funny_to_stats(self):

        def add_to_hist(f_id):
            LOG.warning(f'id {f_id} not found adding')
            self.match_history['match_ids'].append(f_id)

        # adding funny stats
        match_limit = 40
        match_id_diff = []

        for i, match in enumerate(self.cass_summoner.match_history):

            # Limit to last 100 games
            if i >= match_limit:
                LOG.warning(f'Hit 100 match limit, stopping')
                break

            # # skip if already seen
            if match.id in self.match_history['match_ids']:
                LOG.warning('Match id found, skipping')
                continue

            # Exclude arena and other invalid game modes
            try:
                # skip if mode is not classic
                if match.queue.name not in ['ranked_flex_fives', 'normal_draft_fives', 'ranked_solo_fives']:
                    LOG.warning('match not classic')
                    add_to_hist(match.id)
                    match_limit += 1
                    continue
            except ValueError:
                LOG.warning('match returned an error')
                add_to_hist(match.id)
                match_limit += 1
                continue

            # add to hist if found
            add_to_hist(match.id)
            match_id_diff.append(match.id)

            # get current player stats from participants
            LOG.warning(f'{match.id} adding to funny stats')

            player_index = [x.summoner.name for x in match.participants].index(self.username)
            player_info = match.participants[player_index].to_dict()
            player_stats = player_info['stats']
            player_challenges = player_info['challenges']

            # assign to funny stats
            self.match_history['total_matches'] += 1

            # Fill template
            template = copy.deepcopy(self.funny_stats_template)

            template['match']['match_time'] = player_stats['timePlayed']
            template['match']['match_id'] = match.id
            template['match']['add_date'] = self.curr_date

            template['kills']['kda'][0] = player_stats['kills']
            template['kills']['kda'][1] = player_stats['deaths']
            template['kills']['kda'][2] = player_stats['assists']
            template['kills']['first_blood'] = int(player_stats['firstBloodKill'])
            template['kills']['double_kills'] = player_stats['doubleKills']
            template['kills']['triple_kills'] = player_stats['tripleKills']
            template['kills']['quadra_kills'] = player_stats['quadraKills']
            template['kills']['penta_kills'] = player_stats['pentaKills']

            template['vision']['pinks'] = player_stats['visionWardsBoughtInGame']
            template['vision']['wards'] = player_stats['wardsPlaced']
            template['vision']['vision_score'] = player_stats['visionScore']

            template['monsters']['dragon_kills'] = player_stats['dragonKills']
            template['monsters']['baron_kills'] = player_stats['baronKills']
            template['monsters']['creep_kills'] = player_stats['totalMinionsKilled']

            template['objectives']['objectives_stolen'] = player_stats['objectivesStolen']
            template['objectives']['first_tower_kill'] = int(player_stats['firstTowerKill'])
            template['objectives']['tower_kills'] = player_stats['turretKills']

            template['time']['time_cc_self'] = player_stats['totalTimeCCDealt']
            template['time']['time_cc_other'] = player_stats['timeCCingOthers']
            template['time']['time_spent_dead'] = player_stats['totalTimeSpentDead']
            template['time']['time_spent_alive'] = (
                    player_stats['timePlayed'] - player_stats['totalTimeSpentDead'])

            template['gold'] = player_stats['goldEarned']

            template['pings']['missing'] = player_info['enemyMissingPings']
            template['pings']['bait'] = player_info['baitPings']

            template['other']['skill_shots_dodged'] = player_challenges['skillshotsDodged']

            # Add to funny stats list
            self.funny_stats.append(template)

        # track funny stats changes per day
        if self.funny_stats_diff['date'] != self.curr_date:
            LOG.warning('setting funny stats for the day')

            # set values
            self.funny_stats_diff['date'] = self.curr_date
            self.funny_stats_diff['data'] = match_id_diff
