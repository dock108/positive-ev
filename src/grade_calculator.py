"""
Grade Calculator Module
=====================

This module calculates grades for betting opportunities based on multiple factors
including expected value, timing, and market edge.

Key Features:
    - Multi-factor grade calculation (EV, timing, edge)
    - Batch processing of bets
    - CSV export functionality
    - Supabase integration for data storage
    - Configurable date range processing

Grade Calculation Weights:
    - Expected Value (EV): 55%
    - Market Edge: 30%
    - Timing Score: 15%

Grade Scale:
    A: >= 90
    B: >= 80
    C: >= 70
    D: >= 65
    F: < 65

Dependencies:
    - pandas: For data manipulation and CSV export
    - supabase-py: For database operations
    - python-dotenv: For environment variables

Usage:
    # Process last 24 hours
    python src/grade_calculator.py

    # Process specific date range
    python src/grade_calculator.py --start-date 2024-03-01 --end-date 2024-03-14

Author: highlyprofitable108
Created: March 2025
Updated: March 2025 - Removed Kelly criterion, adjusted weights, improved timing granularity
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta

# Add the project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Try relative imports first, fall back to absolute
try:
    from .config import (
        CALCULATOR_LOG_FILE,
        CSV_DIR,
        setup_logging
    )
    from .common_utils import safe_float
    from .supabase_client import (
        get_supabase_client,
        batch_upsert,
        get_most_recent_timestamp
    )
except ImportError:
    # When running as script
    from src.config import (
        CALCULATOR_LOG_FILE,
        CSV_DIR,
        setup_logging
    )
    from src.common_utils import safe_float
    from src.supabase_client import (
        get_supabase_client,
        batch_upsert,
        get_most_recent_timestamp
    )

# Initialize logger and supabase client
logger = setup_logging(CALCULATOR_LOG_FILE, "grade_calculator")
supabase = get_supabase_client()

def standardize_datetime(dt_value):
    """
    Standardize datetime objects to naive UTC for consistent comparison.
    
    Args:
        dt_value: A datetime object or string representation
        
    Returns:
        Naive datetime object (no timezone info)
    """
    if isinstance(dt_value, str):
        try:
            # If it's a string with timezone info, parse it and convert to UTC
            if dt_value.endswith('Z') or '+' in dt_value or '-' in dt_value:
                dt = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                return dt.replace(tzinfo=None)  # Convert to naive in UTC
            else:
                # If there's no timezone, assume it's in UTC
                return datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            # Fallback parsing
            try:
                return datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.error(f"Could not parse datetime: {dt_value}")
                return datetime.now()  # Default to current time if parsing fails
    elif isinstance(dt_value, datetime):
        # If it's already a datetime, standardize to naive UTC
        if dt_value.tzinfo is not None:
            return dt_value.replace(tzinfo=None)
        return dt_value
    else:
        logger.error(f"Unexpected datetime format: {type(dt_value)}")
        return datetime.now()

def calculate_ev_score(ev_percent):
    """Calculate score based on Expected Value, with max cap and decay for high values."""
    try:
        ev = safe_float(ev_percent)
        logger.debug(f"EV Score Calculation - Input EV: {ev}%")
        
        if ev is None:
            logger.debug("EV Score Calculation - Invalid EV value, returning 0")
            return 0
        
        # Cap EV at 15%
        if ev > 15:
            # Apply decay for values above 15%
            normalized_ev = 15 - (ev - 15) * 0.5  # Adjust decay factor as needed
            logger.debug(f"EV Score Calculation - EV exceeds 15% cap, applying decay: {ev}% → {normalized_ev}%")
        else:
            normalized_ev = ev
            logger.debug(f"EV Score Calculation - Using EV as is: {normalized_ev}%")
        
        # Normalize to a score between 0 and 100
        raw_score = (normalized_ev + 10) * 5
        final_score = max(0, min(100, raw_score))
        logger.debug(f"EV Score Calculation - Formula: (normalized_ev + 10) * 5 = ({normalized_ev} + 10) * 5 = {raw_score}")
        logger.debug(f"EV Score Calculation - Final score (capped 0-100): {final_score}")
        return final_score
    except Exception as e:
        logger.error(f"Error calculating EV score: {str(e)}")
        return 0

def calculate_timing_score(event_time, timestamp):
    """
    Calculate score based on time until event with more granular ranges.
    
    The closer to game time, the more valuable a bet with an edge becomes,
    as it's more likely to represent Closing Line Value (CLV).
    """
    try:
        logger.debug(f"Timing Score Calculation - Event time: {event_time}, Bet timestamp: {timestamp}")
        
        # Standardize timestamps using the shared function
        event_dt = standardize_datetime(event_time)
        bet_dt = standardize_datetime(timestamp)
        
        logger.debug(f"Timing Score Calculation - Standardized times - Event: {event_dt}, Bet: {bet_dt}")
        
        # Calculate time difference in hours
        time_diff = (event_dt - bet_dt).total_seconds() / 3600
        logger.debug(f"Timing Score Calculation - Time difference: {time_diff:.2f} hours")
        
        # More granular scoring system emphasizing CLV
        if time_diff <= 0:
            score = 0  # Event already started
            reason = "Event already started"
        elif time_diff <= 0.5:
            score = 100  # Less than 30 minutes
            reason = "Less than 30 minutes before event"
        elif time_diff <= 1:
            score = 95  # 30-60 minutes
            reason = "30-60 minutes before event"
        elif time_diff <= 2:
            score = 90  # 1-2 hours
            reason = "1-2 hours before event"
        elif time_diff <= 3:
            score = 85  # 2-3 hours
            reason = "2-3 hours before event"
        elif time_diff <= 4:
            score = 80  # 3-4 hours
            reason = "3-4 hours before event"
        elif time_diff <= 6:
            score = 75  # 4-6 hours
            reason = "4-6 hours before event"
        elif time_diff <= 8:
            score = 70  # 6-8 hours
            reason = "6-8 hours before event"
        elif time_diff <= 12:
            score = 65  # 8-12 hours
            reason = "8-12 hours before event"
        elif time_diff <= 18:
            score = 60  # 12-18 hours
            reason = "12-18 hours before event"
        elif time_diff <= 24:
            score = 55  # 18-24 hours
            reason = "18-24 hours before event"
        elif time_diff <= 36:
            score = 50  # 24-36 hours
            reason = "24-36 hours before event"
        elif time_diff <= 48:
            score = 45  # 36-48 hours
            reason = "36-48 hours before event"
        elif time_diff <= 72:
            score = 40  # 48-72 hours
            reason = "48-72 hours before event"
        else:
            score = 30  # More than 72 hours
            reason = "More than 72 hours before event"
        
        logger.debug(f"Timing Score Calculation - Assigned score: {score} ({reason})")
        return score
    except Exception as e:
        logger.error(f"Error calculating timing score: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def calculate_kelly_score(win_probability, odds):
    """Calculate score based on Kelly Criterion."""
    try:
        win_prob = safe_float(win_probability)
        if win_prob is None:
            return 0
        
        win_prob = win_prob / 100  # Convert to decimal
        
        odds = float(odds)
        decimal_odds = None
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        # Kelly formula: f* = (p * b - q) / b
        # where p = win probability, q = 1-p, b = decimal odds - 1
        b = decimal_odds - 1
        q = 1 - win_prob
        
        kelly = (win_prob * b - q) / b
        
        # Convert kelly to score (0-100)
        kelly_score = min(kelly * 500, 100)  # Cap at 100
        return max(0, kelly_score)  # Floor at 0
    except Exception as e:
        logger.error(f"Error calculating Kelly score: {str(e)}")
        return 0

def calculate_edge_score(win_probability, odds):
    """Calculate score based on edge over market implied probability."""
    try:
        win_prob = safe_float(win_probability)
        if win_prob is None:
            return 0
        
        odds = float(odds)
        market_implied_prob = None
        if odds > 0:
            market_implied_prob = 100 / (odds + 100) * 100
        else:
            market_implied_prob = abs(odds) / (abs(odds) + 100) * 100
        
        edge = win_prob - market_implied_prob
        normalized_edge = (edge + 10) * 5
        
        # Implement a threshold for minimum edge score
        if normalized_edge < 49:
            return 0  # Discard low edge scores
        
        return max(0, min(100, normalized_edge))
    except Exception as e:
        logger.error(f"Error calculating edge score: {str(e)}")
        return 0

def calculate_ev_trend_score(current_ev, bet_id, timestamp):
    """
    Calculate EV trend score based on changes from initial EV to current EV.
    
    Args:
        current_ev: Current EV percentage
        bet_id: Unique bet identifier
        timestamp: Current timestamp of the bet
        
    Returns:
        EV trend score (0-100)
    """
    try:
        logger.debug(f"EV Trend Score Calculation - Bet ID: {bet_id}, Current EV: {current_ev}%")
        
        current_ev = safe_float(current_ev)
        if current_ev is None or not bet_id:
            logger.debug("EV Trend Score Calculation - Invalid inputs, returning 0")
            return 50  # Neutral score when no trend data available
            
        # Get initial EV from initial_bet_details
        response = supabase.table("initial_bet_details").select("initial_ev, first_seen").eq("bet_id", bet_id).execute()
        
        if not response.data:
            logger.debug(f"EV Trend Score Calculation - No initial details found for bet_id: {bet_id}")
            return 50  # Neutral score when no trend data available
            
        initial_data = response.data[0]
        initial_ev = safe_float(initial_data.get('initial_ev'))
        first_seen = initial_data.get('first_seen')
        
        logger.debug(f"EV Trend Score Calculation - Initial EV: {initial_ev}%, First seen: {first_seen}")
        
        if initial_ev is None or not first_seen:
            logger.debug("EV Trend Score Calculation - Missing initial EV or timestamp, using neutral score")
            return 50  # Neutral score when initial EV is missing
        
        # Calculate EV change
        ev_change = current_ev - initial_ev
        logger.debug(f"EV Trend Score Calculation - EV Change: {current_ev}% - {initial_ev}% = {ev_change}%")
        
        # Basic score starts at 50 (neutral)
        trend_score = 50
        logger.debug(f"EV Trend Score Calculation - Starting with neutral score: {trend_score}")
        
        # Adjust score based on EV change direction and magnitude
        if abs(ev_change) > 0:
            # Calculate percentage change relative to initial EV
            # Use max with small value to avoid division by zero
            pct_change = (ev_change / max(abs(initial_ev), 0.1)) * 100
            logger.debug(f"EV Trend Score Calculation - Percentage change: {pct_change:.2f}%")
            
            # Apply different scaling for positive vs negative changes
            if ev_change > 0:
                # Positive changes get a modest boost (0.5x factor)
                adjustment = min(pct_change * 0.5, 50)  # Cap at +50 points
                trend_score += adjustment
                logger.debug(f"EV Trend Score Calculation - Positive change adjustment: +{adjustment:.2f} points (0.5x factor)")
            else:
                # Negative changes get a larger penalty (1.0x factor)
                adjustment = min(abs(pct_change) * 1.0, 50)  # Cap at -50 points
                trend_score -= adjustment
                logger.debug(f"EV Trend Score Calculation - Negative change adjustment: -{adjustment:.2f} points (1.0x factor)")
        else:
            logger.debug("EV Trend Score Calculation - No EV change detected, keeping neutral score")
        
        # Ensure score is within 0-100 range
        final_score = max(0, min(100, trend_score))
        logger.debug(f"EV Trend Score Calculation - Final score: {final_score}")
        return final_score
    except Exception as e:
        logger.error(f"Error calculating EV trend score: {str(e)}")
        return 50  # Return neutral score on error

def calculate_bayesian_confidence(current_ev, bet_id, event_time, timestamp):
    """
    Calculate Bayesian confidence score using historical EV data and time-based factors.
    
    Args:
        current_ev: Current EV percentage
        bet_id: Unique bet identifier
        event_time: Time of the event/game
        timestamp: Current timestamp of the bet
        
    Returns:
        Bayesian confidence score (0-100)
    """
    try:
        logger.debug(f"Bayesian Confidence Calculation - Bet ID: {bet_id}, Current EV: {current_ev}%")
        
        current_ev = safe_float(current_ev)
        if current_ev is None or not bet_id:
            logger.debug("Bayesian Confidence Calculation - Invalid inputs, returning 0")
            return 0
            
        # Get initial EV from initial_bet_details
        response = supabase.table("initial_bet_details").select("*").eq("bet_id", bet_id).execute()
        
        if not response.data:
            logger.debug(f"Bayesian Confidence Calculation - No initial details found for bet_id: {bet_id}")
            return 50  # Neutral confidence when no historical data available
            
        initial_data = response.data[0]
        initial_ev = safe_float(initial_data.get('initial_ev'))
        first_seen = initial_data.get('first_seen')
        
        logger.debug(f"Bayesian Confidence Calculation - Initial EV: {initial_ev}%, First seen: {first_seen}")
        
        if initial_ev is None or not first_seen:
            logger.debug("Bayesian Confidence Calculation - Missing initial EV or timestamp, using neutral confidence")
            return 50  # Neutral confidence when initial EV is missing
        
        # Standardize all timestamps using the shared function
        first_dt = standardize_datetime(first_seen)
        current_dt = standardize_datetime(timestamp)
        event_dt = standardize_datetime(event_time)
        
        logger.debug(f"Bayesian Confidence Calculation - Standardized timestamps - First seen: {first_dt}, Current: {current_dt}, Event: {event_dt}")
        
        # Calculate time spans
        hours_since_first_seen = (current_dt - first_dt).total_seconds() / 3600
        hours_until_event = (event_dt - current_dt).total_seconds() / 3600
        
        logger.debug(f"Bayesian Confidence Calculation - Hours since first seen: {hours_since_first_seen:.2f}")
        logger.debug(f"Bayesian Confidence Calculation - Hours until event: {hours_until_event:.2f}")
        
        # Start with a base confidence of 50
        confidence = 50
        logger.debug(f"Bayesian Confidence Calculation - Starting with base confidence: {confidence}")
        
        # Calculate EV change
        ev_change = current_ev - initial_ev
        ev_change_pct = abs(ev_change) / max(abs(initial_ev), 0.1) * 100
        
        logger.debug(f"Bayesian Confidence Calculation - EV Change: {ev_change}% ({ev_change_pct:.2f}%)")
        
        # Apply EV change adjustments
        if ev_change > 0:
            # Positive changes get a modest boost (0.5x factor)
            adjustment = min(ev_change_pct * 0.5, 25)  # Cap at +25 points
            confidence += adjustment
            logger.debug(f"Bayesian Confidence Calculation - Positive EV change adjustment: +{adjustment:.2f} (0.5x factor)")
        else:
            # Negative changes get a larger penalty (1.0x factor)
            adjustment = min(ev_change_pct * 1.0, 30)  # Cap at -30 points
            confidence -= adjustment
            logger.debug(f"Bayesian Confidence Calculation - Negative EV change adjustment: -{adjustment:.2f} (1.0x factor)")
        
        # Apply time-based adjustments
        
        # Early improvement bonus (>20hrs before event)
        if hours_until_event > 20 and ev_change > 0:
            confidence += 5  # 5% boost for early positive changes
            logger.debug("Bayesian Confidence Calculation - Early improvement bonus: +5 points")
            
        # Late-stage changes (<3hrs before event)
        if hours_until_event < 3:
            if ev_change >= 0:
                # Positive or stable EV close to event time is valuable
                confidence += 10  # 10% boost for late positive/stable movement
                logger.debug("Bayesian Confidence Calculation - Late positive/stable movement bonus: +10 points")
            else:
                # Late negative changes are concerning
                penalty = min(abs(ev_change_pct) * 0.5, 25)  # Up to 25% penalty
                confidence -= penalty
                logger.debug(f"Bayesian Confidence Calculation - Late negative movement penalty: -{penalty:.2f} points")
        
        # Long-term stability bonus
        if hours_since_first_seen >= 12 and abs(ev_change_pct) < 10:
            confidence += 5  # 5% boost for bets stable over 12+ hours with minimal movement
            logger.debug("Bayesian Confidence Calculation - Long-term stability bonus: +5 points")
        
        # Ensure confidence is within 0-100 range
        final_confidence = max(0, min(100, confidence))
        logger.debug(f"Bayesian Confidence Calculation - Final confidence score: {final_confidence}")
        return final_confidence
    except Exception as e:
        logger.error(f"Error calculating Bayesian confidence: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 50  # Return neutral confidence on error

def calculate_true_bayesian_confidence(current_ev, bet_id, event_time, timestamp, debug=True):
    """
    Calculate true Bayesian probability of beating closing line value given observed signals.
    
    P(Beat CLV|Signals) = P(Signals|Beat CLV) * P(Beat CLV) / P(Signals)
    """
    try:
        debug_info = {
            "bet_id": bet_id,
            "current_ev": current_ev,
            "event_time": event_time,
            "timestamp": timestamp,
            "signals": {},
            "probabilities": {}
        }
        
        # Get initial EV and timing data
        response = supabase.table("initial_bet_details").select("*").eq("bet_id", bet_id).execute()
        if not response.data:
            return 50, {"error": "No initial details found"}
            
        initial_data = response.data[0]
        initial_ev = safe_float(initial_data.get('initial_ev'))
        first_seen = initial_data.get('first_seen')
        
        if initial_ev is None or not first_seen:
            return 50, {"error": "Missing initial EV or timestamp"}
            
        debug_info["initial_ev"] = initial_ev
        debug_info["first_seen"] = first_seen
        
        # 1. Calculate Prior P(Beat CLV)
        prior_beat_clv = 0.52  # Base rate, to be refined with historical data
        debug_info["probabilities"]["prior"] = prior_beat_clv
        
        # 2. Calculate Likelihoods P(Signal|Beat CLV) for each signal
        
        # 2a. EV Change Signal
        ev_change = current_ev - initial_ev
        # Use ev_change_pct for more granular probability adjustments
        ev_change_magnitude = abs(ev_change) / max(abs(initial_ev), 0.1)
        
        debug_info["signals"]["ev_change"] = {
            "raw_change": ev_change,
            "magnitude": ev_change_magnitude
        }
        
        # Scale probability based on magnitude of change
        if ev_change > 0:
            p_ev_signal_given_beat = min(0.7 + (ev_change_magnitude * 0.1), 0.9)
        else:
            p_ev_signal_given_beat = max(0.3 - (ev_change_magnitude * 0.1), 0.1)
            
        debug_info["probabilities"]["ev_signal"] = p_ev_signal_given_beat
        
        # 2b. Timing Signal
        current_dt = standardize_datetime(timestamp)
        event_dt = standardize_datetime(event_time)
        
        hours_until_event = (event_dt - current_dt).total_seconds() / 3600
        debug_info["signals"]["hours_until_event"] = hours_until_event
        
        # More granular timing probabilities
        if hours_until_event < 1:
            p_timing_signal_given_beat = 0.9  # Very close to event
        elif hours_until_event < 3:
            p_timing_signal_given_beat = 0.8  # Close to event
        elif hours_until_event < 6:
            p_timing_signal_given_beat = 0.7  # Moderately close
        elif hours_until_event < 12:
            p_timing_signal_given_beat = 0.6  # Medium timeframe
        elif hours_until_event < 24:
            p_timing_signal_given_beat = 0.5  # Further out
        else:
            p_timing_signal_given_beat = 0.4  # Far from event
            
        debug_info["probabilities"]["timing_signal"] = p_timing_signal_given_beat
        
        # 3. Calculate P(Signals) using law of total probability
        p_signals = (p_ev_signal_given_beat * prior_beat_clv + 
                   (1 - p_ev_signal_given_beat) * (1 - prior_beat_clv))
        debug_info["probabilities"]["signals"] = p_signals
        
        # 4. Apply Bayes Theorem
        posterior = (p_ev_signal_given_beat * p_timing_signal_given_beat * prior_beat_clv) / p_signals
        debug_info["probabilities"]["posterior"] = posterior
        
        # Convert to 0-100 scale
        bayesian_score = posterior * 100
        debug_info["final_score"] = bayesian_score
        
        if debug:
            logger.debug("\n=== True Bayesian Calculation Debug ===")
            logger.debug(f"Bet ID: {bet_id}")
            logger.debug(f"EV Change: {ev_change:.2f}% (Magnitude: {ev_change_magnitude:.2f})")
            logger.debug(f"Hours until event: {hours_until_event:.1f}")
            logger.debug("\nProbabilities:")
            logger.debug(f"- Prior P(Beat CLV): {prior_beat_clv:.3f}")
            logger.debug(f"- P(EV Signal|Beat CLV): {p_ev_signal_given_beat:.3f}")
            logger.debug(f"- P(Timing Signal|Beat CLV): {p_timing_signal_given_beat:.3f}")
            logger.debug(f"- P(Signals): {p_signals:.3f}")
            logger.debug(f"- Posterior P(Beat CLV|Signals): {posterior:.3f}")
            logger.debug(f"\nFinal Score (0-100): {bayesian_score:.2f}")
            logger.debug("=====================================\n")
        
        return bayesian_score, debug_info
        
    except Exception as e:
        logger.error(f"Error calculating true Bayesian confidence: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 50, {"error": str(e)}

def assign_grade(composite_score):
    """Assign letter grade based on absolute composite score."""
    if composite_score >= 90:
        logger.debug(f"Grade Assignment - A (score {composite_score:.2f} >= 90)")
        return 'A'
    elif composite_score >= 80:
        logger.debug(f"Grade Assignment - B (80 <= score {composite_score:.2f} < 90)")
        return 'B'
    elif composite_score >= 70:
        logger.debug(f"Grade Assignment - C (70 <= score {composite_score:.2f} < 80)")
        return 'C'
    elif composite_score >= 65:
        logger.debug(f"Grade Assignment - D (65 <= score {composite_score:.2f} < 70)")
        return 'D'
    else:
        logger.debug(f"Grade Assignment - F (score {composite_score:.2f} < 65)")
        return 'F'

def clean_numeric(value):
    """Clean numeric values by removing percentage signs and other non-numeric characters.
    
    Args:
        value: The value to clean
        
    Returns:
        Cleaned numeric value as float or None if conversion fails
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        # Remove percentage signs and other non-numeric characters
        # except for decimal points and minus signs
        clean_value = value.replace('%', '')
        try:
            return float(clean_value)
        except ValueError:
            logger.warning(f"Could not convert value '{value}' to numeric, defaulting to None")
            return None
    return None

