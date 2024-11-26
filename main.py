import argparse
from datetime import datetime, timedelta
import numpy as np
import json

import pandas as pd
import tensorflow as tf
from colorama import Fore, Style
from zoneinfo import ZoneInfo
import sqlite3
import os
import sys
from src.DataProviders.SbrOddsProvider import SbrOddsProvider
from src.Predict import NN_Runner, XGBoost_Runner
from src.Utils.Dictionaries import team_index_current
from src.Utils.tools import create_todays_games_from_odds, get_json_data, to_data_frame, get_todays_games_json, create_todays_games
from src.Utils import Kelly_Criterion as kc

# fanduel, draftkings, betmgm, pointsbet, caesars, wynn, bet_rivers_ny

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

    # 경기가 없는 경우 처리
    if not games:
        print("오늘/내일 예정된 경기가 없습니다.")
        return None, None, None, None, None

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
        schedule_df = pd.read_csv('Data/nba-2024-UTC.csv')
        schedule_df['Date'] = pd.to_datetime(schedule_df['Date'])
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

    # match_data가 비어있는 경우 처리
    if not match_data:
        print("처리할 경기 데이터가 없습니다.")
        return None, None, None, None, None

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


def save_predictions(games, predictions, odds, target_date):
    """예측 결과를 CSV 파일에 저장하고 승패 최종 파일에도 추가"""
    
    # KST로 날짜 변환 (ET + 1일)
    kst_date = target_date + timedelta(days=1)  # 하루 추가
    game_date = kst_date.strftime('%m/%d')
    
    # 정확한 파일 경로 지정
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'NBA_승패_최종 - 승패.csv')
    
    try:
        final_df = pd.read_csv(file_path)
        print(f"기존 데이터 행 수: {len(final_df)}")
        # 현재 날짜의 데이터를 제외한 데이터만 유지
        final_df = final_df[final_df['날짜'] != game_date]
        initial_bank = final_df['잔액'].iloc[-1] if not final_df.empty else 1000
    except FileNotFoundError:
        print("새로운 파일을 생성합니다.")
        final_df = pd.DataFrame(columns=[
            '날짜', '홈', '어웨이', '예측', '확률', '배당', '결과', 
            '켈리 비율', '진입', '자본금 변화', '날짜별 초기 잔액', '잔액'
        ])
        initial_bank = 1000

    new_records = []
    current_date = None
    current_bank = initial_bank
    
    for count, game in enumerate(games):
        home_team = game[0]
        away_team = game[1]
        game_key = f"{home_team}:{away_team}"
        
        if game_key in odds:
            game_odds = odds[game_key]
            winner = "HOME" if np.argmax(predictions['ml'][count]) == 1 else "AWAY"
            winner_team = home_team if winner == "HOME" else away_team
            prob = float(predictions['ml'][count][0][1 if winner == "HOME" else 0])
            
            # 배당률 변환
            if winner == "HOME":
                odds_value = float(game_odds[home_team]['money_line_odds'])
            else:
                odds_value = float(game_odds[away_team]['money_line_odds'])
            
            if odds_value >= 100:
                decimal_odds = (odds_value / 100) + 1
            else:
                decimal_odds = (100 / abs(odds_value)) + 1
            
            # 켈리 비율 계산
            kelly = min(0.1, max(0, (prob * (decimal_odds - 1) - (1 - prob)) / (decimal_odds - 1)))
            entry_amount = kelly * current_bank
            
            # 날짜별 초기 잔액 계산
            if current_date != game_date:
                daily_initial_bank = current_bank
            else:
                daily_initial_bank = new_records[-1]['날짜별 초기 잔액'] if new_records else current_bank
            
            new_record = {
                '날짜': game_date,
                '홈': home_team,
                '어웨이': away_team,
                '예측': winner_team,
                '확률': prob,
                '배당': round(decimal_odds, 2),
                '결과': '',  # 결과는 빈칸으로 남겨둠
                '켈리 비율': kelly,
                '진입': entry_amount,
                '자본금 변화': 0,  # 결과 입력 전까지는 0
                '날짜별 초기 잔액': daily_initial_bank,
                '잔액': daily_initial_bank  # 결과 입력 전까지는 초기 잔액과 동일
            }
            new_records.append(new_record)
            current_date = game_date
    
    # 새로운 데이터를 DataFrame에 추가
    if new_records:
        new_df = pd.DataFrame(new_records)
        print(f"새로운 데이터 행 수: {len(new_df)}")  # 디버깅용
        
        new_df = new_df.astype({
            '날짜': str,
            '홈': str,
            '어웨이': str,
            '예측': str,
            '확률': float,
            '배당': float,
            '결과': str,
            '켈리 비율': float,
            '진입': float,
            '자본금 변화': float,
            '날짜별 초기 잔액': float,
            '잔액': float
        })
        
        if final_df.empty:
            final_df = new_df
        else:
            final_df = pd.concat([final_df, new_df], ignore_index=True)
        
        print(f"최종 데이터 행 수: {len(final_df)}")  # 디버깅용
        
        try:
            final_df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"파일이 성공적으로 저장되었습니다: {file_path}")
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {str(e)}")


