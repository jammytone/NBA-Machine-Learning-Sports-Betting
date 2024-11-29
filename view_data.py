import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# 페이지 설정
st.set_page_config(layout="wide")  # 전체 페이지를 와이드 모드로 설정

def load_data():
    df = pd.read_csv('NBA_승패_최종 - 승패.csv')
    # 숫자형 컬럼 변환
    numeric_columns = ['확률', '배당', '켈리 비율', '진입', '자본금 변화', '날짜별 초기 잔액', '잔액']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace('%', '').str.replace(',', ''), errors='coerce')
    return df

def load_model_predictions():
    predictions = []
    
    try:
        with open('model_output.txt', 'r') as f:
            lines = f.readlines()
            reading_predictions = False
            
            for line in lines:
                if '기대값 & 켈리 기준' in line:
                    reading_predictions = True
                    continue
                    
                if reading_predictions and line.strip():
                    # 예: "Washington Wizards 기대값: 14.02 뱅크롤 비율: 8.45%"
                    parts = line.strip().split()
                    if len(parts) >= 7:  # 팀명이 두 단어인 경우도 처리
                        team = ' '.join(parts[:-6])  # 팀명
                        ev = float(parts[-4])  # 기대값
                        kelly = float(parts[-1].rstrip('%'))  # 켈리 비율
                        
                        predictions.append({
                            '팀': team,
                            '기대값': ev,
                            '켈리 비율': kelly
                        })
    except FileNotFoundError:
        return pd.DataFrame()
    
    return pd.DataFrame(predictions)

def main():
    st.title('NBA 베팅 데이터 분석')
    
    # 데이터 로드
    df = load_data()
    model_predictions = load_model_predictions()
    
    # 사이드바에 필터 옵션 추가
    st.sidebar.title('필터 옵션')
    dates = sorted(df['날짜'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox('날짜 선택', dates, index=0)
    
    # 메인 컨테이너
    main_container = st.container()
    
    with main_container:
        # 상단 메트릭스 (3열)
        col1, col2, col3 = st.columns(3)
        
        current_balance = df['잔액'].iloc[-1]
        initial_balance = 1000
        profit_percentage = ((current_balance - initial_balance) / initial_balance) * 100
        
        col1.metric(
            "현재 잔액", 
            f"₩{current_balance:,.0f}",
            f"{profit_percentage:+.1f}%"
        )
        
        # 승패 통계
        win_count = len(df[df['결과'] == '승'])
        lose_count = len(df[df['결과'] == '패'])
        total_games = win_count + lose_count
        win_rate = (win_count / total_games * 100) if total_games > 0 else 0
        
        col2.metric(
            "승률", 
            f"{win_rate:.1f}%",
            f"{win_count}승 {lose_count}패"
        )
        
        # 당일 수익
        if selected_date:
            daily_data = df[df['날짜'] == selected_date]
            daily_profit = daily_data['자본금 변화'].sum()
            daily_profit_pct = (daily_profit / daily_data['날짜별 초기 잔액'].iloc[0] * 100) if not daily_data.empty else 0
            
            col3.metric(
                "당일 수익", 
                f"₩{daily_profit:,.0f}",
                f"{daily_profit_pct:+.1f}%"
            )
        
        # 잔액 추이 그래프
        st.subheader('잔액 추이')
        fig = px.line(df, x='날짜', y='잔액', title='잔액 변화')
        fig.update_layout(
            xaxis_title="날짜",
            yaxis_title="잔액",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 선택된 날짜의 데이터 표시
        if selected_date:
            st.subheader(f'{selected_date} 경기 분석')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("실제 베팅 데이터")
                daily_data = df[df['날짜'] == selected_date].copy()
                
                # 데이터 포맷팅
                daily_data['확률'] = daily_data['확률'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else '')
                daily_data['켈리 비율'] = daily_data['켈리 비율'].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else '')
                daily_data['진입'] = daily_data['진입'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else '')
                daily_data['자본금 변화'] = daily_data['자본금 변화'].apply(lambda x: f"{x:+,.0f}" if pd.notnull(x) else '')
                
                st.dataframe(daily_data, use_container_width=True)
            
            with col2:
                st.subheader("모델 예측")
                if not model_predictions.empty:
                    formatted_predictions = model_predictions.copy()
                    formatted_predictions['기대값'] = formatted_predictions['기대값'].apply(lambda x: f"{x:.3f}")
                    formatted_predictions['켈리 비율'] = formatted_predictions['켈리 비율'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(formatted_predictions, use_container_width=True)
                else:
                    st.info("모델 예측 데이터가 없습니다.")
        
        # 퍼센트 계산기
        st.subheader("퍼센트 계산기")
        calc_col1, calc_col2, calc_col3 = st.columns(3)
        
        with calc_col1:
            total_amount = st.number_input('총 금액', min_value=0, value=int(current_balance), step=10000)
        with calc_col2:
            percentage = st.number_input('퍼센트 (%)', min_value=0.0, max_value=100.0, value=10.0, step=0.1)
        with calc_col3:
            kelly_option = st.selectbox('켈리 기준', ['풀켈리', '하프켈리'])
        
        kelly_multiplier = 0.5 if kelly_option == '하프켈리' else 1.0
        calculated_amount = round(total_amount * (percentage/100) * kelly_multiplier)
        
        st.info(f"""
        💰 계산 결과
        - 입력 금액: {total_amount:,}원
        - 적용 비율: {percentage:.1f}% ({kelly_option})
        - 베팅 금액: {calculated_amount:,}원
        """)

if __name__ == '__main__':
    main()
