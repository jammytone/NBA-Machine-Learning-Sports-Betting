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
    
    # 기본 정보 표시
    st.subheader('현재 잔액')
    current_balance = df['잔액'].iloc[-1]
    initial_balance = 1000  # 초기 잔액
    profit_percentage = ((current_balance - initial_balance) / initial_balance) * 100
    
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 잔액", f"₩{current_balance:,.0f}")
    col2.metric("초기 잔액", f"₩{initial_balance:,.0f}")
    col3.metric("수익률", f"{profit_percentage:.1f}%")
    
    # 잔액 추이 그래프
    st.subheader('잔액 추이')
    fig = px.line(df, x='날짜', y='잔액', title='잔액 변화')
    fig.update_layout(
        xaxis_title="날짜",
        yaxis_title="잔액",
        width=1200,
        height=500
    )
    # x축 레이블 회전 각도 조정
    fig.update_xaxes(tickangle=0)
    st.plotly_chart(fig)
    
    # 승패 통계
    st.subheader('승패 통계')
    win_count = len(df[df['결과'] == '승'])
    lose_count = len(df[df['결과'] == '패'])
    total_games = win_count + lose_count
    if total_games > 0:
        win_rate = (win_count / total_games) * 100
        col1, col2, col3 = st.columns(3)
        col1.metric("승리", win_count)
        col2.metric("패배", lose_count)
        col3.metric("승률", f"{win_rate:.1f}%")
    
    # 데이터 테이블 표시
    st.subheader('상세 데이터')
    
    # 숫자 포맷팅
    formatted_df = df.copy()
    formatted_df['확률'] = formatted_df['확률'].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else '')
    formatted_df['켈리 비율'] = formatted_df['켈리 비율'].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else '')
    formatted_df['진입'] = formatted_df['진입'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else '')
    formatted_df['자본금 변화'] = formatted_df['자본금 변화'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else '')
    formatted_df['잔액'] = formatted_df['잔액'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else '')
    
    # 전체 데이터 테이블을 더 넓게 표시
    st.dataframe(formatted_df, width=1200, height=400)
    
    # 날짜별 필터링
    st.sidebar.title('필터 옵션')
    dates = sorted(df['날짜'].unique(), reverse=True)  # 날짜를 역순으로 정렬
    selected_date = st.sidebar.selectbox('날짜 선택', dates, index=0)  # 가장 최근 날짜를 기본값으로
    
    if selected_date:
        filtered_df = df[df['날짜'] == selected_date]
        st.subheader(f'{selected_date} 경기 분석')
        
        # 두 개의 컬럼으로 나누어 표시
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("실제 베팅 데이터")
            # 데이터 포맷팅
            formatted_filtered_df = filtered_df.copy()
            formatted_filtered_df['확률'] = formatted_filtered_df['확률'].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else '')
            formatted_filtered_df['켈리 비율'] = formatted_filtered_df['켈리 비율'].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else '')
            formatted_filtered_df['진입'] = formatted_filtered_df['진입'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else '')
            formatted_filtered_df['자본금 변화'] = formatted_filtered_df['자본금 변화'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else '')
            formatted_filtered_df['잔액'] = formatted_filtered_df['잔액'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else '')
            
            st.dataframe(formatted_filtered_df, width=600)
        
        with col2:
            st.subheader("모델 출력")
            if not model_predictions.empty:
                # 데이터프레임 포맷팅
                formatted_df = model_predictions.copy()
                for col in formatted_df.columns:
                    if '기대값' in col:
                        formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.1f}")  # 소수점 한 자리로 변경
                formatted_df['켈리 비율'] = formatted_df['켈리 비율'].apply(lambda x: f"{x:.1f}%")  # 소수점 한 자리로 변경
                
                st.dataframe(formatted_df, width=600)
            else:
                st.write("모델 예측 데이터가 없습니다.")
        
        # 퍼센트 계산기 추가
        st.subheader("퍼센트 계산기")
        calc_col1, calc_col2, calc_col3 = st.columns(3)
        
        with calc_col1:
            total_amount = st.number_input('총 금액', min_value=0, value=100000, step=10000, key='calc_amount')
        with calc_col2:
            percentage = st.number_input('퍼센트 (%)', min_value=0.0, max_value=100.0, value=10.0, step=0.1, key='calc_percent')
        with calc_col3:
            kelly_option = st.selectbox('켈리 기준', ['풀켈리', '하프켈리'], key='calc_kelly')
        
        # 계산 결과
        kelly_multiplier = 0.5 if kelly_option == '하프켈리' else 1.0
        calculated_amount = round(total_amount * (percentage/100) * kelly_multiplier)
        
        st.markdown(f"""
        ### 계산 결과
        - **입력 금액**: {total_amount:,}
        - **적용 비율**: {percentage:.1f}% ({kelly_option})
        - **계산 금액**: {calculated_amount:,}
        """)

if __name__ == '__main__':
    main()
