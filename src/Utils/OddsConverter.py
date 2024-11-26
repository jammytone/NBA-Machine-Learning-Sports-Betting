def american_to_decimal(american_odds):
    """아메리칸 배당률을 소수점 배당률로 변환"""
    if not american_odds:
        return None
    if american_odds > 0:
        return round(1 + (american_odds / 100), 2)
    else:
        return round(1 + (100 / abs(american_odds)), 2)