def check_and_store_initial_details(bet):
    """Check if bet_id exists in initial_bet_details and store if not."""
    try:
        bet_id = bet.get('bet_id')
        if not bet_id:
            return
            
        # Check if bet_id exists in initial_bet_details
        response = supabase.table("initial_bet_details").select("bet_id").eq("bet_id", bet_id).execute()
        
        if not response.data:
            # Store initial details if bet_id not found
            initial_details = {
                "bet_id": bet_id,
                "initial_ev": clean_numeric(bet.get('ev_percent')),
                "initial_odds": clean_numeric(bet.get('odds')),  # Ensure odds are cleaned and assigned
                "initial_line": bet.get('bet_line'),
                "first_seen": bet.get('timestamp')  # Use bet's timestamp instead of current time
            }
            
            # Log the data being inserted for debugging
            logger.info(f"Adding new initial details for bet_id: {bet_id}, EV: {initial_details['initial_ev']}, "
                        f"Odds: {initial_details['initial_odds']}, Line: {initial_details['initial_line']}, First seen: {bet.get('timestamp')}")
            
            # Insert the record
            supabase.table("initial_bet_details").insert(initial_details).execute()
            logger.info(f"Successfully stored initial details for bet_id: {bet_id}")
    except Exception as e:
        logger.error(f"Error storing initial bet details for {bet_id}: {str(e)}")
        logger.error(f"Bet data: {bet}")

