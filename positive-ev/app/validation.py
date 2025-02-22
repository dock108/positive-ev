from datetime import datetime
from decimal import Decimal, InvalidOperation
from app.exceptions import ValidationError
from app.logger import setup_logger

logger = setup_logger('validation')

def validate_bet_data(bet_data):
    """
    Validate betting data before saving to database.
    
    Args:
        bet_data (dict): Dictionary containing bet data
        
    Returns:
        dict: Validated and cleaned bet data
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Required fields
        required_fields = [
            'bet_id', 'timestamp', 'ev_percent', 'event_time',
            'event_teams', 'sport_league', 'bet_type', 'description',
            'odds', 'sportsbook'
        ]
        
        for field in required_fields:
            if field not in bet_data or bet_data[field] is None:
                raise ValidationError(f"Missing required field: {field}")
        
        # Clean and validate fields
        cleaned_data = {}
        
        # Validate bet_id
        cleaned_data['bet_id'] = str(bet_data['bet_id']).strip()
        if not cleaned_data['bet_id']:
            raise ValidationError("Invalid bet_id")
        
        # Validate timestamp
        try:
            if isinstance(bet_data['timestamp'], str):
                cleaned_data['timestamp'] = datetime.strptime(
                    bet_data['timestamp'], '%Y-%m-%d %H:%M:%S'
                )
            else:
                cleaned_data['timestamp'] = bet_data['timestamp']
        except ValueError as e:
            raise ValidationError(f"Invalid timestamp format: {e}")
        
        # Validate EV percent
        try:
            ev_str = str(bet_data['ev_percent']).replace('%', '').strip()
            cleaned_data['ev_percent'] = float(ev_str)
            if not (0 <= cleaned_data['ev_percent'] <= 100):
                raise ValidationError("EV percent must be between 0 and 100")
        except ValueError as e:
            raise ValidationError(f"Invalid EV percent: {e}")
        
        # Validate event time
        try:
            if isinstance(bet_data['event_time'], str):
                cleaned_data['event_time'] = datetime.strptime(
                    bet_data['event_time'], '%Y-%m-%d %H:%M'
                )
            else:
                cleaned_data['event_time'] = bet_data['event_time']
        except ValueError as e:
            raise ValidationError(f"Invalid event time format: {e}")
        
        # Validate teams
        cleaned_data['event_teams'] = str(bet_data['event_teams']).strip()
        if not cleaned_data['event_teams'] or 'vs' not in cleaned_data['event_teams'].lower():
            raise ValidationError("Invalid event teams format")
        
        # Validate sport/league
        cleaned_data['sport_league'] = str(bet_data['sport_league']).strip()
        if not cleaned_data['sport_league'] or '|' not in cleaned_data['sport_league']:
            raise ValidationError("Invalid sport/league format")
        
        # Validate bet type
        cleaned_data['bet_type'] = str(bet_data['bet_type']).strip()
        if not cleaned_data['bet_type']:
            raise ValidationError("Invalid bet type")
        
        # Validate description
        cleaned_data['description'] = str(bet_data['description']).strip()
        if not cleaned_data['description']:
            raise ValidationError("Invalid description")
        
        # Validate odds
        try:
            odds_str = str(bet_data['odds']).strip()
            if odds_str.startswith('+'):
                cleaned_data['odds'] = int(odds_str)
            elif odds_str.startswith('-'):
                cleaned_data['odds'] = int(odds_str)
            else:
                cleaned_data['odds'] = int(f"+{odds_str}")
        except ValueError as e:
            raise ValidationError(f"Invalid odds format: {e}")
        
        # Validate sportsbook
        cleaned_data['sportsbook'] = str(bet_data['sportsbook']).strip()
        if not cleaned_data['sportsbook']:
            raise ValidationError("Invalid sportsbook")
        
        # Optional fields
        if 'bet_size' in bet_data and bet_data['bet_size']:
            try:
                bet_size_str = str(bet_data['bet_size']).replace('$', '').strip()
                cleaned_data['bet_size'] = Decimal(bet_size_str)
            except (ValueError, InvalidOperation) as e:
                raise ValidationError(f"Invalid bet size: {e}")
        
        if 'win_probability' in bet_data and bet_data['win_probability']:
            try:
                prob_str = str(bet_data['win_probability']).replace('%', '').strip()
                cleaned_data['win_probability'] = float(prob_str)
                if not (0 <= cleaned_data['win_probability'] <= 100):
                    raise ValidationError("Win probability must be between 0 and 100")
            except ValueError as e:
                raise ValidationError(f"Invalid win probability: {e}")
        
        if 'result' in bet_data:
            result = str(bet_data['result']).strip().upper()
            if result and result not in ['WIN', 'LOSS', 'TIE', 'UNCERTAIN']:
                raise ValidationError("Invalid result value")
            cleaned_data['result'] = result
        
        logger.debug(f"Validated bet data: {cleaned_data}")
        return cleaned_data
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise ValidationError(f"Validation failed: {str(e)}")

def validate_player_stats(stats_data):
    """
    Validate player statistics data.
    
    Args:
        stats_data (dict): Dictionary containing player stats
        
    Returns:
        dict: Validated and cleaned stats data
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Required fields
        required_fields = [
            'player_name', 'game_id', 'points', 'rebounds',
            'assists', 'steals', 'blocks', 'turnovers'
        ]
        
        for field in required_fields:
            if field not in stats_data or stats_data[field] is None:
                raise ValidationError(f"Missing required field: {field}")
        
        # Clean and validate fields
        cleaned_data = {}
        
        # Validate player name
        cleaned_data['player_name'] = str(stats_data['player_name']).strip()
        if not cleaned_data['player_name']:
            raise ValidationError("Invalid player name")
        
        # Validate game ID
        cleaned_data['game_id'] = str(stats_data['game_id']).strip()
        if not cleaned_data['game_id']:
            raise ValidationError("Invalid game ID")
        
        # Validate numeric stats
        numeric_fields = [
            'points', 'rebounds', 'assists', 'steals',
            'blocks', 'turnovers', 'made_threes'
        ]
        
        for field in numeric_fields:
            if field in stats_data:
                try:
                    value = int(stats_data[field])
                    if value < 0:
                        raise ValidationError(f"{field} cannot be negative")
                    cleaned_data[field] = value
                except ValueError as e:
                    raise ValidationError(f"Invalid {field} value: {e}")
        
        logger.debug(f"Validated player stats: {cleaned_data}")
        return cleaned_data
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise ValidationError(f"Validation failed: {str(e)}")

