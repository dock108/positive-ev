from flask import Blueprint, jsonify, request
from app.routes.chat import token_required

parlay_bp = Blueprint('parlay', __name__, url_prefix='/api/parlay')

@parlay_bp.route('/calculate', methods=['POST'])
@token_required
def calculate_parlay(current_user):
    """
    Calculate parlay odds and potential payout.
    
    Expected JSON payload:
    {
        "odds": ["+120", "-110", "+150"]  # Array of American odds
    }
    """
    data = request.get_json()
    
    if not data or 'odds' not in data:
        return jsonify({"error": "Missing required odds data"}), 400
    
    odds_list = data.get('odds', [])
    
    if not odds_list or not isinstance(odds_list, list):
        return jsonify({"error": "Odds must be provided as a non-empty array"}), 400
    
    try:
        # Convert American odds to decimal
        decimal_odds = []
        for odd in odds_list:
            if isinstance(odd, str):
                if odd.startswith('+'):
                    # Positive odds (e.g., +150)
                    decimal = float(odd[1:]) / 100 + 1
                elif odd.startswith('-'):
                    # Negative odds (e.g., -110)
                    decimal = 100 / float(odd[1:]) + 1
                else:
                    # Try to parse as a number
                    value = float(odd)
                    if value >= 100:  # Assume positive American odds
                        decimal = value / 100 + 1
                    elif value <= -100:  # Assume negative American odds
                        decimal = 100 / abs(value) + 1
                    else:
                        # Assume it's already decimal odds
                        decimal = value
            else:
                # Assume it's already a number
                decimal = float(odd)
            
            decimal_odds.append(decimal)
        
        # Calculate combined decimal odds
        combined_decimal = 1
        for odd in decimal_odds:
            combined_decimal *= odd
        
        # Convert back to American odds
        if combined_decimal > 2:
            american_odds = f"+{int((combined_decimal - 1) * 100)}"
        else:
            american_odds = f"-{int(100 / (combined_decimal - 1))}"
        
        # Calculate implied probability
        implied_probability = (1 / combined_decimal) * 100
        
        # Calculate potential payout for a $100 bet
        potential_payout = 100 * combined_decimal
        
        return jsonify({
            "input_odds": odds_list,
            "decimal_odds": decimal_odds,
            "combined_decimal_odds": combined_decimal,
            "american_odds": american_odds,
            "implied_probability": f"{implied_probability:.2f}%",
            "potential_payout": f"${potential_payout:.2f}",
            "profit": f"${potential_payout - 100:.2f}"
        })
        
    except Exception as e:
        return jsonify({"error": f"Error calculating parlay: {str(e)}"}), 400
