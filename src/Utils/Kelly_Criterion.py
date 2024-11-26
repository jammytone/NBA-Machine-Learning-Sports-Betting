def american_to_decimal(american_odds):
    """
    Converts American odds to decimal odds (European odds).
    """
    if american_odds > 0:
        decimal_odds = (american_odds / 100) + 1
    else:
        decimal_odds = (100 / abs(american_odds)) + 1
    return round(decimal_odds, 2)

def calculate_kelly_criterion(american_odds, model_prob):
    """
    Calculates the fraction of the bankroll to be wagered on each bet
    """
    decimal_odds = american_to_decimal(american_odds)
    bankroll_fraction = ((decimal_odds * model_prob - 1) / (decimal_odds - 1)) * 100
    bankroll_fraction = round(bankroll_fraction, 2)
    return bankroll_fraction if bankroll_fraction > 0 else 0