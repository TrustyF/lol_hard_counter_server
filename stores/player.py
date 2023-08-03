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
        "print_calls": False,
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
        self.profile_icon = None

        # dates
        self.curr_date = datetime.today().strftime(DATE_FORMAT)

        # Summoner
        self.cass_summoner = cass.Summoner(name=self.username, region='EUW')

    # Class functions

    # json functions
    def load_from_json(self, data):
        """Set class variables from data"""

        # deserialize username
        if 'username' in data:
            self.username = data['username']

        # deserialize queue
        if 'ranked' in data:
            self.ranked = data['ranked']

        # deserialize profile icon
        if 'profile_icon' in data:
            self.profile_icon = data['profile_icon']

        # updates
        self.update_nearest_date()
        self.update_profile_icon()

    def save_to_json(self):
        """Return formatted values to be saved to json"""
        return {
            'username': self.username,
            'ranked': self.ranked,
            'profile_icon': self.profile_icon,
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

    def update_profile_icon(self):
        self.profile_icon = self.cass_summoner.profile_icon.id

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
