import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
from pathlib import Path

# 스타일 및 설정
st.set_page_config(
    page_title="NBA 베팅 예측 대시보드",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전역 CSS 스타일 적용
st.markdown("""
    <style>
    .stMetric {
        background-color: #1f1f1f !important;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .metric-value {
        color: #ffffff !important;
    }
    .metric-label {
        color: #cccccc !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 5px;
    }
    .dataframe {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 세션 스테이트 초기화
if 'bankroll_jaehoon' not in st.session_state:
    st.session_state.bankroll_jaehoon = 1000000  # 100만원
if 'bankroll_kyungnam' not in st.session_state:
    st.session_state.bankroll_kyungnam = 1000000  # 100만원

def load_predictions():
    """현재 예측 결과를 가져오는 함수"""
    try:
        with open('predictions.json', 'r') as f:
            predictions = json.load(f)
        return predictions
    except FileNotFoundError:
        return {
            "games": []
        }

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

def load_history():
    """과거 예측 결과와 수익률을 가져오는 함수"""
    start_date = "2024-11-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    date_range = pd.date_range(start=start_date, end=end_date)
    
    # 베팅 히스토리 로드
    betting_history = load_betting_history()
    
    # 켈리 비율 선택에 따른 뱅크롤 변화 계산
    use_half_kelly = st.session_state.get('kelly_type', "하프 켈리") == "하프 켈리"
    jaehoon_changes = calculate_bankroll_changes(betting_history, st.session_state.bankroll_jaehoon, "jaehoon", use_half_kelly)
    kyungnam_changes = calculate_bankroll_changes(betting_history, st.session_state.bankroll_kyungnam, "kyungnam", use_half_kelly)
    
    # 적중률 계산
    jaehoon_win_rates = calculate_win_rates(betting_history, "jaehoon")
    kyungnam_win_rates = calculate_win_rates(betting_history, "kyungnam")
    
    # 날짜별 데이터 초기화
    jaehoon_data = {}
    kyungnam_data = {}
    
    # 모든 날짜에 대해 기본값 설정
    for date in date_range:
        date_str = date.strftime("%Y-%m-%d")
        jaehoon_data[date_str] = {
            "bankroll": st.session_state.bankroll_jaehoon,
            "profit_rate": 0.0,
            "win_rate": 0.0
        }
        kyungnam_data[date_str] = {
            "bankroll": st.session_state.bankroll_kyungnam,
            "profit_rate": 0.0,
            "win_rate": 0.0
        }
    
    # 변화 데이터 적용
    for change in jaehoon_changes:
        date = change["date"]
        if date in jaehoon_data:
            jaehoon_data[date]["bankroll"] = change["bankroll"]
            jaehoon_data[date]["profit_rate"] = change["profit_rate"]
    
    for change in kyungnam_changes:
        date = change["date"]
        if date in kyungnam_data:
            kyungnam_data[date]["bankroll"] = change["bankroll"]
            kyungnam_data[date]["profit_rate"] = change["profit_rate"]
    
    # 적중률 데이터 적용
    for date, stats in jaehoon_win_rates.items():
        if date in jaehoon_data and stats["total"] > 0:
            jaehoon_data[date]["win_rate"] = (stats["wins"] / stats["total"]) * 100
    
    for date, stats in kyungnam_win_rates.items():
        if date in kyungnam_data and stats["total"] > 0:
            kyungnam_data[date]["win_rate"] = (stats["wins"] / stats["total"]) * 100
    
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

# 탭 생성
tab1, tab2, tab3 = st.tabs(["오늘의 예측", "수익률 트래킹", "통계 분석"])

with tab1:
    st.header("오늘의 경기 예측")
    
    # 켈리 비율 선택
    kelly_type = st.radio(
        "켈리 비율 선택",
        ["풀 켈리", "하프 켈리"],
        horizontal=True
    )
    
    # 예측 데이터 로드
    predictions = load_predictions()
    
    # 예측 결과를 데이터프레임으로 변환
    pred_df = pd.DataFrame(predictions["games"])
    
    # 선택된 켈리 비율에 따라 컬럼 구성
    kelly_column = "kelly" if kelly_type == "풀 켈리" else "half_kelly"
    kelly_label = "켈리 비율" if kelly_type == "풀 켈리" else "하프 켈리 비율"
    
    # 스타일이 적용된 테이블로 표시
    st.dataframe(
        pred_df,
        column_config={
            "teams": "경기",
            "win_prediction": "승리 예측",
            "ou_prediction": "오버/언더",
            kelly_column: kelly_label,
            "expected_value": "기대값"
        },
        hide_index=True,
    )

with tab2:
    st.header("수익률 트래킹")
    
    # 사용자 선택
    selected_user = st.radio(
        "사용자 선택",
        ["재훈", "경남"],
        horizontal=True
    )
    
    # 베팅 기록 표시
    st.subheader("베팅 기록")
    betting_history = load_betting_history()
    
    if betting_history["bets"]:
        # 날짜별로 그룹화
        dates = {}
        for bet in betting_history["bets"]:
            date = bet["date"]
            if date not in dates:
                dates[date] = []
            dates[date].append(bet)
        
        # 날짜별로 표시
        for date in sorted(dates.keys(), reverse=True):
            st.write(f"📅 {date}")
            
            # 해당 날짜의 베팅들을 표로 표시
            bet_data = []
            for bet in dates[date]:
                bet_data.append({
                    "팀": bet["team"],
                    "배당": bet["odds"],
                    "비중": f"{bet['kelly']}%",
                    "결과": "승" if bet["result"] == "win" else "패" if bet["result"] == "lose" else "미정"
                })
            
            df = pd.DataFrame(bet_data)
            st.dataframe(
                df,
                column_config={
                    "팀": st.column_config.TextColumn("팀"),
                    "배당": st.column_config.NumberColumn("배당"),
                    "비중": st.column_config.TextColumn("비중"),
                    "결과": st.column_config.TextColumn(
                        "결과",
                        help="베팅 결과",
                    ),
                },
                hide_index=True,
            )
            
            # 날짜별 통계
            wins = sum(1 for bet in dates[date] if bet["result"] == "win")
            total = sum(1 for bet in dates[date] if bet["result"] in ["win", "lose"])
            if total > 0:
                win_rate = (wins / total) * 100
                st.write(f"당일 적중률: {win_rate:.1f}% ({wins}/{total})")
            st.divider()
    else:
        st.info("아직 베팅 기록이 없습니다.")
    
    # 히스토리 데이터 로드
    jaehoon_df, kyungnam_df = load_history()
    history_df = jaehoon_df if selected_user == "재훈" else kyungnam_df
    current_bankroll = st.session_state.bankroll_jaehoon if selected_user == "재훈" else st.session_state.bankroll_kyungnam
    
    # 현재 뱅크롤 표시
    st.metric(
        label="현재 뱅크롤",
        value=f"{current_bankroll:,}원"
    )
    
    # 수익률 차트
    fig_profit = px.line(
        history_df, 
        x="날짜", 
        y="수익률",
        title=f"{selected_user}님의 누적 수익률 추이"
    )
    st.plotly_chart(fig_profit, use_container_width=True)
    
    # 뱅크롤 차트
    fig_bankroll = px.line(
        history_df,
        x="날짜",
        y="뱅크롤",
        title=f"{selected_user}님의 뱅크롤 변화 추이"
    )
    st.plotly_chart(fig_bankroll, use_container_width=True)
    
    # 적중률 차트
    fig_accuracy = px.line(
        history_df,
        x="날짜",
        y="적중률",
        title=f"{selected_user}님의 예측 적중률 추이"
    )
    st.plotly_chart(fig_accuracy, use_container_width=True)

with tab3:
    st.header("통계 분석")
    
    # 사용자별 통계
    jaehoon_stats = {
        "전체 적중률": "62.5%",
        "누적 수익률": "124.5%",
        "ROI": "24.5%"
    }
    
    kyungnam_stats = {
        "전체 적중률": "58.3%",
        "누적 수익률": "115.2%",
        "ROI": "15.2%"
    }
    
    selected_stats = jaehoon_stats if selected_user == "재훈" else kyungnam_stats
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="전체 적중률",
            value=selected_stats["전체 적중률"],
            delta="2.1%"
        )
    
    with col2:
        st.metric(
            label="누적 수익률",
            value=selected_stats["누적 수익률"],
            delta="5.2%"
        )
    
    with col3:
        st.metric(
            label="ROI",
            value=selected_stats["ROI"],
            delta="1.2%"
        )

# CSS 스타일 적용
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)