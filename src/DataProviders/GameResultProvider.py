from datetime import datetime, timedelta
from sbrscrape import Scoreboard
from zoneinfo import ZoneInfo

class GameResultProvider:
    """NBA 경기 결과를 가져오는 클래스"""
    
    def __init__(self, target_date=None):
        if target_date:
            self.date = target_date
        else:
            # 현재 ET 시간 기준
            current_time_et = datetime.now(ZoneInfo("America/New_York"))
            self.date = current_time_et.date()
            
    def get_results(self):
        """특정 날짜의 NBA 경기 결과를 가져오는 함수
        
        Returns:
            dictionary: {홈팀이름 + ':' + 원정팀이름: 홈팀점수-원정팀점수}
        """
        date_str = self.date.strftime('%Y-%m-%d')
        sb = Scoreboard(sport="NBA", date=date_str)
        
        results = {}
        if hasattr(sb, 'games'):
            for game in sb.games:
                if 'home_score' in game and 'away_score' in game:
                    home_team = game['home_team'].replace("Los Angeles Clippers", "LA Clippers")
                    away_team = game['away_team'].replace("Los Angeles Clippers", "LA Clippers")
                    score = f"{game['home_score']}-{game['away_score']}"
                    results[f"{home_team}:{away_team}"] = score
                    
        return results