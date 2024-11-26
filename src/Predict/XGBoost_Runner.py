import copy
import os

import numpy as np
import pandas as pd
import xgboost as xgb
from colorama import Fore, Style, init, deinit
from src.Utils import Expected_Value
from src.Utils import Kelly_Criterion as kc
from src.Utils.OddsConverter import american_to_decimal


# from src.Utils.Dictionaries import team_index_current
# from src.Utils.tools import get_json_data, to_data_frame, get_todays_games_json, create_todays_games
init()
xgb_ml = xgb.Booster()
xgb_ml.load_model('/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/Models/XGBoost_Models/XGBoost_68.7%_ML-4.json')
xgb_uo = xgb.Booster()
xgb_uo.load_model('/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/Models/XGBoost_Models/XGBoost_54.8%_UO-8.json')


def xgb_runner(data, todays_games_uo, frame_ml, games, home_team_odds, away_team_odds, kelly=False):
    ml_predictions_array = []
    ou_predictions_array = []

    for row in data:
        ml_predictions_array.append(xgb_ml.predict(xgb.DMatrix(np.array([row]))))

    frame_uo = copy.deepcopy(frame_ml)
    frame_uo['OU'] = np.asarray(todays_games_uo)
    data = frame_uo.values
    data = data.astype(float)

    for row in data:
        ou_predictions_array.append(xgb_uo.predict(xgb.DMatrix(np.array([row]))))

    count = 0
    for game in games:
        home_team = game[0]
        away_team = game[1]
        
        # 배당률 문자열 생성 (아메리칸 + 소수점)
        home_decimal = american_to_decimal(home_team_odds[count])
        away_decimal = american_to_decimal(away_team_odds[count])
        home_odds_str = f"({home_team_odds[count]:+d}/{home_decimal})" if home_team_odds[count] else ""
        away_odds_str = f"({away_team_odds[count]:+d}/{away_decimal})" if away_team_odds[count] else ""
        
        # 승리 확률이 더 높은 팀 표시 (밝은 초록색과 어두운 초록색 사용)
        if ml_predictions_array[count][0][1] >= ml_predictions_array[count][0][0]:
            print(f"{Fore.GREEN}{home_team}{Style.RESET_ALL} "
                  f"{Fore.LIGHTGREEN_EX}{home_odds_str} ({ml_predictions_array[count][0][1]*100:.1f}%){Style.RESET_ALL} vs "
                  f"{Fore.RED}{away_team}{Style.RESET_ALL} "
                  f"{Fore.LIGHTRED_EX}{away_odds_str}{Style.RESET_ALL}: ", end='')
        else:
            print(f"{Fore.RED}{home_team}{Style.RESET_ALL} "
                  f"{Fore.LIGHTRED_EX}{home_odds_str}{Style.RESET_ALL} vs "
                  f"{Fore.GREEN}{away_team}{Style.RESET_ALL} "
                  f"{Fore.LIGHTGREEN_EX}{away_odds_str} ({ml_predictions_array[count][0][0]*100:.1f}%){Style.RESET_ALL}: ", end='')
        
        # 오버/언더 예측 출력
        if ou_predictions_array[count][0][1] >= ou_predictions_array[count][0][0]:
            print(f"OVER {todays_games_uo[count]} ({ou_predictions_array[count][0][1]*100:.1f}%)")
        else:
            print(f"UNDER {todays_games_uo[count]} ({ou_predictions_array[count][0][0]*100:.1f}%)")
        
        count += 1

    if kelly:
        output_text = "------------기대값 & 켈리 기준-----------\n"
        print(output_text.strip())
        
        count = 0
        for game in games:
            home_team = game[0]
            away_team = game[1]
            ev_home = ev_away = 0
            if home_team_odds[count] and away_team_odds[count]:
                ev_home = float(Expected_Value.expected_value(ml_predictions_array[count][0][1], int(home_team_odds[count])))
                ev_away = float(Expected_Value.expected_value(ml_predictions_array[count][0][0], int(away_team_odds[count])))
            
            bankroll_descriptor = ' 뱅크롤 비율: '
            bankroll_fraction_home = bankroll_descriptor + str(kc.calculate_kelly_criterion(home_team_odds[count], ml_predictions_array[count][0][1])) + '%'
            bankroll_fraction_away = bankroll_descriptor + str(kc.calculate_kelly_criterion(away_team_odds[count], ml_predictions_array[count][0][0])) + '%'
            
            # 콘솔 출력 (색상 포함)
            expected_value_colors = {'home_color': Fore.GREEN if ev_home > 0 else Fore.RED,
                                   'away_color': Fore.GREEN if ev_away > 0 else Fore.RED}
            
            home_line = f"{home_team} 기대값: {expected_value_colors['home_color']}{ev_home:.2f}{Style.RESET_ALL}{bankroll_fraction_home}"
            away_line = f"{away_team} 기대값: {expected_value_colors['away_color']}{ev_away:.2f}{Style.RESET_ALL}{bankroll_fraction_away}"
            
            print(home_line)
            print(away_line)
            
            # 파일에 저장할 텍스트 (색상 코드 제외)
            output_text += f"{home_team} 기대값: {ev_home:.2f}{bankroll_fraction_home}\n"
            output_text += f"{away_team} 기대값: {ev_away:.2f}{bankroll_fraction_away}\n"
            
            count += 1
        
        # 파일 저장
        with open('/Users/burgerprince/Desktop/project/betting/NBA-Machine-Learning-Sports-Betting/model_output.txt', 'w') as f:
            f.write(output_text)
    else:
        print("---------------------기대값--------------------")
        count = 0
        for game in games:
            home_team = game[0]
            away_team = game[1]
            ev_home = ev_away = 0
            if home_team_odds[count] and away_team_odds[count]:
                ev_home = float(Expected_Value.expected_value(ml_predictions_array[count][0][1], int(home_team_odds[count])))
                ev_away = float(Expected_Value.expected_value(ml_predictions_array[count][0][0], int(away_team_odds[count])))
            expected_value_colors = {'home_color': Fore.GREEN if ev_home > 0 else Fore.RED,
                            'away_color': Fore.GREEN if ev_away > 0 else Fore.RED}
            bankroll_descriptor = ' 뱅크롤 비율: '
            bankroll_fraction_home = bankroll_descriptor + str(kc.calculate_kelly_criterion(home_team_odds[count], ml_predictions_array[count][0][1])) + '%'
            bankroll_fraction_away = bankroll_descriptor + str(kc.calculate_kelly_criterion(away_team_odds[count], ml_predictions_array[count][0][0])) + '%'

            print(home_team + ' 기대값: ' + expected_value_colors['home_color'] + str(ev_home) + Style.RESET_ALL + (bankroll_fraction_home if kelly else ''))
            print(away_team + ' 기대값: ' + expected_value_colors['away_color'] + str(ev_away) + Style.RESET_ALL + (bankroll_fraction_away if kelly else ''))
            count += 1

    deinit()
    
    # 예측 결과 반환
    return {
        'ml': ml_predictions_array,
        'ou': ou_predictions_array
    }
