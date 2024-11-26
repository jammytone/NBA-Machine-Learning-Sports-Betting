import os
import random
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import toml
from sbrscrape import Scoreboard

# TODO: Add tests

sys.path.insert(1, os.path.join(sys.path[0], '../..'))

sportsbook = 'fanduel'
df_data = []

# 24-25 시즌 설정
season_config = {
    '2024-25': {
        'start_date': "2024-10-22",
        'end_date': datetime.now().strftime('%Y-%m-%d'),  # 현재 날짜까지만
    }
}

# 경로 수정
con = sqlite3.connect("/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/Data/OddsData.sqlite")  # 상대 경로 수정

for key, value in season_config.items():
    date_pointer = datetime.strptime(value['start_date'], "%Y-%m-%d").date()
    end_date = datetime.strptime(value['end_date'], "%Y-%m-%d").date()
    teams_last_played = {}

    while date_pointer <= end_date:
        print("Getting odds data: ", date_pointer)
        sb = Scoreboard(date=date_pointer)

        if not hasattr(sb, "games"):
            date_pointer = date_pointer + timedelta(days=1)
            continue

        for game in sb.games:
            if game['home_team'] not in teams_last_played:
                teams_last_played[game['home_team']] = date_pointer
                home_games_rested = timedelta(days=7)  # start of season, big number
            else:
                current_date = date_pointer
                home_games_rested = current_date - teams_last_played[game['home_team']]
                teams_last_played[game['home_team']] = current_date

            if game['away_team'] not in teams_last_played:
                teams_last_played[game['away_team']] = date_pointer
                away_games_rested = timedelta(days=7)  # start of season, big number
            else:
                current_date = date_pointer
                away_games_rested = current_date - teams_last_played[game['away_team']]
                teams_last_played[game['away_team']] = current_date

            try:
                df_data.append({
                    'Date': date_pointer,
                    'Home': game['home_team'],
                    'Away': game['away_team'],
                    'OU': game['total'][sportsbook],
                    'Spread': game['away_spread'][sportsbook],
                    'ML_Home': game['home_ml'][sportsbook],
                    'ML_Away': game['away_ml'][sportsbook],
                    'Points': game['away_score'] + game['home_score'],
                    'Win_Margin': game['home_score'] - game['away_score'],
                    'Days_Rest_Home': home_games_rested.days,
                    'Days_Rest_Away': away_games_rested.days
                })
            except KeyError:
                print(f"No {sportsbook} odds data found for game: {game}")

        date_pointer = date_pointer + timedelta(days=1)
        time.sleep(random.randint(1, 3))

    df = pd.DataFrame(df_data, )
    df.to_sql(f"odds_{key}_new", con, if_exists="replace")
con.close()
