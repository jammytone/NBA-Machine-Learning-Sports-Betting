import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
from pathlib import Path
from pytz import timezone, utc
from zoneinfo import ZoneInfo
from src.Utils.Dictionaries import team_index_current

# 전체적인 테마 설정
st.set_page_config(
    page_title="NBA 베팅 분석 대시보드",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/project',
        'Report a bug': "https://github.com/yourusername/project/issues",
        'About': "NBA 경기 예측 및 베팅 분석을 위한 대시보드입니다."
    }
)

# 사용자 정의 CSS 스타일
st.markdown("""
<style>
    /* 카드형 컴포넌트 스타일 */
    .stMetric {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* 데이터프레임 스타일링 */
    .dataframe {
        background-color: #2d2d2d;
        border-radius: 8px;
        font-size: 14px;
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        padding: 0.5rem;
        background-color: #1e1e1e;
        border-radius: 10px;
    }
    
    /* 버튼 스타일링 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #4CAF50;
        color: white;
    }
    
    /* 사이드바 스타일링 */
    .sidebar .sidebar-content {
        background-color: #1e1e1e;
    }
    
    /* 경기 카드 스타일링 */
    .game-card {
        background-color: #2d2d2d;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #444;
    }
    
    .game-card h3 {
        color: #4CAF50;
        margin-bottom: 0.5rem;
    }
    
    .game-card p {
        margin: 0.25rem 0;
        color: #ddd;
    }
    
    /* 통계 카드 스타일링 */
    .stat-card {
        background-color: #1e1e1e;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    
    /* 필터 섹션 스타일링 */
    .filter-section {
        background-color: #2d2d2d;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    /* 차트 컨테이너 스타일링 */
    .chart-container {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 세션 스테이트 초기화
if 'bankroll_jaehoon' not in st.session_state:
    st.session_state.bankroll_jaehoon = 1000000
if 'bankroll_kyungnam' not in st.session_state:
    st.session_state.bankroll_kyungnam = 1000000

def load_predictions():
    """현재 예측 결과를 가져오는 함수"""
    try:
        with open('predictions.json', 'r') as f:
            predictions = json.load(f)
            
        # 각 게임의 홈/어웨이 팀 켈리 기준 출력
        for game in predictions["games"]:
            print(f"{game['teams']}:")
            print(f"Home Team ({game['home_team']}):")
            print(f"  Full Kelly: {game['home_kelly']}")
            print(f"  Half Kelly: {game['home_half_kelly']}")
            print(f"Away Team ({game['away_team']}):")
            print(f"  Full Kelly: {game['away_kelly']}")
            print(f"  Half Kelly: {game['away_half_kelly']}")
            
        return predictions
    except FileNotFoundError:
        return {
            "games": []
        }
    
def train_prediction_model(betting_history):
    """간단한 승률 예측 모델"""
    if not betting_history["bets"]:
        return {"accuracy": 0, "precision": 0, "recall": 0}
        
    # 여기에 실제 모델 학습 코드 추가
    return {"accuracy": 0, "precision": 0, "recall": 0}

def plot_model_performance(metrics):
    """모델 성능 시각화"""
    if all(v == 0 for v in metrics.values()):
        st.warning("모델 성능 분석을 위한 데이터가 충분하지 않습니다.")
        return
        
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("정확도", f"{metrics['accuracy']:.1f}%")
    with col2:
        st.metric("정밀도", f"{metrics['precision']:.1f}%")
    with col3:
        st.metric("재현율", f"{metrics['recall']:.1f}%")

def plot_win_rate_calendar(betting_history):
    """승률 캘린더 히트맵"""
    calendar_data = prepare_calendar_data(betting_history)
    
    fig = px.imshow(
        calendar_data,
        title="일별 승률 히트맵",
        color_continuous_scale="RdYlGn",
        aspect="auto"
    )
    
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e"
    )
    
    return fig

def calculate_bankroll_changes(betting_history, initial_bankroll, user, use_half_kelly=False):
    """베팅 기록을 바탕으로 뱅크롤 변화 계산"""
    changes = []
    current_bankroll = initial_bankroll
    
    # 사용자의 베팅만 필터링
    user_bets = [bet for bet in betting_history["bets"] if bet["user"] == user]
    
    for bet in user_bets:
        kelly = bet["kelly"] / 2 if use_half_kelly else bet["kelly"]  # 하프켈리 적용
        if bet["result"] == "win":
            if bet["odds"] > 0:
                win_amount = (kelly / 100) * current_bankroll * (bet["odds"] / 100)
            else:
                win_amount = (kelly / 100) * current_bankroll * (100 / abs(bet["odds"]))
            current_bankroll += win_amount
        elif bet["result"] == "lose":
            loss_amount = (kelly / 100) * current_bankroll
            current_bankroll -= loss_amount
        
        changes.append({
            "date": bet["date"],
            "bankroll": current_bankroll,
            "profit_rate": ((current_bankroll - initial_bankroll) / initial_bankroll) * 100
        })
    
    return changes

def calculate_win_rates(betting_history, user):
    """날짜별 적중률 계산"""
    win_rates = {}
    user_bets = [bet for bet in betting_history["bets"] if bet["user"] == user]
    
    for bet in user_bets:
        date = bet["date"]
        if date not in win_rates:
            win_rates[date] = {"wins": 0, "total": 0}
        
        if bet["result"] == "win":
            win_rates[date]["wins"] += 1
        if bet["result"] in ["win", "lose"]:
            win_rates[date]["total"] += 1
    
    return win_rates

def setup_notifications():
    """실시간 알림 설정"""
    st.sidebar.header("알림 설정")
    
    notify_settings = {
        "승률 임계값": st.sidebar.number_input(
            "승률 임계값 (%)", 
            min_value=0, 
            max_value=100, 
            value=60
        ),
        "최소 배당": st.sidebar.number_input(
            "최소 배당", 
            min_value=1.0, 
            value=1.5
        ),
        "켈리 비율": st.sidebar.number_input(
            "최소 켈리 비율 (%)", 
            min_value=0, 
            max_value=100, 
            value=5
        )
    }
    
    return notify_settings

def check_notifications(predictions, notify_settings):
    """알림 조건 체크"""
    notifications = []
    
    for game in predictions["games"]:
        if (float(game["win_prediction"].split("(")[1].strip("%)")) >= notify_settings["승 임계값"] and
            float(game["kelly"].strip("%")) >= notify_settings["켈리 비율"]):
            notifications.append({
                "type": "HIGH_CONFIDENCE",
                "message": f"높은 승률 경기 발견: {game['teams']}"
            })
    
    return notifications

def calculate_total_profit_rate(user):
    """총 수익률 계산"""
    history = load_betting_history()
    user_bets = [bet for bet in history["bets"] if bet["user"].lower() == user.lower()]
    
    if not user_bets:
        return 0.0
        
    initial_bankroll = st.session_state[f"bankroll_{user.lower()}"]
    current_bankroll = calculate_current_bankroll(user_bets, initial_bankroll)
    
    return round(((current_bankroll - initial_bankroll) / initial_bankroll) * 100, 2)

def calculate_average_win_rate(user):
    """평균 승률 계산"""
    history = load_betting_history()
    user_bets = [bet for bet in history["bets"] if bet["user"].lower() == user.lower()]
    
    if not user_bets:
        return 0.0
        
    wins = len([bet for bet in user_bets if bet["result"] == "win"])
    total = len([bet for bet in user_bets if bet["result"] in ["win", "lose"]])
    
    return round((wins / total) * 100, 2) if total > 0 else 0.0

def calculate_max_win_streak(user):
    """최대 연승 계산"""
    history = load_betting_history()
    user_bets = [bet for bet in history["bets"] if bet["user"].lower() == user.lower()]
    
    max_streak = current_streak = 0
    for bet in user_bets:
        if bet["result"] == "win":
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
            
    return max_streak

def calculate_roi(user):
    """투자수익률(ROI) 계산"""
    history = load_betting_history()
    user_bets = [bet for bet in history["bets"] if bet["user"].lower() == user.lower()]
    
    if not user_bets:
        return 0.0
    
    total_investment = 0
    total_returns = 0
    
    for bet in user_bets:
        kelly = bet["kelly"] / 100
        initial_bankroll = st.session_state[f"bankroll_{user.lower()}"]
        investment = kelly * initial_bankroll
        
        total_investment += investment
        if bet["result"] == "win":
            if bet["odds"] > 0:
                returns = investment * (bet["odds"] / 100)
            else:
                returns = investment * (100 / abs(bet["odds"]))
            total_returns += returns
    
    return round(((total_returns - total_investment) / total_investment) * 100, 2) if total_investment > 0 else 0.0

def calculate_team_stats(betting_history, team):
    """팀별 통계 계산"""
    team_stats = {
        "dates": [],
        "win_rates": [],
        "roi_values": [],
        "total_bets": 0,
        "wins": 0,
        "profit": 0
    }
    
    # 베팅 기록이 비어있으면 기본값 반환
    if not betting_history["bets"]:
        return team_stats
        
    # 해당 팀의 베팅만 필터링 (teams 대신 team 키 사용)
    team_bets = [bet for bet in betting_history["bets"] 
                if bet["team"] == team]
    
    for bet in team_bets:
        date = bet["date"]
        if date not in team_stats["dates"]:
            team_stats["dates"].append(date)
            
            # 해당 날짜의 승률 계산
            date_bets = [b for b in team_bets if b["date"] == date]
            wins = len([b for b in date_bets if b["result"] == "win"])
            total = len(date_bets)
            win_rate = (wins / total * 100) if total > 0 else 0
            team_stats["win_rates"].append(win_rate)
            
            # ROI 계산
            investment = sum(b["kelly"] for b in date_bets)
            returns = sum(b["profit"] if "profit" in b else 0 for b in date_bets)
            roi = ((returns - investment) / investment * 100) if investment > 0 else 0
            team_stats["roi_values"].append(roi)
        
        # 전체 통계 업데이트
        team_stats["total_bets"] += 1
        if bet["result"] == "win":
            team_stats["wins"] += 1
        team_stats["profit"] += bet["profit"] if "profit" in bet else 0
    
    return team_stats

def plot_team_win_rate(team_stats):
    """팀별 승률 차트"""
    # DataFrame 생성
    df = pd.DataFrame({
        'dates': team_stats["dates"],
        'win_rates': team_stats["win_rates"]
    })
    
    fig = px.line(
        df,  # DataFrame 사용
        x='dates',
        y='win_rates',
        title="팀별 승률 추이",
        template="plotly_dark",
        labels={"dates": "날짜", "win_rates": "승률 (%)"}
    )
    
    fig.update_layout(
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font=dict(color="white"),
        hovermode="x unified",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_team_roi(team_stats):
    """팀별 ROI 차트"""
    # DataFrame 생성
    df = pd.DataFrame({
        'dates': team_stats["dates"],
        'roi_values': team_stats["roi_values"]
    })
    
    fig = px.line(
        df,
        x='dates',
        y='roi_values',
        title="팀별 ROI 추이",
        template="plotly_dark",
        labels={"dates": "날짜", "roi_values": "ROI (%)"}
    )
    
    fig.update_layout(
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font=dict(color="white"),
        hovermode="x unified",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def load_history():
    """베팅 기록을 DataFrame으로 변환"""
    betting_history = load_betting_history()
    
    if not betting_history["bets"]:
        return pd.DataFrame(), pd.DataFrame()
        
    dates = sorted(list(set(bet["date"] for bet in betting_history["bets"])))
    date_range = pd.date_range(start=dates[0], end=dates[-1])
    
    # 사용자별 데이터 초기화 (영문 키 사용)
    jaehoon_data = {date.strftime("%Y-%m-%d"): {"profit_rate": 0, "bankroll": st.session_state.bankroll_jaehoon, "win_rate": 0} 
                    for date in date_range}
    kyungnam_data = {date.strftime("%Y-%m-%d"): {"profit_rate": 0, "bankroll": st.session_state.bankroll_kyungnam, "win_rate": 0} 
                    for date in date_range}
    
    # 데이터 채우기 (영문 키 사용)
    for user, data in [("jaehoon", jaehoon_data), ("kyungnam", kyungnam_data)]:
        bankroll_changes = calculate_bankroll_changes(betting_history, st.session_state[f"bankroll_{user}"], user)
        win_rates = calculate_win_rates(betting_history, user)
        
        for change in bankroll_changes:
            date = change["date"]
            data[date]["profit_rate"] = change["profit_rate"]
            data[date]["bankroll"] = change["bankroll"]
            
        for date, rates in win_rates.items():
            if rates["total"] > 0:
                data[date]["win_rate"] = (rates["wins"] / rates["total"]) * 100
    
    # DataFrame 생성
    jaehoon_df = pd.DataFrame({
        "날짜": date_range,
        "수익률": [jaehoon_data[date.strftime("%Y-%m-%d")]["profit_rate"] for date in date_range],
        "뱅크롤": [jaehoon_data[date.strftime("%Y-%m-%d")]["bankroll"] for date in date_range],
        "적중률": [jaehoon_data[date.strftime("%Y-%m-%d")]["win_rate"] for date in date_range]
    })
    
    kyungnam_df = pd.DataFrame({
        "날짜": date_range,
        "수익률": [kyungnam_data[date.strftime("%Y-%m-%d")]["profit_rate"] for date in date_range],
        "뱅크롤": [kyungnam_data[date.strftime("%Y-%m-%d")]["bankroll"] for date in date_range],
        "적중률": [kyungnam_data[date.strftime("%Y-%m-%d")]["win_rate"] for date in date_range]
    })
    
    return jaehoon_df, kyungnam_df

def load_betting_history():
    """베팅 기록을 로드하는 함수"""
    try:
        with open('betting_history.json', 'r') as f:
            history = json.load(f)
        return history
    except FileNotFoundError:
        return {"bets": []}

def prepare_calendar_data(betting_history):
    """캘린더 데이터 준비"""
    calendar_data = pd.DataFrame()
    
    # 베팅 기록에서 날짜별 승률 계산
    dates = []
    win_rates = []
    
    for bet in betting_history["bets"]:
        date = bet["date"]
        if date not in dates:
            dates.append(date)
            wins = len([b for b in betting_history["bets"] if b["date"] == date and b["result"] == "win"])
            total = len([b for b in betting_history["bets"] if b["date"] == date])
            win_rates.append((wins / total * 100) if total > 0 else 0)
    
    calendar_data["date"] = dates
    calendar_data["win_rate"] = win_rates
    calendar_data["date"] = pd.to_datetime(calendar_data["date"])
    
    # 피벗 테이블 생성
    calendar_matrix = calendar_data.pivot_table(
        values="win_rate",
        index=calendar_data["date"].dt.isocalendar().week,
        columns=calendar_data["date"].dt.isocalendar().day,
        aggfunc="mean"
    ).fillna(0)
    
    return calendar_matrix

def calculate_current_bankroll(bets, initial_bankroll):
    """현재 뱅크롤 계산"""
    current_bankroll = initial_bankroll
    
    for bet in bets:
        kelly = bet["kelly"]
        if bet["result"] == "win":
            if bet["odds"] > 0:
                win_amount = (kelly / 100) * current_bankroll * (bet["odds"] / 100)
            else:
                win_amount = (kelly / 100) * current_bankroll * (100 / abs(bet["odds"]))
            current_bankroll += win_amount
        elif bet["result"] == "lose":
            loss_amount = (kelly / 100) * current_bankroll
            current_bankroll -= loss_amount
    
    return current_bankroll

def american_to_decimal(american_odds):
    """미국식 배당을 소수점 배당으로 변환"""
    if american_odds >= 100:
        return round((american_odds / 100) + 1, 2)
    else:
        return round((100 / abs(american_odds)) + 1, 2)
    

def plot_profit_chart(history_df):
    """수익률 차트"""
    fig = px.line(
        history_df,
        x="날짜",
        y="수익률",
        title="수익률 추이",
        template="plotly_dark"
    )
    
    fig.update_layout(
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font=dict(color="white"),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor="#333"),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor="#333")
    )
    
    return fig

def calculate_correlations(betting_history):
    """상관관계 분석"""
    if not betting_history["bets"]:
        return pd.DataFrame()
        
    df = pd.DataFrame(betting_history["bets"])
    
    # 필요한 수치형 데이터만 선택
    numeric_columns = ["kelly", "odds"]
    if all(col in df.columns for col in numeric_columns):
        return df[numeric_columns].corr()
    
    return pd.DataFrame()

def plot_correlation_heatmap(correlation_matrix):
    """상관관계 히트맵"""
    if correlation_matrix.empty:
        st.warning("상관관계 분석을 위한 데이터가 충분하지 않습니다.")
        return
        
    fig = px.imshow(
        correlation_matrix,
        color_continuous_scale="RdBu",
        aspect="auto"
    )
    
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_betting_history():
    """베팅 기록 표시 및 결과 수동 업데이트"""
    st.header("베팅 기록")
    
    try:
        with open('betting_history.json', 'r') as f:
            history = json.load(f)
        
        # 데이터프레임으로 변환
        if not history["bets"]:
            st.warning("베팅 기록이 없습니다.")
            return
            
        df = pd.DataFrame(history["bets"])
        df = df.sort_values('date', ascending=False)  # 최신 기록이 위로
        
        # 각 베팅 기록을 표로 표시
        for idx, bet in df.iterrows():
            with st.container():
                cols = st.columns([2, 1, 1, 1, 1])
                
                # 날짜와 팀
                cols[0].markdown(f"**{bet['date']} - {bet['team']}**")
                
                # 배당
                cols[1].write(f"배당: {bet['odds']}")
                
                # 켈리 비율
                cols[2].write(f"켈리: {bet['kelly']}%")
                
                # 유저
                cols[3].write(f"유저: {bet['user']}")
                
                # 결과 선택 (드롭다운)
                new_result = cols[4].selectbox(
                    "결과",
                    options=["pending", "win", "lose"],
                    key=f"result_{bet['date']}_{bet['team']}",
                    index=["pending", "win", "lose"].index(bet['result'])
                )
                
                # 결과가 변경되면 저장
                if new_result != bet['result']:
                    history["bets"][idx]['result'] = new_result
                    with open('betting_history.json', 'w') as f:
                        json.dump(history, f, indent=4)
                    st.success("결과가 업데이트되었습니다.")
                    st.rerun()  # 페이지 새로고침
                
                # 구분선 추가
                st.divider()
        
        # 통계 요약
        st.subheader("베팅 통계")
        col1, col2, col3, col4 = st.columns(4)
        
        # 전체 베팅 수
        total_bets = len(df)
        col1.metric("전체 베팅", f"{total_bets}건")
        
        # 승리 수
        wins = len(df[df['result'] == 'win'])
        col2.metric("승리", f"{wins}건")
        
        # 승률
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        col3.metric("승률", f"{win_rate:.1f}%")
        
        # 진행중인 베팅
        pending = len(df[df['result'] == 'pending'])
        col4.metric("진행중", f"{pending}건")
                
    except FileNotFoundError:
        st.warning("베팅 기록이 없습니다.")

# 사이드바
st.sidebar.title("NBA 베팅 예측")

# 뱅크롤 설정
st.sidebar.header("뱅크롤 설정")
new_bankroll_jaehoon = st.sidebar.number_input(
    "재훈님 뱅크롤 (원)",
    min_value=0,
    value=st.session_state.bankroll_jaehoon,
    step=100000,
    format="%d"
)
new_bankroll_kyungnam = st.sidebar.number_input(
    "경남님 뱅크롤 (원)",
    min_value=0,
    value=st.session_state.bankroll_kyungnam,
    step=100000,
    format="%d"
)

# 뱅크롤 업데이트
if new_bankroll_jaehoon != st.session_state.bankroll_jaehoon:
    st.session_state.bankroll_jaehoon = new_bankroll_jaehoon
if new_bankroll_kyungnam != st.session_state.bankroll_kyungnam:
    st.session_state.bankroll_kyungnam = new_bankroll_kyungnam

selected_date = st.sidebar.date_input(
    "날짜 선택",
    datetime.now()
)

# 메인 페이지
st.title("🏀 NBA 베팅 예측 대시보드")

# 새로운 필터 옵션들
with st.sidebar:
    st.header("필터 설정")
    
    # # 날짜 범위 선택
    # date_range = st.date_input(
    #     "기간 선택",
    #     value=(datetime.now() - timedelta(days=30), datetime.now()),
    #     key="date_range"
    # )
    
    # # 최소 승률 필터
    # min_win_rate = st.slider(
    #     "최소 승률",
    #     min_value=0,
    #     max_value=100,
    #     value=50,
    #     step=5,
    #     key="min_win_rate"
    # )
    
    # # 배당률 범위 필터
    # odds_range = st.slider(
    #     "배당률 범위",
    #     min_value=1.0,
    #     max_value=5.0,
    #     value=(1.5, 3.0),
    #     step=0.1,
    #     key="odds_range"
    # )
    
    # # 켈리 기준 설정
    # kelly_options = st.radio(
    #     "켈리 기준",
    #     options=["풀 켈리", "하프 켈리", "쿼터 켈리"],
    #     key="kelly_criterion"
    # )

# 새로운 분석 탭 추가
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "오늘의 예측", 
    "수익률 분석", 
    "팀별 분석",
    "고급 통계",
    "베팅 기록"
])

# 오늘의 예측 탭
with tab1:
    st.header("오늘의 NBA 경기 예측")
    
    # 예측 결과 로드
    predictions = load_predictions()
    
    # 예측 결과 표시를 위한 3개의 컬럼 생성
    col1, col2, col3 = st.columns(3)
    
    for game in predictions["games"]:
        with col1:
            # 경기 카드 생성
            with st.container():
                st.markdown(f"""
                <div class="game-card">
                    <h3>{game['teams']}</h3>
                    <p>승리 예측: {game['win_prediction']}</p>
                    <p>오버/언더 예측: {game['ou_prediction']}</p>
                    <h4>홈팀 ({game['home_team']})</h4>
                    <p>전체 켈리: {game['home_kelly']}</p>
                    <p>하프 켈리: {game['home_half_kelly']}</p>
                    <h4>원정팀 ({game['away_team']})</h4>
                    <p>전체 켈리: {game['away_kelly']}</p>
                    <p>하프 켈리: {game['away_half_kelly']}</p>
                </div>
                """, unsafe_allow_html=True)

# 수익률 분석 탭
with tab2:
    st.header("베팅 수익률 분석")
    
    # 베팅 기록 로드 및 DataFrame 생성
    betting_history = load_betting_history()
    jaehoon_df, kyungnam_df = load_history()
    
    # 사용자 선택
    selected_user = st.radio(
        "분석할 사용자 선택",
        options=["재훈", "경남"],
        horizontal=True
    )
    
    # 기간별 분석 옵션
    analysis_period = st.selectbox(
        "분석 기간",
        options=["전체", "최근 1개월", "최근 3개월", "최근 6개월"]
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 수익률 차트
        st.subheader("수익률 추이")
        profit_chart = plot_profit_chart(jaehoon_df if selected_user == "재훈" else kyungnam_df)
        st.plotly_chart(profit_chart, use_container_width=True)
        
    with col2:
        # 승률 캘린더
        st.subheader("승률 캘린더")
        win_rate_chart = plot_win_rate_calendar(betting_history)
        st.plotly_chart(win_rate_chart, use_container_width=True)
    
    # 주요 통계 지표
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 수익률", f"{calculate_total_profit_rate(selected_user)}%")
    with col2:
        st.metric("평균 승률", f"{calculate_average_win_rate(selected_user)}%")
    with col3:
        st.metric("최대 연승", f"{calculate_max_win_streak(selected_user)}회")
    with col4:
        st.metric("ROI", f"{calculate_roi(selected_user)}%")

# 팀별 분석 탭
with tab3:
    st.header("팀별 성과 분석")
    
    # 팀 선택
    selected_team = st.selectbox(
        "팀 선택",
        options=list(team_index_current.keys())
    )
    
    # 팀별 통계 계산
    team_stats = calculate_team_stats(betting_history, selected_team)
    
    # 요약 통계
    col1, col2, col3 = st.columns(3)
    with col1:
        win_rate = (team_stats["wins"] / team_stats["total_bets"] * 100) if team_stats["total_bets"] > 0 else 0
        st.metric("전체 승률", f"{win_rate:.1f}%")
    with col2:
        st.metric("총 베팅 수", f"{team_stats['total_bets']}회")
    with col3:
        st.metric("총 수익", f"{team_stats['profit']:,.0f}원")
    
    # 차트 표시
    col1, col2 = st.columns(2)
    with col1:
        plot_team_win_rate(team_stats)
    with col2:
        plot_team_roi(team_stats)

# 고급 통계 탭
with tab4:
    st.header("고급 통계 분석")
    
    # 상관관계 분석
    correlation_matrix = calculate_correlations(betting_history)
    plot_correlation_heatmap(correlation_matrix)
    
    # 승률 예측 모델
    st.subheader("승률 예측 모델")
    model_metrics = train_prediction_model(betting_history)
    plot_model_performance(model_metrics)

# 베팅 기록 탭
with tab5:
    show_betting_history()