def calculate_bet_grade(bet, use_new_bayesian=False):
    """Calculate grade for a single bet."""
    try:
        # Extract required fields
        bet_id = bet.get('bet_id')
        ev_percent = bet.get('ev_percent')
        event_time = bet.get('event_time')
        odds = bet.get('odds')
        win_probability = bet.get('win_probability')
        timestamp = bet.get('timestamp')
        
        logger.debug(f"===== GRADE CALCULATION START: Bet ID {bet_id} =====")
        logger.debug(f"Input data - EV: {ev_percent}%, Odds: {odds}, Win Prob: {win_probability}%, Event Time: {event_time}, Timestamp: {timestamp}")
        
        # Skip bets with missing critical data
        if not all([bet_id, ev_percent, odds, win_probability, event_time, timestamp]):
            missing = []
            if not bet_id:
                missing.append("bet_id")
            if not ev_percent:
                missing.append("ev_percent")
            if not odds:
                missing.append("odds")
            if not win_probability:
                missing.append("win_probability")
            if not event_time:
                missing.append("event_time")
            if not timestamp:
                missing.append("timestamp")
            logger.debug(f"SKIPPED: Bet {bet_id} - Missing required data: {', '.join(missing)}")
            return None
        
        # Check and store initial bet details
        logger.debug(f"Checking/storing initial details for bet {bet_id}")
        check_and_store_initial_details(bet)
        
        # Calculate individual scores
        logger.debug(f"Calculating component scores for bet {bet_id}")
        
        ev_score = calculate_ev_score(ev_percent)
        logger.debug(f"Component Score - EV Score: {ev_score:.2f}")
        
        timing_score = calculate_timing_score(event_time, timestamp)
        logger.debug(f"Component Score - Timing Score: {timing_score:.2f}")
        
        ev_trend_score = calculate_ev_trend_score(ev_percent, bet_id, timestamp)
        logger.debug(f"Component Score - EV Trend Score: {ev_trend_score:.2f}")
        
        # Calculate both Bayesian scores
        old_bayesian_score = calculate_bayesian_confidence(ev_percent, bet_id, event_time, timestamp)
        new_bayesian_score, debug_info = calculate_true_bayesian_confidence(ev_percent, bet_id, event_time, timestamp)
        
        # Choose which Bayesian score to use
        bayesian_score = new_bayesian_score if use_new_bayesian else old_bayesian_score
        
        logger.debug(f"Component Score - Original Bayesian Score: {old_bayesian_score:.2f}")
        logger.debug(f"Component Score - True Bayesian Score: {new_bayesian_score:.2f}")
        logger.debug(f"Using {'new' if use_new_bayesian else 'original'} Bayesian score")
        if use_new_bayesian:
            logger.debug("True Bayesian Debug Info:")
            for key, value in debug_info.items():
                if isinstance(value, dict):
                    logger.debug(f"{key}:")
                    for subkey, subvalue in value.items():
                        logger.debug(f"  {subkey}: {subvalue}")
                else:
                    logger.debug(f"{key}: {value}")
        
        # Calculate composite score with updated weights
        logger.debug("Calculating composite score with weights: EV=55%, Timing=15%, EV Trend=15%, Bayesian=15%")
        
        ev_component = 0.55 * ev_score
        timing_component = 0.15 * timing_score
        trend_component = 0.15 * ev_trend_score
        bayesian_component = 0.15 * bayesian_score
        
        logger.debug("Weighted components:")
        logger.debug(f"  EV Score: {ev_score:.2f} × 0.55 = {ev_component:.2f}")
        logger.debug(f"  Timing Score: {timing_score:.2f} × 0.15 = {timing_component:.2f}")
        logger.debug(f"  EV Trend Score: {ev_trend_score:.2f} × 0.15 = {trend_component:.2f}")
        logger.debug(f"  Bayesian Score: {bayesian_score:.2f} × 0.15 = {bayesian_component:.2f}")
        
        composite_score = (
            ev_component +
            timing_component +
            trend_component +
            bayesian_component
        )
        
        logger.debug(f"Raw Composite Score: {ev_component:.2f} + {timing_component:.2f} + {trend_component:.2f} + {bayesian_component:.2f} = {composite_score:.2f}")

        # Log individual scores and composite score
        logger.info(
            f"Bet ID: {bet_id}, EV Score: {ev_score:.2f}, Timing Score: {timing_score:.2f}, "
            f"EV Trend Score: {ev_trend_score:.2f}, Bayesian Score: {bayesian_score:.2f}, "
            f"Composite Score: {composite_score:.2f}"
        )

        # Log the contributions to composite score
        logger.info(
            f"Composite Score Calculation: (0.55 * {ev_score:.2f}) + (0.15 * {timing_score:.2f}) + "
            f"(0.15 * {ev_trend_score:.2f}) + (0.15 * {bayesian_score:.2f}) = {composite_score:.2f}"
        )
        
        # Assign grade using absolute scale
        logger.debug("Assigning grade based on composite score")
        grade = assign_grade(composite_score)
        logger.debug(f"Grade assignment: {grade}")
        
        # Apply EV override rule - Cap at 'C' if EV is too good to be true (≥ 20%)
        current_ev = safe_float(ev_percent)
        if current_ev is not None and current_ev >= 20:
            # Override if current grade is better than C
            if grade in ['A', 'B']:
                logger.debug(f"Applying EV override rule - EV {current_ev}% >= 20%, capping grade at C")
                prev_grade = grade
                grade = 'C'
                logger.info(f"Applying EV override rule for bet {bet_id}: EV={current_ev}% capped at grade C (was {prev_grade})")
        
        # Log the assigned grade
        logger.info(f"Assigned Grade for Bet ID {bet_id}: {grade}")
        
        # Create grade record
        grade_record = {
            "bet_id": bet_id,
            "grade": grade,
            "calculated_at": datetime.now().isoformat(),
            "ev_score": round(ev_score, 2),
            "timing_score": round(timing_score, 2),
            "ev_trend_score": round(ev_trend_score, 2),
            "bayesian_confidence": round(bayesian_score, 2),
            "composite_score": round(composite_score, 2),
            "grading_method": "absolute"
        }
        
        logger.debug(f"===== GRADE CALCULATION COMPLETE: Bet ID {bet_id}, Grade: {grade} =====")
        return grade_record
    except Exception as e:
        logger.error(f"Error calculating grade for bet {bet.get('bet_id', 'unknown')}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_bets_last_24h():
    """Get bets added in the last 24 hours with only the most recent version of each bet_id."""
    supabase = get_supabase_client()
    
    # Calculate 24 hours ago
    cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
    
    try:
        # Get all unique bet_ids from the last 24 hours with pagination
        all_bet_ids = set()
        page_size = 1000
        offset = 0
        
        while True:
            query = (
                supabase.table("betting_data")
                .select("bet_id")
                .gte("timestamp", cutoff_time)
                .limit(page_size)
                .offset(offset)
            )
            
            response = query.execute()
            current_page = response.data
            
            if not current_page:
                break
                
            bet_ids = [record.get('bet_id') for record in current_page if record.get('bet_id')]
            all_bet_ids.update(bet_ids)
            logger.info(f"Retrieved {len(current_page)} bet IDs (offset {offset}), total unique IDs: {len(all_bet_ids)}")
            
            if len(current_page) < page_size:
                break
                
            offset += page_size
        
        logger.info(f"Found {len(all_bet_ids)} unique bet IDs from the last 24 hours")
        
        # Now get the most recent record for each bet_id
        unique_bets = []
        for bet_id in all_bet_ids:
            # Get the most recent record for this bet_id
            response = supabase.table("betting_data").select("*").eq("bet_id", bet_id).order("timestamp", desc=True).limit(1).execute()
            if response.data:
                unique_bets.append(response.data[0])
        
        logger.info(f"Retrieved {len(unique_bets)} unique bets from the last 24 hours")
        return unique_bets
    except Exception as e:
        logger.error(f"Error retrieving bets from last 24 hours: {e}")
        # Fall back to the pagination method if the approach fails
        logger.info("Falling back to pagination method")
        return get_bets_last_24h_paginated()

def get_bets_by_date_range(start_date, end_date):
    """Get bets within a specific date range with only the most recent version of each bet_id."""
    supabase = get_supabase_client()
    
    # Format end_date to include the entire day
    if end_date:
        end_date = f"{end_date}T23:59:59"
    
    try:
        # Get all unique bet_ids in the date range with pagination
        all_bet_ids = set()
        page_size = 1000
        offset = 0
        
        while True:
            query = (
                supabase.table("betting_data")
                .select("bet_id")
            )
            if start_date:
                query = query.gte("timestamp", start_date)
            if end_date:
                query = query.lte("timestamp", end_date)
            
            query = query.limit(page_size).offset(offset)
            
            response = query.execute()
            current_page = response.data
            
            if not current_page:
                break
                
            bet_ids = [record.get('bet_id') for record in current_page if record.get('bet_id')]
            all_bet_ids.update(bet_ids)
            logger.info(f"Retrieved {len(current_page)} bet IDs (offset {offset}), total unique IDs: {len(all_bet_ids)}")
            
            if len(current_page) < page_size:
                break
                
            offset += page_size
        
        logger.info(f"Found {len(all_bet_ids)} unique bet IDs in date range")
        
        # Now get the most recent record for each bet_id within the date range
        unique_bets = []
        total_processed = 0
        for bet_id in all_bet_ids:
            # Get the most recent record for this bet_id within the date range
            query = (
                supabase.table("betting_data")
                .select("*")
                .eq("bet_id", bet_id)
            )
            if start_date:
                query = query.gte("timestamp", start_date)
            if end_date:
                query = query.lte("timestamp", end_date)
            
            response = query.order("timestamp", desc=True).limit(1).execute()
            if response.data:
                unique_bets.append(response.data[0])
            
            total_processed += 1
            if total_processed % 100 == 0:  # Log progress every 100 bets
                logger.info(f"Processed {total_processed}/{len(all_bet_ids)} bet IDs")
        
        logger.info(f"Retrieved {len(unique_bets)} unique bets from date range {start_date} to {end_date}")
        return unique_bets
    except Exception as e:
        logger.error(f"Error retrieving bets from date range: {e}")
        # Fall back to the pagination method if the approach fails
        logger.info("Falling back to pagination method")
        return get_bets_by_date_range_paginated(start_date, end_date)

# Keep the original methods as fallbacks
def get_bets_last_24h_paginated():
    """Get bets added in the last 24 hours using pagination."""
    supabase = get_supabase_client()
    
    # Calculate 24 hours ago
    cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
    
    try:
        # Query bets from the last 24 hours with pagination
        all_bets = []
        page_size = 1000
        has_more = True
        start = 0
        
        while has_more:
            # Build query with pagination
            query = supabase.table("betting_data").select("*").gte("timestamp", cutoff_time)
            query = query.range(start, start + page_size - 1)
            
            # Execute query
            response = query.execute()
            bets = response.data
            
            if bets:
                all_bets.extend(bets)
                logger.info(f"Retrieved {len(bets)} bets from the last 24 hours (offset {start})")
                
                if len(bets) == page_size:
                    start += page_size
                else:
                    has_more = False
            else:
                has_more = False
        
        # Get only the most recent version of each bet
        unique_bets = get_most_recent_bets(all_bets)
        logger.info(f"Retrieved {len(all_bets)} total bets, filtered to {len(unique_bets)} unique bets")
        return unique_bets
    except Exception as e:
        logger.error(f"Error retrieving bets from last 24 hours with pagination: {e}")
        return []

def get_bets_by_date_range_paginated(start_date, end_date):
    """Get bets within a specific date range using pagination."""
    supabase = get_supabase_client()
    
    # Format end_date to include the entire day
    if end_date:
        end_date = f"{end_date}T23:59:59"
    
    try:
        # Query bets with pagination
        all_bets = []
        page_size = 1000
        has_more = True
        start = 0
        
        while has_more:
            # Build query with date filters and pagination
            query = supabase.table("betting_data").select("*")
            if start_date:
                query = query.gte("timestamp", start_date)
            if end_date:
                query = query.lte("timestamp", end_date)
            
            # Apply pagination
            query = query.range(start, start + page_size - 1)
            
            # Execute query
            response = query.execute()
            bets = response.data
            
            if bets:
                all_bets.extend(bets)
                logger.info(f"Retrieved {len(bets)} bets from date range (offset {start})")
                
                if len(bets) == page_size:
                    start += page_size
                else:
                    has_more = False
            else:
                has_more = False
        
        # Get only the most recent version of each bet
        unique_bets = get_most_recent_bets(all_bets)
        logger.info(f"Retrieved {len(all_bets)} total bets, filtered to {len(unique_bets)} unique bets from date range {start_date} to {end_date}")
        return unique_bets
    except Exception as e:
        logger.error(f"Error retrieving bets from date range with pagination: {e}")
        return []

def get_most_recent_bets(bets):
    """
    Filter a list of bets to get only the most recent version of each bet_id.
    
    Args:
        bets: List of bet records
        
    Returns:
        List of the most recent betting records for each bet_id
    """
    if not bets:
        return []
    
    # Group by bet_id and keep only the most recent
    latest_bets_by_id = {}
    for record in bets:
        bet_id = record.get("bet_id")
        timestamp = record.get("timestamp", "")
        
        if not bet_id or not timestamp:
            continue
            
        if bet_id not in latest_bets_by_id or timestamp > latest_bets_by_id[bet_id].get("timestamp", ""):
            latest_bets_by_id[bet_id] = record
    
    return list(latest_bets_by_id.values())

def process_bets(bets):
    """Process a list of bets and calculate grades."""
    if not bets:
        logger.info("No bets to process")
        return []
    
    logger.info(f"Processing {len(bets)} bets")
    
    # Calculate grades for all bets
    grades = []
    for bet in bets:
        grade_record = calculate_bet_grade(bet)
        if grade_record:
            grades.append(grade_record)
    
    logger.info(f"Calculated grades for {len(grades)} bets")
    return grades

def save_grades_to_csv(grades, filename):
    """Save grades to a CSV file."""
    if not grades:
        logger.info("No grades to save to CSV")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(grades)
    
    # Ensure directory exists
    os.makedirs(CSV_DIR, exist_ok=True)
    
    # Save to CSV
    csv_path = os.path.join(CSV_DIR, filename)
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved {len(grades)} grades to {csv_path}")

def upload_grades_to_supabase(grades):
    """Upload grades to Supabase in bulk."""
    if not grades:
        logger.info("No grades to upload to Supabase")
        return
    
    logger.info(f"Uploading {len(grades)} grades to Supabase")
    
    # Ensure we have unique bet_ids to avoid conflicts
    unique_grades = {}
    for grade in grades:
        bet_id = grade.get("bet_id")
        if bet_id:
            unique_grades[bet_id] = grade
    
    unique_grade_list = list(unique_grades.values())
    logger.info(f"Filtered to {len(unique_grade_list)} unique grades by bet_id")
    
    # Use batch_upsert with the unique list
    batch_upsert("bet_grades", unique_grade_list, "bet_id")
    logger.info("Upload complete")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Calculate grades for betting data.')
    parser.add_argument('--start-date', type=str, help='Start date for date range (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date for date range (YYYY-MM-DD)')
    return parser.parse_args()

def main():
    """Main function to run grade calculations."""
    try:
        logger.info("Starting grade calculator main function")
        # Parse command line arguments
        args = parse_arguments()
        start_time = datetime.now()
        
        # Debug log the arguments
        logger.info(f"Arguments received: start_date={args.start_date}, end_date={args.end_date}")
        
        # Determine which mode to run in
        if args.start_date:
            # Date range mode
            logger.info(f"Running in date range mode: {args.start_date} to {args.end_date or 'now'}")
            bets = get_bets_by_date_range(args.start_date, args.end_date)
        else:
            # Get most recent timestamp from database
            most_recent = get_most_recent_timestamp()
            if most_recent:
                logger.info(f"Running for most recent timestamp: {most_recent}")
                bets = get_bets_by_date_range(most_recent, most_recent)
            else:
                # Fallback to last 24 hours if no data exists
                logger.info("No existing bets found, falling back to last 24 hours mode")
                bets = get_bets_last_24h()
        
        # Process bets
        grades = process_bets(bets)
        
        if args.start_date:
            # Save to CSV with datestamp for date range mode
            datestamp = datetime.now().strftime("%Y%m%d")
            filename = f"full_grades_{datestamp}.csv"
            save_grades_to_csv(grades, filename)
        
        # Upload to Supabase
        upload_grades_to_supabase(grades)
        
        # Log completion
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Completed in {duration:.2f} seconds. Processed {len(bets)} bets, created {len(grades) if 'grades' in locals() else 0} grades.")
        
    except Exception as e:
        logger.error(f"Error in grade calculator: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Script running as __main__")
    main()
