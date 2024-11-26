from sbrscrape import Scoreboard
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class SbrOddsProvider:
    """ 팀 위치에 대한 약어 사전입니다. 때때로 전체 이름 대신 약어로 저장됩니다.
    머니라인 옵션 이름은 항상 전체 이름이 필요합니다.
    Returns:
        string: 전체 위치 이름
    """

    def __init__(self, sportsbook="fanduel", target_date=None):
        if target_date:
            # 전달받은 날짜 사용
            date_str = target_date.strftime('%Y-%m-%d')
        else:
            # 현재 ET 시간 기준으로 경기 날짜 결정
            current_time_et = datetime.now(ZoneInfo("America/New_York"))
            date_str = current_time_et.strftime('%Y-%m-%d')
                
        print(f"검색하는 날짜: {date_str}")
        sb = Scoreboard(sport="NBA", date=date_str)
        self.games = sb.games if hasattr(sb, 'games') else []
        if not self.games:
            print(f"{date_str}에 예정된 NBA 경기가 없습니다.")
        self.sportsbook = sportsbook

    def get_odds(self):
        """Sbr 서버의 json 컨텐츠에서 배당률을 반환하는 함수

        Returns:
            dictionary: [홈팀이름 + ':' + 원정팀이름: { 홈팀: 머니라인배당, 원정팀: 머니라인배당 }, 언더오버배당: 값]
        """
        dict_res = {}
        
        # 배당률 출력 헤더
        print(f"------------------{self.sportsbook} odds data------------------")
        
        for game in self.games:
            home_team_name = game['home_team'].replace("Los Angeles Clippers", "LA Clippers")
            away_team_name = game['away_team'].replace("Los Angeles Clippers", "LA Clippers")
            
            money_line_home_value = money_line_away_value = totals_value = None
            
            if self.sportsbook in game['home_ml']:
                money_line_home_value = game['home_ml'][self.sportsbook]
            if self.sportsbook in game['away_ml']:
                money_line_away_value = game['away_ml'][self.sportsbook]
            if self.sportsbook in game['total']:
                totals_value = game['total'][self.sportsbook]
                
            # 배당률 출력
            print(f"{away_team_name} ({money_line_away_value}) @ {home_team_name} ({money_line_home_value})")
            
            dict_res[home_team_name + ':' + away_team_name] = {
                'under_over_odds': totals_value,
                home_team_name: {'money_line_odds': money_line_home_value},
                away_team_name: {'money_line_odds': money_line_away_value}
            }
        
        return dict_res
