from pprint import pprint


class Player:
    def __init__(self):
        self.username = None
        self.rank = {
            "RANKED_SOLO_5x5": {
                "rank": 0,
                "winrate": [0, 0]
            },
            "RANKED_FLEX_SR": {
                "rank": 0,
                "winrate": [0, 0]
            },
        }
        self.rank_history = {
            "RANKED_SOLO_5x5": {},
            "RANKED_FLEX_SR": {},
        }
        self.rank_info = {
            "nearest_date": "00/00/0000"
        }

    def load_from_json(self, data):
        if 'username' in data:
            self.username = data['username']

        if 'rank' in data:
            self.rank = data['rank']

        if 'rank_history' in data:
            self.rank_history = data['rank_history']

        if 'rank_info' in data:
            self.rank_info = data['rank_info']

    def save_to_json(self):
        return {
            'username': self.username,
            'rank': self.rank,
            'rank_history': self.rank_history,
            'rank_info': self.rank_info
        }
