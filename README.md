# NBA 베팅 예측 시스템 🏀

XGBoost와 Neural Network를 활용하여 NBA 경기의 승패와 언더/오버를 예측하는 머신러닝 시스템입니다. 2007-08 시즌부터 현재까지의 팀 데이터와 배당률을 학습하여 오늘 경기의 베팅을 추천합니다.

## 주요 기능

- 머니라인 예측 정확도: ~69%
- 언더/오버 예측 정확도: ~55%
- 켈리 기준을 통한 최적 베팅 금액 계산
- 실시간 배당률 데이터 자동 수집 (FanDuel 등)
- 대시보드를 통한 수익률 트래킹
- 사용자별(재훈/경남) 베팅 기록 및 수익 관리

## 설치 방법

Python 3.9가 필요합니다.

```bash
# 가상환경 생성 및 활성화
$ python3 -m venv nba_env
$ source nba_env/bin/activate  # Linux/Mac
$ .\nba_env\Scripts\activate   # Windows

# 저장소 클론 및 패키지 설치
$ git clone https://github.com/jammytone/NBA-Machine-Learning-Sports-Betting.git
$ cd NBA-Machine-Learning-Sports-Betting
$ pip install -r requirements.txt
```

## 사용 방법

### 1. 예측 실행

```bash
$ python main.py -xgb -odds=fanduel -kc
```

옵션 설명:
- `-xgb`: XGBoost 모델 사용
- `-odds`: 배당률 데이터 소스 선택 (fanduel, draftkings, betmgm, pointsbet, caesars, wynn, bet_rivers_ny)
- `-kc`: 켈리 기준 적용

### 2. 대시보드 실행

```bash
$ streamlit run dashboard.py
```

대시보드 기능:
- 오늘의 경기 예측 결과 확인
- 풀 켈리/하프 켈리 선택
- 사용자별 수익률 트래킹
- 베팅 기록 관리
- 통계 분석 (적중률, ROI 등)

## 데이터 업데이트 및 모델 재학습

```bash
# 2023-24 시즌 최신 데이터 수집
cd src/Process-Data
python -m Get_Data
python -m Get_Odds_Data
python -m Create_Games

# 모델 재학습
cd ../Train-Models
python -m XGBoost_Model_ML
python -m XGBoost_Model_UO
```

## 주의사항

- 하프 켈리 기준 사용을 권장합니다 (리스크 관리)
- 모든 베팅은 신중하게 결정하세요
- 과도한 베팅은 금물입니다

## 패키지 버전

주요 패키지 버전:
- Python 3.9
- streamlit==1.31.0
- pandas==1.5.3
- plotly==5.18.0
- numpy==1.24.3
- xgboost==2.0.3
- tensorflow==2.15.0

## 기여

모든 기여를 환영합니다. 이슈나 PR을 자유롭게 올려주세요.
