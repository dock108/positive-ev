from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ParlayResult:
    decimal_odds: float
    american_odds: float
    implied_prob_from_odds: float
    true_win_prob: float
    ev: float
    kelly_fraction: float
    total_edge: float
    correlated_warning: bool = False

class ParlayUtils:
    @staticmethod
    def american_to_decimal(american_odds: float) -> float:
        """Convert American odds to decimal odds."""
        if american_odds > 0:
            return (american_odds / 100.0) + 1
        else:
            return (100.0 / abs(american_odds)) + 1

    @staticmethod
    def decimal_to_american(decimal_odds: float) -> int:
        """Convert decimal odds to American odds."""
        if decimal_odds >= 2:
            return int(round((decimal_odds - 1) * 100))
        else:
            return int(round(-100 / (decimal_odds - 1)))

    @staticmethod
    def kelly_fraction(decimal_odds: float, win_prob: float) -> float:
        """Calculate Kelly criterion fraction for a bet."""
        if win_prob <= 0 or win_prob >= 1:
            return 0.0
        b = decimal_odds - 1  # Decimal odds minus 1 gives us the b in Kelly formula
        q = 1 - win_prob  # Probability of losing
        return max(0, (b * win_prob - q) / b)

    @staticmethod
    def check_correlation(bets: List[Dict]) -> bool:
        """
        Check if bets might be correlated (same game/player).
        Returns True if potential correlation detected.
        """
        games = set()
        players = set()
        
        for bet in bets:
            if 'event_id' in bet:
                games.add(bet['event_id'])
            if 'player_name' in bet and bet['player_name']:
                players.add(bet['player_name'])
        
        # If we have multiple bets from same game or player, they might be correlated
        return len(games) < len(bets) or len(players) < len(bets)

    @staticmethod
    def compute_parlay_odds(bets: List[Dict]) -> ParlayResult:
        """
        Compute parlay odds and related metrics for a list of bets.
        Each bet dict should have: odds (American), win_probability, ev_percent
        """
        market_decimal_product = 1.0  # For market implied odds
        true_prob_product = 1.0
        
        # Calculate the weighted average EV instead of summing
        total_weighted_ev = 0.0
        total_weight = 0.0
        
        for bet in bets:
            # Calculate market decimal odds
            market_dec_odds = ParlayUtils.american_to_decimal(float(bet['odds']))
            market_decimal_product *= market_dec_odds
            
            # Use true win probability from our calculations
            win_prob = float(bet['win_probability']) / 100 if 'win_probability' in bet else 0.5
            true_prob_product *= win_prob
            
            # Weight each bet's EV by its probability
            ev = float(bet.get('ev_percent', 0))
            total_weighted_ev += ev * win_prob
            total_weight += win_prob
        
        # Calculate average EV weighted by probabilities
        avg_ev = total_weighted_ev / total_weight if total_weight > 0 else 0
        
        # Scale down EV based on number of legs
        scaled_ev = avg_ev * (0.8 ** (len(bets) - 1))  # Each additional leg reduces EV by 20%
        
        # Calculate true decimal odds from true probability
        true_decimal_odds = 1.0 / true_prob_product if true_prob_product > 0 else float('inf')
        
        # Convert true decimal odds to American
        true_american_odds = ParlayUtils.decimal_to_american(true_decimal_odds)
        
        # Calculate market implied probability
        market_implied_prob = 1.0 / market_decimal_product
        
        # Calculate edge as difference between true probability and market probability
        edge = true_prob_product - market_implied_prob
        
        # Kelly calculation for parlay using true probability and true decimal odds
        kelly = ParlayUtils.kelly_fraction(true_decimal_odds, true_prob_product)
        
        # Check for correlation
        correlated = ParlayUtils.check_correlation(bets)
        
        return ParlayResult(
            decimal_odds=true_decimal_odds,
            american_odds=true_american_odds,
            implied_prob_from_odds=market_implied_prob,
            true_win_prob=true_prob_product,
            ev=scaled_ev,  # Use the scaled average EV
            kelly_fraction=kelly,
            total_edge=edge * 100,  # Convert edge to percentage
            correlated_warning=correlated
        ) 