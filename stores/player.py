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
                'creep_kills': 0,
            },
            'objectives': {
                'objectives_stolen': 0,
                'first_tower_kill': 0,
                'tower_kills': 0,
            },
            'gold': 0,
            'time': {
                'total_time_played': 0,
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
            }

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
                        # if self.username == 'TURBO OLINGO': pprint(missing)
                        data['ranked'][queue][missing] = self.ranked[queue][missing]

                self.ranked = data['ranked']

            # deserialize match history
            if 'match_history' in data:
                self.match_history = data['match_history']

            # deserialize match history
            if 'funny_stats' in data:
                self.funny_stats = data['funny_stats']

        # updates
        self.update_nearest_date()

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

            all_dates = list(queue_entry['rank_history'].keys())

            # Check if any dates exist
            if len(all_dates) > 0:

                # remove today from possible picks
                if self.curr_date in all_dates:
                    all_dates.pop(all_dates.index(self.curr_date))

                all_dates = [datetime.strptime(x, DATE_FORMAT) for x in all_dates]
                nearset_date = utils.nearest_date(all_dates, datetime.strptime(self.curr_date, DATE_FORMAT))
                self.ranked[queue]['nearest_rank'] = [nearset_date, queue_entry['rank_history'][nearset_date]]

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
                LOG.warning(f'setting new current rank for {self.username} to {self.ranked[queue]["rank"]} in'
                            f' {queue} with winrate {self.ranked[queue]["winrate"]}')

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
            if queue_entry['rank'] == queue_entry['nearest_rank'][1]:
                LOG.warning('rank unchanged')
                continue

            # Update
            LOG.info(f'updated new rank to {self.ranked[queue]["rank"]}')
            self.ranked[queue]['rank_history'][self.curr_date] = self.ranked[queue]['rank']

    def add_funny_to_stats(self):

        def add_to_hist(f_id):
            LOG.warning(f'id {f_id} not found adding')
            self.match_history.append(f_id)

        match_limit = 100
        for i, match in enumerate(self.cass_summoner.match_history):

            # Limit to last 100 games
            if i >= match_limit:
                LOG.warning(f'Hit 100 match limit, stopping')
                break

            # # skip if already seen
            if match.id in self.match_history:
                LOG.warning(f'match {match.id} found, not adding')
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

            # get current player stats from participants
            LOG.warning(f'{match.id} adding to funny stats')
            # pprint(dir(match.mode))
            player_index = [x.summoner.name for x in match.participants].index(self.username)

            player_info = match.participants[player_index].to_dict()
            player_stats = player_info['stats']
            player_challenges = player_info['challenges']

            # pprint((match.participants[player_index].to_dict()))

            # constants
            time_played = player_stats['timePlayed']

            # assign to funny stats
            self.funny_stats['total_matches'] += 1
            self.funny_stats['time']['total_time_played'] += time_played

            self.funny_stats['kills']['kda'][0] += player_stats['kills']
            self.funny_stats['kills']['kda'][1] += player_stats['deaths']
            self.funny_stats['kills']['kda'][2] += player_stats['assists']
            self.funny_stats['kills']['first_blood'] += int(player_stats['firstBloodKill'])
            self.funny_stats['kills']['double_kills'] += player_stats['doubleKills']
            self.funny_stats['kills']['triple_kills'] += player_stats['tripleKills']
            self.funny_stats['kills']['quadra_kills'] += player_stats['quadraKills']
            self.funny_stats['kills']['penta_kills'] += player_stats['pentaKills']

            self.funny_stats['vision']['pinks'] += player_stats['visionWardsBoughtInGame']
            self.funny_stats['vision']['wards'] += player_stats['wardsPlaced']
            self.funny_stats['vision']['vision_score'] += player_stats['visionScore']

            self.funny_stats['monsters']['dragon_kills'] += player_stats['dragonKills']
            self.funny_stats['monsters']['baron_kills'] += player_stats['baronKills']
            self.funny_stats['monsters']['creep_kills'] += player_stats['totalMinionsKilled']

            self.funny_stats['objectives']['objectives_stolen'] += player_stats['objectivesStolen']
            self.funny_stats['objectives']['first_tower_kill'] += int(player_stats['firstTowerKill'])
            self.funny_stats['objectives']['tower_kills'] += player_stats['turretKills']

            self.funny_stats['time']['time_cc_self'] += player_stats['totalTimeCCDealt']
            self.funny_stats['time']['time_cc_other'] += player_stats['timeCCingOthers']
            self.funny_stats['time']['time_spent_dead'] += player_stats['totalTimeSpentDead']
            self.funny_stats['time']['time_spent_alive'] += (time_played - player_stats['totalTimeSpentDead'])

            self.funny_stats['gold'] += player_stats['goldEarned']

            self.funny_stats['pings']['missing'] += player_info['enemyMissingPings']
            self.funny_stats['pings']['bait'] += player_info['baitPings']

            self.funny_stats['other']['skill_shots_dodged'] += player_challenges['skillshotsDodged']