def get_historical_odds(target_date):
    """SQLite에서 특정 날짜의 배당률 데이터를 가져오는 함수"""
    # 현재 프로젝트 디렉토리 기준으로 상대 경로 사용
    conn = sqlite3.connect('Data/OddsData.sqlite')
    cursor = conn.cursor()
    
    # 날짜 형식을 SQLite 쿼리에 맞게 변환
    date_str = target_date.strftime('%Y-%m-%d')
    
    query = """
    SELECT Home, Away, ML_Home, ML_Away, OU
    FROM "odds_2024-25_new"
    WHERE Date = ?
    """
    
    cursor.execute(query, (date_str,))
    odds_data = cursor.fetchall()
    
    # odds 딕셔너리 형식으 변환
    odds = {}
    for home_team, away_team, ml_home, ml_away, ou in odds_data:
        key = f"{home_team}:{away_team}"
        odds[key] = {
            home_team: {'money_line_odds': ml_home},
            away_team: {'money_line_odds': ml_away},
            'under_over_odds': ou
        }
    
    conn.close()
    return odds


def main():
    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        # KST와 ET 시간 계산
        current_time_kst = datetime.now(ZoneInfo("Asia/Seoul"))
        current_time_et = current_time_kst.astimezone(ZoneInfo("America/New_York"))
        
        # 현재 ET 날짜 사용
        target_date = current_time_et.date()
        
        # ET 오후 11시 이후면 다음날 경기를 찾음 (당일 경기는 거의 끝남)
        if current_time_et.hour >= 21:
            target_date += timedelta(days=1)
        # ET 오전 4시 이전이면 당일 경기를 찾음 (전날 경기는 이미 끝남)
        elif current_time_et.hour < 4:
            pass
        # 그 외 시간대에는 당일 경기를 찾음
        else:
            pass

    print(f"검색하는 날짜 (ET): {target_date}")
    print(f"현재 시간 (KST): {datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"현재 시간 (ET): {datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 경기가 없을 경우 다음날 경기 찾기 (최대 7일)
    odds = None
    max_attempts = 7
    attempts = 0
    original_date = target_date
    
    while attempts < max_attempts:
        if args.odds:
            odds_provider = SbrOddsProvider(sportsbook=args.odds, target_date=target_date)
            odds = odds_provider.get_odds()
        elif target_date:
            odds = get_historical_odds(target_date)
            
        if odds and any(None not in (game_odds[team]['money_line_odds'] for team in game_odds if team != 'under_over_odds') 
                       for game_odds in odds.values()):
            break
            
        print(f"{target_date} (ET)에 유효한 배당이 없어 다음 날짜를 확인합니다.")
        target_date += timedelta(days=1)  # 다음 날짜로 이동
        attempts += 1
    
    if not odds or not any(None not in (game_odds[team]['money_line_odds'] for team in game_odds if team != 'under_over_odds') 
                          for game_odds in odds.values()):
        print(f"지난 {max_attempts}일 동안 유효한 배당이 없습니다.")
        return
    
    if odds:
        games = create_todays_games_from_odds(odds)
    else:
        if target_date:
            schedule_df = pd.read_csv('Data/nba-2024-UTC.csv', 
                                    parse_dates=['Date'],
                                    date_format='%d/%m/%Y %H:%M')
            # UTC 날짜를 ET로 변환 (UTC-4)
            schedule_df['Date'] = schedule_df['Date'] - pd.Timedelta(hours=4)
            days_games = schedule_df[schedule_df['Date'].dt.date == target_date]
            games = [(row['Home Team'], row['Away Team']) for _, row in days_games.iterrows()]
    data = get_json_data(data_url)
    df = to_data_frame(data)
    data, todays_games_uo, frame_ml, home_team_odds, away_team_odds = createTodaysGames(games, df, odds)

    # 데이터가 없는 경우 처리
    if data is None:
        print("분석할 경기가 없습니다. 프로그램을 종료합니다.")
        return

    if args.nn:
        print("------------Neural Network Model Predictions-----------")
        data = tf.keras.utils.normalize(data, axis=1)
        NN_Runner.nn_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, args.kc)
        print("-------------------------------------------------------")
    if args.xgb:
        print("---------------XGBoost Model Predictions---------------")
        predictions = XGBoost_Runner.xgb_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, args.kc)
        
        print("-------------------------------------------------------")
        print("예측 결과가 성공적으로 저장되었습니다.")
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
    
    try:
        main()
        print("예측 결과가 성공적으로 저장되었습니다.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")