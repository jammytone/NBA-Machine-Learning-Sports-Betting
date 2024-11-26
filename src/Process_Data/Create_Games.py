import os
import sqlite3
import sys

import numpy as np
import pandas as pd
import toml

sys.path.insert(1, os.path.join(sys.path[0], '../..'))
from src.Utils.Dictionaries import team_index_07, team_index_08, team_index_12, team_index_13, team_index_14, \
    team_index_current

config = toml.load("/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/config.toml")

df = pd.DataFrame
scores = []
win_margin = []
OU = []
OU_Cover = []
games = []
days_rest_away = []
days_rest_home = []
teams_con = sqlite3.connect("/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/Data/TeamData.sqlite")
odds_con = sqlite3.connect("/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/Data/OddsData.sqlite")

# TeamData.sqlite에서 사용 가능한 날짜 확인
def get_available_dates(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [table[0] for table in cursor.fetchall()]

available_dates = get_available_dates(teams_con)

def get_team_index(team_name, season):
    """시즌별 팀 인덱스를 안전하게 가져오는 함수"""
    if season == '2024-25':
        idx = team_index_current.get(team_name)
    elif season == '2007-08':
        idx = team_index_07.get(team_name)
    elif season == '2008-09' or season == "2009-10" or season == "2010-11" or season == "2011-12":
        idx = team_index_08.get(team_name)
    elif season == "2012-13":
        idx = team_index_12.get(team_name)
    elif season == '2013-14':
        idx = team_index_13.get(team_name)
    else:
        idx = team_index_14.get(team_name)
        
        # Charlotte Hornets/Bobcats 예외 처리
        if idx is None and team_name == "Charlotte Hornets":
            idx = team_index_14.get("Charlotte Bobcats")
    
    if idx is None:
        print(f"Warning: Could not find index for team {team_name} in season {season}")
    return idx

for key, value in config['create-games'].items():
    print(key)
    odds_df = pd.read_sql_query(f"select * from \"odds_{key}_new\"", odds_con, index_col="index")
    team_table_str = key
    year_count = 0
    season = key

    for row in odds_df.itertuples():
        home_team = row[2]
        away_team = row[3]

        date = row[1]

        # 해당 날짜의 팀 데이터가 있는 경우에만 처리
        if date in available_dates:
            team_df = pd.read_sql_query(f"select * from \"{date}\"", teams_con, index_col="index")
            if len(team_df.index) == 30:
                # 팀 인덱스 확인
                home_idx = get_team_index(home_team, season)
                away_idx = get_team_index(away_team, season)
                
                if home_idx is None or away_idx is None:
                    print(f"Skipping game - Team not found in index - Home: {home_team}, Away: {away_team}")
                    continue
                
                try:
                    home_team_series = team_df.iloc[home_idx]
                    away_team_series = team_df.iloc[away_idx]
                    
                    game = pd.concat([home_team_series, away_team_series.rename(
                        index={col: f"{col}.1" for col in team_df.columns.values}
                    )])
                    games.append(game)
                    
                    scores.append(row[8])
                    win_margin.append(1 if row[9] > 0 else 0)
                    OU.append(row[4])
                    
                    if row[8] < row[4]:
                        OU_Cover.append(0)
                    elif row[8] > row[4]:
                        OU_Cover.append(1)
                    else:
                        OU_Cover.append(2)
                    
                    days_rest_home.append(row[10])
                    days_rest_away.append(row[11])
                    
                except Exception as e:
                    print(f"Error processing game: {home_team} vs {away_team} on {date}")
                    print(e)
                    continue
        else:
            print(f"Skipping date {date} - no team data available")
odds_con.close()
teams_con.close()
season = pd.concat(games, ignore_index=True, axis=1)
season = season.T
frame = season.drop(columns=['TEAM_ID', 'TEAM_ID.1'])
frame['Score'] = np.asarray(scores)
frame['Home-Team-Win'] = np.asarray(win_margin)
frame['OU'] = np.asarray(OU)
frame['OU-Cover'] = np.asarray(OU_Cover)
frame['Days-Rest-Home'] = np.asarray(days_rest_home)
frame['Days-Rest-Away'] = np.asarray(days_rest_away)
# fix types
for field in frame.columns.values:
    if 'TEAM_' in field or 'Date' in field or field not in frame:
        continue
    frame[field] = frame[field].astype(float)
con = sqlite3.connect("/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/Data/dataset.sqlite")
frame.to_sql("dataset_2012-25_new", con, if_exists="replace")
con.close()
