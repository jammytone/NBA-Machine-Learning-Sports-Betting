def parse_data(data):
    """문자열 데이터를 DataFrame으로 변환"""
    import pandas as pd

    # 데이터를 줄 단위로 분리하고 빈 줄 제거
    lines = [line.strip() for line in data.strip().split('\n') if line.strip()]

    # 각 줄을 쉼표로 분리하여 리스트로 변환
    parsed_data = [line.split(',') for line in lines]

    # DataFrame 생성
    df = pd.DataFrame(parsed_data, columns=['date', 'team1', 'team2', 'predicted_winner',
                                          'probability', 'odds', 'result'])

    # probability를 float로 변환
    df['probability'] = df['probability'].astype(float)

    return df

def analyze_losing_streaks(df):
    """각 확률 구간별 연패 시퀀스 분석"""
    
    # Kelly Criterion 계산 함수 추가
    def calculate_kelly(probability, odds):
        """켈리 기준 계산"""
        win_prob = probability
        lose_prob = 1 - probability
        return (win_prob * (odds - 1) - lose_prob) / (odds - 1)
    
    # 데이터프레임에 켈리 기준값 추가
    df['kelly'] = df.apply(lambda x: calculate_kelly(x['probability'], float(x['odds'])), axis=1)
    
    # 확률 구간별로 데이터 분류
    high_prob = df[df['probability'] >= 0.7].reset_index(drop=True)
    mid_prob = df[(df['probability'] >= 0.6) & (df['probability'] < 0.7)].reset_index(drop=True)
    low_prob = df[df['probability'] < 0.6].reset_index(drop=True)

    def find_losing_streaks(data):
        current_streak = 0
        streaks = []
        streak_dates = []
        current_dates = []

        for idx, row in data.iterrows():
            if row['result'] == '패':
                current_streak += 1
                current_dates.append(row['date'])
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                    streak_dates.append(current_dates)
                current_streak = 0
                current_dates = []

        if current_streak > 0:
            streaks.append(current_streak)
            streak_dates.append(current_dates)

        return streaks, streak_dates

    high_streaks, high_dates = find_losing_streaks(high_prob)
    mid_streaks, mid_dates = find_losing_streaks(mid_prob)
    low_streaks, low_dates = find_losing_streaks(low_prob)

    print("\n=== 확률 구간별 연패 분석 ===")

    print("\n높은 확률 구간 (>= 0.7):")
    print(f"총 경기 수: {len(high_prob)}경기")
    print(f"승/패: {len(high_prob[high_prob['result']=='승'])}/{len(high_prob[high_prob['result']=='패'])}")
    print(f"승률: {len(high_prob[high_prob['result']=='승'])/len(high_prob)*100:.1f}%")
    print(f"모든 연패 시퀀스: {high_streaks}")
    for streak, dates in zip(high_streaks, high_dates):
        if streak >= 2:
            print(f"{streak}연패 발생 기간: {dates[0]} ~ {dates[-1]}")

    print("\n중간 확률 구간 (0.6-0.7):")
    print(f"총 경기 수: {len(mid_prob)}경기")
    print(f"승/패: {len(mid_prob[mid_prob['result']=='승'])}/{len(mid_prob[mid_prob['result']=='패'])}")
    print(f"승률: {len(mid_prob[mid_prob['result']=='승'])/len(mid_prob)*100:.1f}%")
    print(f"모든 연패 시퀀스: {mid_streaks}")
    for streak, dates in zip(mid_streaks, mid_dates):
        if streak >= 2:
            print(f"{streak}연패 발생 기간: {dates[0]} ~ {dates[-1]}")

    print("\n낮은 확률 구간 (< 0.6):")
    print(f"총 경기 수: {len(low_prob)}경기")
    print(f"승/패: {len(low_prob[low_prob['result']=='승'])}/{len(low_prob[low_prob['result']=='패'])}")
    print(f"승률: {len(low_prob[low_prob['result']=='승'])/len(low_prob)*100:.1f}%")
    print(f"모든 연패 시퀀스: {low_streaks}")
    for streak, dates in zip(low_streaks, low_dates):
        if streak >= 2:
            print(f"{streak}연패 발생 기간: {dates[0]} ~ {dates[-1]}")

    print("\n=== 마틴게일 수익 분석 ===")
    initial_bet = 100000

    def calculate_martingale_profits(data, multiplier):
        current_bet = initial_bet
        total_profit = 0
        max_loss = 0
        consecutive_losses = 0
        daily_profits = []  # 날짜별 수익금 추적

        for _, row in data.iterrows():
            daily_result = {
                'date': row['date'],
                'teams': f"{row['team1']} vs {row['team2']}",
                'bet_amount': current_bet,
                'odds': float(row['odds']),
                'result': row['result']
            }

            if row['result'] == '승':
                # 승리시 수익 계산 (배당률 * 베팅금액 - 베팅금액)
                profit = float(row['odds']) * current_bet - current_bet
                total_profit += profit
                current_bet = initial_bet  # 초기 베팅금액으로 리셋
                consecutive_losses = 0
                daily_result['profit'] = profit
            else:
                # 패배시 손실 계산
                total_profit -= current_bet
                consecutive_losses += 1
                max_loss = min(max_loss, total_profit)
                daily_result['profit'] = -current_bet
                current_bet *= multiplier  # 다음 베팅금액 증가

            daily_result['cumulative_profit'] = total_profit
            daily_profits.append(daily_result)

        return total_profit, max_loss, daily_profits

    for prob_range, data, multiplier in [
        ("높은 확률(>=0.7)", high_prob, 2.5),
        ("중간 확률(0.6-0.7)", mid_prob, 2.0),
        ("낮은 확률(<0.6)", low_prob, 1.5)
    ]:
        total_profit, max_loss, daily_profits = calculate_martingale_profits(data, multiplier)
        print(f"\n{prob_range} 구간:")
        print(f"총 수익: {int(total_profit):,}원")
        print(f"최대 손실액: {abs(int(max_loss)):,}원")
        print(f"수익률: {int(total_profit/initial_bet*100)}%")

        print("\n날짜별 상세 수익:")
        print(f"{'날짜':^10} {'경기':^35} {'베팅금액':>12} {'배당률':>8} {'결과':^4} {'수익금':>12} {'누적수익':>12}")
        print("-" * 95)
        for daily in daily_profits:
            print(f"{daily['date']:^10} {daily['teams']:<35} {int(daily['bet_amount']):>12,} {daily['odds']:>8.2f} {daily['result']:^4} {int(daily['profit']):>12,} {int(daily['cumulative_profit']):>12,}")
        print("-" * 95)

    print("\n=== 마틴게일 필요 자금 분석 ===")
    initial_bet = 100000
    for prob_range, streaks in [("높은 확률", high_streaks), ("중간 확률", mid_streaks), ("낮은 확률", low_streaks)]:
        if streaks:
            max_streak = max(streaks)
            if prob_range == "높은 확률":
                multiplier = 2.5
            elif prob_range == "중간 확률":
                multiplier = 2.0
            else:
                multiplier = 1.5

            required_money = initial_bet * (multiplier ** max_streak - 1) / (multiplier - 1)
            print(f"\n{prob_range} 구간:")
            print(f"최대 연패: {max_streak}회")
            print(f"필요 자금: {required_money:,.0f}원")

            # 연패별 베팅금액 시뮬레이션
            bet = initial_bet
            print("연패시 베팅금액 시퀀스:")
            for i in range(max_streak):
                print(f"{i+1}연패: {bet:,.0f}원")
                bet *= multiplier

    print("\n=== 하프켈리 기준 수익률 분석 ===")
    initial_bank = 10000000  # 1천만원 초기자금
    
    def calculate_kelly_profits(data):
        bank = initial_bank
        daily_profits = []
        
        for _, row in data.iterrows():
            kelly = row['kelly'] * 0.5  # 하프켈리 적용
            odds = float(row['odds'])
            
            # 켈리 비율이 양수일 때만 베팅
            if kelly > 0:
                bet_amount = bank * kelly
                daily_result = {
                    'date': row['date'],
                    'teams': f"{row['team1']} vs {row['team2']}",
                    'kelly': kelly,  # 하프켈리 값 저장
                    'full_kelly': kelly * 2,  # 원래 켈리값도 참고용으로 저장
                    'bet_amount': bet_amount,
                    'odds': odds,
                    'result': row['result']
                }
                
                if row['result'] == '승':
                    profit = bet_amount * (odds - 1)
                    bank += profit
                    daily_result['profit'] = profit
                else:
                    bank -= bet_amount
                    daily_result['profit'] = -bet_amount
                
                daily_result['current_bank'] = bank
                daily_profits.append(daily_result)
        
        return bank - initial_bank, daily_profits

    for prob_range, data in [
        ("높은 확률(>=0.7)", high_prob),
        ("중간 확률(0.6-0.7)", mid_prob),
        ("낮은 확률(<0.6)", low_prob)
    ]:
        total_profit, daily_profits = calculate_kelly_profits(data)
        print(f"\n{prob_range} 구간:")
        print(f"총 수익: {int(total_profit):,}원")
        print(f"수익률: {total_profit/initial_bank*100:.1f}%")
        
        if daily_profits:
            min_bank = min(p['current_bank'] for p in daily_profits)
            max_drawdown = initial_bank - min_bank
            print(f"최대 손실액: {int(max_drawdown):,}원")
            
            print("\n주요 베팅 내역:")
            print(f"{'날짜':^10} {'경기':^35} {'하프켈리':>8} {'풀켈리':>8} {'베팅금액':>12} {'결과':^4} {'수익금':>12} {'잔액':>12}")
            print("-" * 103)
            for daily in daily_profits:
                print(f"{daily['date']:^10} {daily['teams']:<35} {daily['kelly']:>7.1%} {daily['full_kelly']:>7.1%} {int(daily['bet_amount']):>12,} {daily['result']:^4} {int(daily['profit']):>12,} {int(daily['current_bank']):>12,}")
            print("-" * 103)

    # 사용자 경험 개선을 위한 요약 정보 출력
    print("\n=== 전체 요약 ===")
    print(f"총 분석 기간: {df['date'].min()} ~ {df['date'].max()}")
    print(f"총 경기 수: {len(df)}경기")
    print(f"전체 승률: {len(df[df['result']=='승'])/len(df):.1%}")
    print(f"평균 배당률: {df['odds'].astype(float).mean():.2f}")
    print(f"평균 켈리 비율: {df['kelly'].mean():.2%}")

