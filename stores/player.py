import json
from pprint import pprint
import cassiopeia as cass
from tinydb import Query
from datetime import datetime, date, timedelta
import os
import copy

from stores.constants import LOG, DATE_FORMAT
import stores.utils as utils


class Player:
    def __init__(self, username, database):
        # Inherent values
        self.username = username
        self.database = database

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
        self.match_ids = []

        # data format
        self.match_template = {
            "match_info": {
                "match_win": True,
                "player_side": None,
                "sides": {
                    "red": {
                        "isWinner": None,
                        "objectives": {},
                    },
                    "blue": {
                        "isWinner": None,
                        "objectives": {},
                    },
                }
            },
            "player_stats": {
                'kills': 0,
                'deaths': 0,
                'assists': 0,
                'goldPerMinute': 0,
                'firstBloodKill': 0,
                'totalAllyJungleMinionsKilled': 0,
                'totalEnemyJungleMinionsKilled': 0,
                'totalMinionsKilled': 0,
                'dodgeSkillShotsSmallWindow': 0,
                'maxCsAdvantageOnLaneOpponent': 0,
                'maxLevelLeadLaneOpponent': 0,
                'visionScoreAdvantageLaneOpponent': 0,
                'totalDamageTaken': 0,
                'totalDamageDealt': 0,
                'totalDamageDealtToChampions': 0,
                'teamDamagePercentage': 0,
                'damageSelfMitigated': 0,
                'totalHeal': 0,
                'totalHealsOnTeammates': 0,
                'totalDamageShieldedOnTeammates': 0,
                'timeAlive': 0,
                'totalTimeSpentDead': 0,
                'totalTimeCCDealt': 0,
                'timeCCingOthers': 0,
                'turretTakedowns': 0,
                'damageDealtToTurrets': 0,
                'takedownOnFirstTurret': 0,
                'objectivesStolen': 0,
                'epicMonsterStolenWithoutSmite': 0,
                'teamRiftHeraldKills': 0,
                'dragonTakedowns': 0,
                'teamBaronKills': 0,
                'teamElderDragonKills': 0,
                'detectorWardsPlaced': 0,
                'wardsPlaced': 0,
                'visionScore': 0,
                'doubleKills': 0,
                'tripleKills': 0,
                'quadraKills': 0,
                'pentaKills': 0,
                'enemyMissingPings': 0,
                'baitPings': 0,
            },
            "match_ranks": {
                "red": [],
                "blue": [],
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

            # deserialize match hist
            if 'match_history' in data:
                self.match_history = data['match_history']

            # deserialize match ids
            if 'match_ids' in data:
                self.match_ids = data['match_ids']

    def save_to_json(self):
        """Return formatted values to be saved to json"""
        return {
            'username': self.username,
            'ranked': self.ranked,
            'match_history': self.match_history,
            'match_ids': self.match_ids,
        }

    # db functions
    def save_current_player(self):
        LOG.warning(f'saving {self.username} to DB')
        user_query = Query().username == self.username

        if self.database.get(user_query):
            self.database.update(self.save_to_json(), user_query)
        else:
            self.database.insert(self.save_to_json())

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
                self.update_nearest_date()

        self.save_current_player()

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

    def add_match_to_history(self):

        def add_to_id_hist(f_id):
            LOG.warning(f'id {f_id} not found adding')
            self.match_ids.append(f_id)

        def recursive_fill_template_from_dict(data: dict, template: dict):
            for f_key in data:
                if f_key in template:
                    template[f_key] = data[f_key]
                if isinstance(data[f_key], dict):
                    recursive_fill_template_from_dict(data[f_key], template)

        # adding to match hist
        match_limit = 2

        for i, match in enumerate(self.cass_summoner.match_history):

            # Limit to last n games
            if i >= match_limit:
                LOG.warning(f'Hit match limit, stopping')
                break

            # skip if already seen
            if match.id in self.match_ids:
                LOG.warning('Match id found, skipping')
                continue

            # Exclude arena and other invalid game modes
            try:
                # skip if mode is not classic
                if match.queue.name not in ['ranked_flex_fives', 'normal_draft_fives', 'ranked_solo_fives']:
                    LOG.warning('match not classic')
                    add_to_id_hist(match.id)
                    match_limit += 1
                    continue
            except ValueError:
                LOG.warning('match returned an error')
                add_to_id_hist(match.id)
                match_limit += 1
                continue

            # add to hist if found
            add_to_id_hist(match.id)

            # get current player stats from participants
            LOG.warning(f'{match.id} adding to match history')
            player_index = [x.summoner.name for x in match.participants].index(self.username)
            player_info = match.participants[player_index].to_dict()

            match_template = copy.deepcopy(self.match_template)

            # map player match stats
            recursive_fill_template_from_dict(player_info, match_template['player_stats'])

            # add match info for red and blue side
            for f_side in match.teams:
                side_info = f_side.to_dict()
                recursive_fill_template_from_dict(side_info,
                                                  match_template['match_info']['sides'][f_side.side.name])

                # Set current player extra details
                if self.username in [x['summonerName'] for x in side_info['participants']]:
                    match_template['match_info']['match_win'] = side_info['isWinner']
                    match_template['match_info']['player_side'] = f_side.side.name

            # calc match ranks
            for player in match.participants:

                player_summ = player.summoner

                participant_stats = {
                    'username': player.summoner.name,
                    'rank': 0,
                    'winrate': [0, 0],
                    'account_lvl': player_summ.level
                }

                # get solo q rank
                for entry in player_summ.league_entries:
                    values = entry.to_dict()
                    queue = values['queue']

                    if queue == 'RANKED_SOLO_5x5':
                        # check if any rank exists
                        if 'tier' in values:
                            participant_stats['rank'] = utils.convert_to_rank_val(values)
                            participant_stats['winrate'] = [values['wins'], values['losses']]

                # add player to match
                match_template["match_ranks"][player.side.name].append(participant_stats)

            # Add match to list
            self.match_history.append(match_template)

            # save to db
            self.save_current_player()
