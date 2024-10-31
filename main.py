import argparse
from datetime import datetime, timedelta
import numpy as np
import json

import pandas as pd
import tensorflow as tf
from colorama import Fore, Style
from zoneinfo import ZoneInfo

from src.DataProviders.SbrOddsProvider import SbrOddsProvider
from src.Predict import NN_Runner, XGBoost_Runner
from src.Utils.Dictionaries import team_index_current
from src.Utils.tools import create_todays_games_from_odds, get_json_data, to_data_frame, get_todays_games_json, create_todays_games
from src.Utils import Kelly_Criterion as kc

todays_games_url = 'https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2024/scores/00_todays_scores.json'
data_url = 'https://stats.nba.com/stats/leaguedashteamstats?' \
           'Conference=&DateFrom=&DateTo=&Division=&GameScope=&' \
           'GameSegment=&LastNGames=0&LeagueID=00&Location=&' \
           'MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&' \
           'PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&' \
           'PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&' \
           'Season=2024-25&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&' \
           'StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision='


def createTodaysGames(games, df, odds):
    match_data = []
    todays_games_uo = []
    home_team_odds = []
    away_team_odds = []

    home_team_days_rest = []
    away_team_days_rest = []

    for game in games:
        home_team = game[0]
        away_team = game[1]
        if home_team not in team_index_current or away_team not in team_index_current:
            continue
        if odds is not None:
            game_odds = odds[home_team + ':' + away_team]
            todays_games_uo.append(game_odds['under_over_odds'])

            home_team_odds.append(game_odds[home_team]['money_line_odds'])
            away_team_odds.append(game_odds[away_team]['money_line_odds'])

        else:
            todays_games_uo.append(input(home_team + ' vs ' + away_team + ': '))

            home_team_odds.append(input(home_team + ' odds: '))
            away_team_odds.append(input(away_team + ' odds: '))

        # calculate days rest for both teams
        schedule_df = pd.read_csv('Data/nba-2024-UTC.csv', parse_dates=['Date'], date_format='%d/%m/%Y %H:%M')
        home_games = schedule_df[(schedule_df['Home Team'] == home_team) | (schedule_df['Away Team'] == home_team)]
        away_games = schedule_df[(schedule_df['Home Team'] == away_team) | (schedule_df['Away Team'] == away_team)]
        today_et = datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
        previous_home_games = home_games.loc[schedule_df['Date'] <= today_et].sort_values('Date',ascending=False).head(1)['Date']
        previous_away_games = away_games.loc[schedule_df['Date'] <= today_et].sort_values('Date',ascending=False).head(1)['Date']
        if len(previous_home_games) > 0:
            last_home_date = previous_home_games.iloc[0]
            home_days_off = timedelta(days=1) + today_et - last_home_date
        else:
            home_days_off = timedelta(days=7)
        if len(previous_away_games) > 0:
            last_away_date = previous_away_games.iloc[0]
            away_days_off = timedelta(days=1) + today_et - last_away_date
        else:
            away_days_off = timedelta(days=7)
        # print(f"{away_team} days off: {away_days_off.days} @ {home_team} days off: {home_days_off.days}")

        home_team_days_rest.append(home_days_off.days)
        away_team_days_rest.append(away_days_off.days)
        home_team_series = df.iloc[team_index_current.get(home_team)]
        away_team_series = df.iloc[team_index_current.get(away_team)]
        stats = pd.concat([home_team_series, away_team_series])
        stats['Days-Rest-Home'] = home_days_off.days
        stats['Days-Rest-Away'] = away_days_off.days
        match_data.append(stats)

    games_data_frame = pd.concat(match_data, ignore_index=True, axis=1)
    games_data_frame = games_data_frame.T

    frame_ml = games_data_frame.drop(columns=['TEAM_ID', 'TEAM_NAME'])
    data = frame_ml.values
    data = data.astype(float)

    return data, todays_games_uo, frame_ml, home_team_odds, away_team_odds


def expected_value(probability, american_odds):
    """기대값 계산 함수"""
    if american_odds >= 100:
        decimal_odds = (american_odds / 100) + 1
    else:
        decimal_odds = (100 / abs(american_odds)) + 1
        
    return probability * (decimal_odds - 1) - (1 - probability)