# 먼저 데이터 정의
data = """
10/24,Detroit Pistons,Indiana Pacers,Indiana Pacers,0.708,1.48,승
10/24,Philadelphia 76ers,Milwaukee Bucks,Philadelphia 76ers,0.529,2.48,패
10/24,Houston Rockets,Charlotte Hornets,Houston Rockets,0.752,1.33,패
10/24,New Orleans Pelicans,Chicago Bulls,New Orleans Pelicans,0.746,1.45,승
10/24,Utah Jazz,Memphis Grizzlies,Utah Jazz,0.514,2.2,패
10/24,LA Clippers,Phoenix Suns,LA Clippers,0.611,2.72,패
10/24,Portland Trail Blazers,Golden State Warriors,Golden State Warriors,0.757,1.39,승
10/25,Sacramento Kings,Minnesota Timberwolves,Minnesota Timberwolves,0.571,1.85,승
10/26,Toronto Raptors,Philadelphia 76ers,Philadelphia 76ers,0.708,1.57,패
10/27,Charlotte Hornets,Miami Heat,Miami Heat,0.715,1.57,승
10/27,Memphis Grizzlies,Orlando Magic,Orlando Magic,0.715,1.81,패
10/27,San Antonio Spurs,Houston Rockets,Houston Rockets,0.643,1.77,패
10/27,Phoenix Suns,Dallas Mavericks,Phoenix Suns,0.59,1.82,승
10/28,Portland Trail Blazers,New Orleans Pelicans,New Orleans Pelicans,0.782,1.41,패
10/29,Orlando Magic,Indiana Pacers,Indiana Pacers,0.502,3.15,패
10/29,Miami Heat,Detroit Pistons,Miami Heat,0.795,1.3,승
10/29,New York Knicks,Cleveland Cavaliers,New York Knicks,0.624,1.63,패
10/29,Memphis Grizzlies,Chicago Bulls,Chicago Bulls,0.671,3.25,승
10/29,San Antonio Spurs,Houston Rockets,Houston Rockets,0.643,1.68,승
10/29,Phoenix Suns,Los Angeles Lakers,Phoenix Suns,0.627,1.68,승
10/30,Brooklyn Nets,Denver Nuggets,Brooklyn Nets,0.67,2.88,패
10/30,Golden State Warriors,New Orleans Pelicans,Golden State Warriors,0.724,2.18,승
10/31,Philadelphia 76ers,Detroit Pistons,Detroit Pistons,0.559,2.52,승
10/31,Cleveland Cavaliers,Los Angeles Lakers,Cleveland Cavaliers,0.706,1.48,승
10/31,Miami Heat,New York Knicks,Miami Heat,0.581,2.12,패
10/31,Golden State Warriors,New Orleans Pelicans,Golden State Warriors,0.692,1.7,승
11/1,Memphis Grizzlies,Milwaukee Bucks,Memphis Grizzlies,0.551,2.88,승
11/1,Utah Jazz,San Antonio Spurs,San Antonio Spurs,0.592,2.1,승
11/01,LA Clippers,Phoenix Suns,LA Clippers,0.508,2.66,패
11/02,Brooklyn Nets,Chicago Bulls,Brooklyn Nets,0.64,1.74,승
11/02,New Orleans Pelicans,Indiana Pacers,New Orleans Pelicans,0.519,2.36,승
11/02,Minnesota Timberwolves,Denver Nuggets,Minnesota Timberwolves,0.673,1.54,승
11/03,Charlotte Hornets,Boston Celtics,Charlotte Hornets,0.506,5,패
11/03,Philadelphia 76ers,Memphis Grizzlies,Memphis Grizzlies,0.63,1.93,승
11/03,Milwaukee Bucks,Cleveland Cavaliers,Cleveland Cavaliers,0.637,2.02,승
11/03,Washington Wizards,Miami Heat,Washington Wizards,0.529,4.3,패
11/04,Brooklyn Nets,Detroit Pistons,Brooklyn Nets,0.731,1.65,패
11/05,Cleveland Cavaliers,Milwaukee Bucks,Cleveland Cavaliers,0.808,1.38,승
11/05,Brooklyn Nets,Memphis Grizzlies,Brooklyn Nets,0.551,2.48,승
11/05,Miami Heat,Sacramento Kings,Sacramento Kings,0.564,1.86,승
11/05,Chicago Bulls,Utah Jazz,Chicago Bulls,0.836,1.3,패
11/05,Houston Rockets,New York Knicks,New York Knicks,0.577,1.76,패
11/05,New Orleans Pelicans,Portland Trail Blazers,New Orleans Pelicans,0.6,1.74,패
11/05,Dallas Mavericks,Indiana Pacers,Dallas Mavericks,0.704,1.47,패
11/07,Charlotte Hornets,Detroit Pistons,Detroit Pistons,0.598,1.79,패
11/07,Memphis Grizzlies,Los Angeles Lakers,Memphis Grizzlies,0.632,1.86,승
11/07,Phoenix Suns,Miami Heat,Phoenix Suns,0.708,1.53,승
11/07,LA Clippers,Philadelphia 76ers,LA Clippers,0.745,1.83,승
11/08,San Antonio Spurs,Portland Trail Blazers,San Antonio Spurs,0.737,1.58,승
11/09,Detroit Pistons,Atlanta Hawks,Detroit Pistons,0.563,1.82,승
11/09,Dallas Mavericks,Phoenix Suns,Dallas Mavericks,0.651,1.72,패
11/10,San Antonio Spurs,Utah Jazz,San Antonio Spurs,0.827,1.41,패
11/11,Detroit Pistons,Houston Rockets,Detroit Pistons,0.513,2.62,패
11/11,Philadelphia 76ers,Charlotte Hornets,Charlotte Hornets,0.606,2.36,패
11/11,Portland Trail Blazers,Memphis Grizzlies,Memphis Grizzlies,0.7,1.82,승
11/12,New Orleans Pelicans,Brooklyn Nets,Brooklyn Nets,0.62,1.85,승
11/13,Detroit Pistons,Miami Heat,Detroit Pistons,0.504,2.04,승
11/13,Philadelphia 76ers,New York Knicks,New York Knicks,0.688,1.64,승
11/13,Utah Jazz,Phoenix Suns,Phoenix Suns,0.718,1.43,승
11/13,Golden State Warriors,Dallas Mavericks,Golden State Warriors,0.592,1.69,승
11/14,Orlando Magic,Indiana Pacers,Orlando Magic,0.562,2.04,승
11/14,Los Angeles Lakers,Memphis Grizzlies,Memphis Grizzlies,0.606,3.35,패
11/16,Orlando Magic,Philadelphia 76ers,Orlando Magic,0.739,1.7,승
11/16,San Antonio Spurs,Los Angeles Lakers,San Antonio Spurs,0.604,2.18,패
11/16,New Orleans Pelicans,Denver Nuggets,Denver Nuggets,0.689,1.65,패
11/16,Sacramento Kings,Minnesota Timberwolves,Sacramento Kings,0.654,2.08,패
11/17,Charlotte Hornets,Milwaukee Bucks,Charlotte Hornets,0.533,2.42,승
11/18,Oklahoma City Thunder,Dallas Mavericks,Oklahoma City Thunder,0.763,1.34,패
11/19,Detroit Pistons,Chicago Bulls,Detroit Pistons,0.746,1.57,패
11/19,Miami Heat,Philadelphia 76ers,Miami Heat,0.676,1.66,승
11/19,Milwaukee Bucks,Houston Rockets,Houston Rockets,0.506,2.42,패
11/19,Sacramento Kings,Atlanta Hawks,Sacramento Kings,0.711,1.55,패
11/20,Boston Celtics,Cleveland Cavaliers,Cleveland Cavaliers,0.634,2.88,패
11/21,Memphis Grizzlies,Philadelphia 76ers,Memphis Grizzlies,0.811,2.42,승
11/22,Charlotte Hornets,Detroit Pistons,Detroit Pistons,0.564,1.89,패
11/22,San Antonio Spurs,Utah Jazz,San Antonio Spurs,0.776,1.68,승
11/23,Philadelphia 76ers,Brooklyn Nets,Brooklyn Nets,0.541,2.48,패
11/23,Chicago Bulls,Atlanta Hawks,Atlanta Hawks,0.569,1.86,패
11/23,Denver Nuggets,Dallas Mavericks,Dallas Mavericks,0.568,2.42,승
11/24,Chicago Bulls,Memphis Grizzlies,Memphis Grizzlies,0.674,1.51,승
11/24,San Antonio Spurs,Golden State Warriors,San Antonio Spurs,0.534,2.28,승
11/24,Los Angeles Lakers,Denver Nuggets,Los Angeles Lakers,0.72,1.54,패
11/25,Philadelphia 76ers,LA Clippers,LA Clippers,0.642,1.77,승
11/25,Miami Heat,Dallas Mavericks,Dallas Mavericks,0.588,2.24,패
11/26,Indiana Pacers,New Orleans Pelicans,Indiana Pacers,0.712,1.43,승
11/26,Denver Nuggets,New York Knicks,New York Knicks,0.554,2.44,승
"""

# 그 다음 분석 실행
df = parse_data(data)
analyze_losing_streaks(df)
