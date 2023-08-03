from datetime import datetime
from stores.constants import DATE_FORMAT


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
    return datetime.strftime(min(items, key=lambda x: abs(x - pivot)), DATE_FORMAT)