def save_predictions(games, predictions, odds):
    """예측 결과를 JSON 파일로 저장하고 베팅 히스토리 업데이트"""
    results = {
        "games": []
    }
    
    # 오늘 날짜
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 기존 베팅 히스토리 로드
    try:
        with open('betting_history.json', 'r') as f:
            betting_history = json.load(f)
    except FileNotFoundError:
        betting_history = {"bets": []}
    
    # 오늘 날짜의 기존 베팅 삭제 (재실행 시 중복 방지)
    betting_history["bets"] = [bet for bet in betting_history["bets"] if bet["date"] != today]
    
    count = 0
    for game in games:
        home_team = game[0]
        away_team = game[1]
        game_key = f"{home_team}:{away_team}"
        
        if game_key in odds:
            game_odds = odds[game_key]
            winner = "HOME" if np.argmax(predictions['ml'][count]) == 1 else "AWAY"
            winner_team = home_team if winner == "HOME" else away_team
            winner_prob = round(float(predictions['ml'][count][0][1 if winner == "HOME" else 0]) * 100, 1)
            
            ou_pred = "OVER" if np.argmax(predictions['ou'][count]) == 1 else "UNDER"
            ou_prob = round(float(predictions['ou'][count][0][1 if ou_pred == "OVER" else 0]) * 100, 1)
            
            # 켈리 기준 계산
            if winner == "HOME":
                odds_value = int(game_odds[home_team]['money_line_odds'])
                kelly = kc.calculate_kelly_criterion(odds_value, winner_prob/100)
            else:
                odds_value = int(game_odds[away_team]['money_line_odds'])
                kelly = kc.calculate_kelly_criterion(odds_value, winner_prob/100)
            
            # 기대값이 양수이고 켈리 기준이 양수인 경우만 베팅 히스토리에 추가
            ev = round(float(expected_value(winner_prob/100, odds_value)), 2)
            if ev > 0 and kelly > 0:
                betting_history["bets"].append({
                    "date": today,
                    "team": winner_team,
                    "odds": odds_value,
                    "kelly": kelly,
                    "result": "pending",  # 경기 결과는 나중에 업데이트
                    "user": "jaehoon"  # 또는 "kyungnam"
                })
            
            results["games"].append({
                "teams": f"{home_team} vs {away_team}",
                "win_prediction": f"{winner_team} ({winner_prob}%)",
                "ou_prediction": f"{ou_pred} {game_odds['under_over_odds']} ({ou_prob}%)",
                "kelly": f"{kelly}%",
                "half_kelly": f"{kelly/2}%",
                "expected_value": ev
            })
        count += 1
    
    # predictions.json 파일로 저장
    with open('predictions.json', 'w') as f:
        json.dump(results, f)
    
    # betting_history.json 파일로 저장
    with open('betting_history.json', 'w') as f:
        json.dump(betting_history, f, indent=4)


def main():
    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    
    # KST 오전 -> 전날 ET 경기
    # KST 오후 -> 당일 ET 경기
    current_time_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    if current_time_kst.hour < 12:  # KST 오전
        target_date = (current_time_kst - timedelta(days=1)).date()
    else:
        target_date = current_time_kst.date()
    
    odds = None
    if args.odds:
        odds = SbrOddsProvider(sportsbook=args.odds).get_odds()
        games = create_todays_games_from_odds(odds)
        if len(games) == 0:
            print("오늘의 경기가 없습니다.")
            return
            
        # 배당률이 없는 경기 필터링
        valid_games = []
        valid_odds = {}
        for game in games:
            key = f"{game[0]}:{game[1]}"
            if key in odds and odds[key][game[0]]['money_line_odds'] is not None:
                valid_games.append(game)
                valid_odds[key] = odds[key]
                
        if not valid_games:
            print(f"{target_date} 경기의 배당률이 아직 제공되지 않습니다.")
            return
            
        games = valid_games
        odds = valid_odds
    else:
        if target_date:
            schedule_df = pd.read_csv('Data/nba-2024-UTC.csv', parse_dates=['Date'])
            days_games = schedule_df[schedule_df['Date'].dt.date == target_date]
            games = [(row['Home Team'], row['Away Team']) for _, row in days_games.iterrows()]
        else:
            data = get_todays_games_json(todays_games_url)
            games = create_todays_games(data)
    data = get_json_data(data_url)
    df = to_data_frame(data)
    data, todays_games_uo, frame_ml, home_team_odds, away_team_odds = createTodaysGames(games, df, odds)
    if args.nn:
        print("------------Neural Network Model Predictions-----------")
        data = tf.keras.utils.normalize(data, axis=1)
        NN_Runner.nn_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, args.kc)
        print("-------------------------------------------------------")
    if args.xgb:
        print("---------------XGBoost Model Predictions---------------")
        predictions = XGBoost_Runner.xgb_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, args.kc)
        save_predictions(games, predictions, odds)
        print("-------------------------------------------------------")
    if args.A:
        print("---------------XGBoost Model Predictions---------------")
        XGBoost_Runner.xgb_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, args.kc)
        print("-------------------------------------------------------")
        data = tf.keras.utils.normalize(data, axis=1)
        print("------------Neural Network Model Predictions-----------")
        NN_Runner.nn_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, args.kc)
        print("-------------------------------------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Model to Run')
    parser.add_argument('-xgb', action='store_true', help='Run with XGBoost Model')
    parser.add_argument('-nn', action='store_true', help='Run with Neural Network Model')
    parser.add_argument('-A', action='store_true', help='Run all Models')
    parser.add_argument('-odds', help='Sportsbook to fetch from. (fanduel, draftkings, betmgm, pointsbet, caesars, wynn, bet_rivers_ny')
    parser.add_argument('-kc', action='store_true', help='Calculates percentage of bankroll to bet based on model edge')
    parser.add_argument('-date', help='Date to analyze (YYYY-MM-DD format)')
    args = parser.parse_args()
    main()