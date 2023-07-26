import requests

api = ["http://localhost:5000", "https://ttt-trustyfox.pythonanywhere.com"]
requests.get(f'{api[1]}/player/add_rank_to_history')