def validate_model_input(input_data):
    """
    Validate model input data.
    
    Args:
        input_data (dict): Dictionary containing model input features
        
    Returns:
        dict: Validated and cleaned input data
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Required fields will depend on your model
        required_fields = [
            'ev_percent', 'odds', 'win_probability',
            'time_to_event', 'bet_time_category'
        ]
        
        for field in required_fields:
            if field not in input_data or input_data[field] is None:
                raise ValidationError(f"Missing required field: {field}")
        
        # Clean and validate fields
        cleaned_data = {}
        
        # Validate numeric fields
        numeric_fields = {
            'ev_percent': (0, 100),
            'win_probability': (0, 100),
            'time_to_event': (0, float('inf'))
        }
        
        for field, (min_val, max_val) in numeric_fields.items():
            try:
                value = float(input_data[field])
                if not (min_val <= value <= max_val):
                    raise ValidationError(
                        f"{field} must be between {min_val} and {max_val}"
                    )
                cleaned_data[field] = value
            except ValueError as e:
                raise ValidationError(f"Invalid {field} value: {e}")
        
        # Validate odds
        try:
            odds_str = str(input_data['odds']).strip()
            if odds_str.startswith('+'):
                cleaned_data['odds'] = int(odds_str)
            elif odds_str.startswith('-'):
                cleaned_data['odds'] = int(odds_str)
            else:
                cleaned_data['odds'] = int(f"+{odds_str}")
        except ValueError as e:
            raise ValidationError(f"Invalid odds format: {e}")
        
        # Validate categorical fields
        cleaned_data['bet_time_category'] = str(input_data['bet_time_category']).strip()
        if cleaned_data['bet_time_category'] not in ['Early', 'Mid', 'Late']:
            raise ValidationError("Invalid bet time category")
        
        # Add any additional player stats if present
        player_stats = [
            col for col in input_data.keys()
            if any(x in col for x in ['_avg', '_std', '_trend', '_consistency'])
        ]
        
        for stat in player_stats:
            try:
                cleaned_data[stat] = float(input_data[stat])
            except ValueError as e:
                raise ValidationError(f"Invalid {stat} value: {e}")
        
        logger.debug(f"Validated model input: {cleaned_data}")
        return cleaned_data
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise ValidationError(f"Validation failed: {str(e)}") 