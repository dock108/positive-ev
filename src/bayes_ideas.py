#!/usr/bin/env python3
"""
Bayesian Analysis Test Script
=============================

This script tests new Bayesian approaches against the current implementation
by pulling 100 recent betting records and comparing results.

The primary goal is to implement a more rigorous Bayesian approach focused on:
P(beat closing line value|signals)

Usage:
    python src/bayes_ideas.py

Author: highlyprofitable108
Created: March 2025
"""

import os
import sys
import pandas as pd
import json
from datetime import datetime

# Add the project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import from grade_calculator and other modules
try:
    from src.config import setup_logging
    from src.supabase_client import get_supabase_client
    from src.grade_calculator import (
        calculate_bayesian_confidence,
        calculate_true_bayesian_confidence,
        standardize_datetime,
        safe_float
    )
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Setup logging
logger = setup_logging("logs/bayes_debug.log", "bayes_debug")
supabase = get_supabase_client()

def get_recent_bets(limit=100):
    """
    Fetch the most recent unique betting records.
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of unique betting records
    """
    try:
        logger.info(f"Fetching {limit} recent betting records")
        
        # Get the most recent records
        response = supabase.table("betting_data").select("*").order("timestamp", desc=True).limit(limit * 3).execute()
        
        if not response.data:
            logger.warning("No betting records found")
            return []
            
        # Get unique bet_ids (keeping most recent version)
        unique_bets = {}
        for bet in response.data:
            bet_id = bet.get("bet_id")
            if bet_id and bet_id not in unique_bets:
                unique_bets[bet_id] = bet
                
            # Stop once we have enough unique bets
            if len(unique_bets) >= limit:
                break
                
        bets_list = list(unique_bets.values())
        logger.info(f"Retrieved {len(bets_list)} unique betting records")
        return bets_list
    except Exception as e:
        logger.error(f"Error fetching recent bets: {e}")
        return []

def get_historical_bets_with_outcomes(limit=500):
    """
    Fetch historical bets that have closing line data for training/evaluation.
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        Dictionary mapping bet_id to bet data with closing line outcome
    """
    try:
        logger.info(f"Fetching up to {limit} historical bets with outcomes")
        
        # Query historical_bets or actual_bets table that contains closing line data
        response = supabase.table("actual_bets").select("*").limit(limit).execute()
        
        if not response.data:
            logger.warning("No historical bets with outcomes found")
            return {}
            
        # Create mapping from bet_id to bet data with outcome
        historical_data = {}
        for record in response.data:
            bet_id = record.get("bet_id")
            if bet_id and "beat_closing_line" in record:
                historical_data[bet_id] = record
                
        logger.info(f"Retrieved {len(historical_data)} historical bets with outcome data")
        return historical_data
    except Exception as e:
        logger.error(f"Error fetching historical bets: {e}")
        return {}

def calibrate_bayesian_priors(historical_data):
    """
    Calibrate Bayesian prior probabilities using historical data.
    
    Args:
        historical_data: Dictionary of historical bets with outcomes
        
    Returns:
        Dictionary of calibrated prior probabilities
    """
    try:
        logger.info("Calibrating Bayesian priors from historical data")
        
        if not historical_data:
            logger.warning("No historical data available for calibration, using default priors")
            return {
                "prior_beat_clv": 0.52,  # Default prior probability
                "ev_change_coefficients": {
                    "positive": {"base": 0.7, "factor": 0.1, "max": 0.9},
                    "negative": {"base": 0.3, "factor": 0.1, "min": 0.1}
                },
                "timing_thresholds": {
                    1: 0.90,   # <1 hour
                    3: 0.80,   # 1-3 hours
                    6: 0.70,   # 3-6 hours
                    12: 0.60,  # 6-12 hours
                    24: 0.50,  # 12-24 hours
                    float('inf'): 0.40  # >24 hours
                }
            }
        
        # Count how many bets beat the closing line
        beat_clv_count = sum(1 for data in historical_data.values() 
                            if data.get('beat_closing_line', False) is True)
        total_count = len(historical_data)
        
        # Calculate prior probability
        prior_beat_clv = beat_clv_count / total_count if total_count > 0 else 0.52
        
        # Analyze EV changes
        positive_ev_changes = []
        negative_ev_changes = []
        timing_data = {
            1: {"beat": 0, "total": 0},    # <1 hour
            3: {"beat": 0, "total": 0},    # 1-3 hours
            6: {"beat": 0, "total": 0},    # 3-6 hours
            12: {"beat": 0, "total": 0},   # 6-12 hours
            24: {"beat": 0, "total": 0},   # 12-24 hours
            float('inf'): {"beat": 0, "total": 0}  # >24 hours
        }
        
        for bet_id, data in historical_data.items():
            # Get initial EV data
            initial_ev_response = supabase.table("initial_bet_details").select("*").eq("bet_id", bet_id).execute()
            if not initial_ev_response.data:
                continue
                
            initial_data = initial_ev_response.data[0]
            initial_ev = safe_float(initial_data.get('initial_ev'))
            current_ev = safe_float(data.get('ev_percent'))
            
            if initial_ev is not None and current_ev is not None:
                ev_change = current_ev - initial_ev
                beat_clv = data.get('beat_closing_line', False)
                
                if ev_change > 0:
                    positive_ev_changes.append((ev_change, beat_clv))
                else:
                    negative_ev_changes.append((ev_change, beat_clv))
            
            # Calculate timing data
            event_time = data.get('event_time')
            timestamp = data.get('timestamp')
            
            if event_time and timestamp:
                event_dt = standardize_datetime(event_time)
                bet_dt = standardize_datetime(timestamp)
                
                hours_until_event = (event_dt - bet_dt).total_seconds() / 3600
                beat_clv = data.get('beat_closing_line', False)
                
                # Add to timing buckets
                for threshold in timing_data.keys():
                    if hours_until_event < threshold:
                        timing_data[threshold]["total"] += 1
                        if beat_clv:
                            timing_data[threshold]["beat"] += 1
                        break
        
        # Calculate EV change coefficients
        positive_ev_coef = {"base": 0.7, "factor": 0.1, "max": 0.9}
        negative_ev_coef = {"base": 0.3, "factor": 0.1, "min": 0.1}
        
        # Calculate timing thresholds
        timing_thresholds = {}
        for threshold, counts in timing_data.items():
            if counts["total"] > 0:
                timing_thresholds[threshold] = counts["beat"] / counts["total"]
            else:
                # Use default values if no data
                if threshold == 1:
                    timing_thresholds[threshold] = 0.90
                elif threshold == 3:
                    timing_thresholds[threshold] = 0.80
                elif threshold == 6:
                    timing_thresholds[threshold] = 0.70
                elif threshold == 12:
                    timing_thresholds[threshold] = 0.60
                elif threshold == 24:
                    timing_thresholds[threshold] = 0.50
                else:
                    timing_thresholds[threshold] = 0.40
        
        calibrated_priors = {
            "prior_beat_clv": prior_beat_clv,
            "ev_change_coefficients": {
                "positive": positive_ev_coef,
                "negative": negative_ev_coef
            },
            "timing_thresholds": timing_thresholds
        }
        
        logger.info(f"Calibrated prior P(Beat CLV): {prior_beat_clv:.3f}")
        logger.info(f"Calibrated timing thresholds: {timing_thresholds}")
        
        return calibrated_priors
    except Exception as e:
        logger.error(f"Error calibrating Bayesian priors: {e}")
        # Return default values on error
        return {
            "prior_beat_clv": 0.52,
            "ev_change_coefficients": {
                "positive": {"base": 0.7, "factor": 0.1, "max": 0.9},
                "negative": {"base": 0.3, "factor": 0.1, "min": 0.1}
            },
            "timing_thresholds": {
                1: 0.90, 3: 0.80, 6: 0.70, 12: 0.60, 24: 0.50, float('inf'): 0.40
            }
        }

def calculate_new_bayesian_score(bet, historical_data, calibrated_priors):
    """
    Calculate P(beat closing line value|signals) using proper Bayesian approach.
    
    Args:
        bet: Betting record
        historical_data: Dictionary with historical bet outcomes
        calibrated_priors: Dictionary with calibrated prior probabilities
        
    Returns:
        Bayesian score (0-100) and debug info
    """
    try:
        bet_id = bet.get('bet_id')
        current_ev = safe_float(bet.get('ev_percent'))
        event_time = bet.get('event_time')
        timestamp = bet.get('timestamp')
        
        debug_info = {
            "bet_id": bet_id,
            "current_ev": current_ev,
            "event_time": event_time,
            "timestamp": timestamp,
            "signals": {},
            "probabilities": {}
        }
        
        if not all([bet_id, current_ev, event_time, timestamp]):
            return 50, {"error": "Missing required data"}
        
        # Get initial EV from initial_bet_details
        response = supabase.table("initial_bet_details").select("*").eq("bet_id", bet_id).execute()
        if not response.data:
            return 50, {"error": "No initial details found"}
            
        initial_data = response.data[0]
        initial_ev = safe_float(initial_data.get('initial_ev'))
        first_seen = initial_data.get('first_seen')
        
        debug_info["initial_ev"] = initial_ev
        debug_info["first_seen"] = first_seen
        
        # 1. Prior probability P(Beat CLV) from calibrated priors
        prior_beat_clv = calibrated_priors["prior_beat_clv"]
        debug_info["probabilities"]["prior"] = prior_beat_clv
        
        # 2. Calculate Likelihoods for each signal
        
        # 2a. EV Change Signal
        ev_change = current_ev - initial_ev
        ev_change_magnitude = abs(ev_change) / max(abs(initial_ev), 0.1)
        
        debug_info["signals"]["ev_change"] = {
            "raw_change": ev_change,
            "magnitude": ev_change_magnitude
        }
        
        # Likelihood P(EV Signal|Beat CLV) using calibrated coefficients
        ev_coef = calibrated_priors["ev_change_coefficients"]
        if ev_change > 0:
            # Positive EV changes more likely when bet will beat CLV
            base = ev_coef["positive"]["base"]
            factor = ev_coef["positive"]["factor"]
            max_val = ev_coef["positive"]["max"]
            p_ev_signal_given_beat = min(base + (ev_change_magnitude * factor), max_val)
        else:
            # Negative EV changes less likely when bet will beat CLV
            base = ev_coef["negative"]["base"]
            factor = ev_coef["negative"]["factor"]
            min_val = ev_coef["negative"]["min"]
            p_ev_signal_given_beat = max(base - (ev_change_magnitude * factor), min_val)
            
        debug_info["probabilities"]["ev_signal_given_beat"] = p_ev_signal_given_beat
        
        # 2b. Timing Signal
        current_dt = standardize_datetime(timestamp)
        event_dt = standardize_datetime(event_time)
        
        hours_until_event = (event_dt - current_dt).total_seconds() / 3600
        debug_info["signals"]["hours_until_event"] = hours_until_event
        
        # Likelihood P(Timing Signal|Beat CLV) using calibrated thresholds
        timing_thresholds = calibrated_priors["timing_thresholds"]
        p_timing_signal_given_beat = None
        
        # Find appropriate threshold
        for threshold in sorted(timing_thresholds.keys()):
            if hours_until_event < threshold:
                p_timing_signal_given_beat = timing_thresholds[threshold]
                break
                
        # Default value if no threshold matches (should not happen)
        if p_timing_signal_given_beat is None:
            p_timing_signal_given_beat = 0.40
            
        debug_info["probabilities"]["timing_signal_given_beat"] = p_timing_signal_given_beat
        
        # 3. Calculate P(Signals|~Beat CLV) - Probability of observing signals if bet won't beat CLV
        # These are the complement probabilities (could be refined with more data)
        p_ev_signal_given_not_beat = 1 - p_ev_signal_given_beat
        p_timing_signal_given_not_beat = 1 - p_timing_signal_given_beat
        
        debug_info["probabilities"]["ev_signal_given_not_beat"] = p_ev_signal_given_not_beat
        debug_info["probabilities"]["timing_signal_given_not_beat"] = p_timing_signal_given_not_beat
        
        # 4. Calculate P(Signals) using law of total probability
        # P(Signals) = P(Signals|Beat CLV) * P(Beat CLV) + P(Signals|~Beat CLV) * P(~Beat CLV)
        p_signals = (
            (p_ev_signal_given_beat * p_timing_signal_given_beat * prior_beat_clv) + 
            (p_ev_signal_given_not_beat * p_timing_signal_given_not_beat * (1 - prior_beat_clv))
        )
        debug_info["probabilities"]["signals"] = p_signals
        
        # 5. Apply Bayes Theorem
        # P(Beat CLV|Signals) = P(Signals|Beat CLV) * P(Beat CLV) / P(Signals)
        posterior = (
            (p_ev_signal_given_beat * p_timing_signal_given_beat * prior_beat_clv) / 
            p_signals
        )
        debug_info["probabilities"]["posterior"] = posterior
        
        # Convert to 0-100 scale
        bayesian_score = posterior * 100
        debug_info["final_score"] = bayesian_score
        
        # Check ground truth if available in historical data (for evaluation only)
        if bet_id in historical_data:
            actual_beat_clv = historical_data[bet_id].get("beat_closing_line", False)
            debug_info["actual_beat_clv"] = actual_beat_clv
        
        return bayesian_score, debug_info
        
    except Exception as e:
        logger.error(f"Error calculating new Bayesian score: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 50, {"error": str(e)}

def compare_bayesian_approaches(bets, historical_data, calibrated_priors):
    """
    Compare current and new Bayesian approaches.
    
    Args:
        bets: List of betting records
        historical_data: Dictionary with historical bet outcomes
        calibrated_priors: Dictionary with calibrated prior probabilities
        
    Returns:
        DataFrame with comparison results
    """
    results = []
    
    for bet in bets:
        bet_id = bet.get('bet_id')
        current_ev = bet.get('ev_percent')
        event_time = bet.get('event_time')
        timestamp = bet.get('timestamp')
        
        # Skip bets with missing critical data
        if not all([bet_id, current_ev, event_time, timestamp]):
            logger.warning(f"Skipping bet {bet_id} - Missing required data")
            continue
        
        # Calculate scores using both approaches
        current_score = calculate_bayesian_confidence(current_ev, bet_id, event_time, timestamp)
        true_score, true_debug_info = calculate_true_bayesian_confidence(current_ev, bet_id, event_time, timestamp)
        new_score, new_debug_info = calculate_new_bayesian_score(bet, historical_data, calibrated_priors)
        
        # Get actual outcome if available in historical data
        actual_beat_clv = None
        if bet_id in historical_data:
            actual_beat_clv = historical_data[bet_id].get("beat_closing_line", None)
        
        # Add to results
        results.append({
            "bet_id": bet_id,
            "current_bayesian_score": current_score,
            "true_bayesian_score": true_score,
            "new_bayesian_score": new_score,
            "ev_percent": current_ev,
            "event_time": event_time,
            "timestamp": timestamp,
            "hours_to_event": (standardize_datetime(event_time) - standardize_datetime(timestamp)).total_seconds() / 3600,
            "actual_beat_clv": actual_beat_clv,
            "current_debug": "Heuristic scoring system",
            "true_debug": json.dumps(true_debug_info),
            "new_debug": json.dumps(new_debug_info)
        })
    
    return pd.DataFrame(results)

def main():
    """Main function to compare Bayesian approaches."""
    try:
        logger.info("Starting Bayesian analysis comparison")
        
        # Get recent betting records to analyze
        bets = get_recent_bets(limit=100)
        if not bets:
            logger.error("No betting records available for analysis")
            return
        
        # Get historical bets with outcomes for training/evaluation
        historical_data = get_historical_bets_with_outcomes(limit=500)
        
        # Calibrate Bayesian priors using historical data
        calibrated_priors = calibrate_bayesian_priors(historical_data)
        
        # Compare approaches
        results_df = compare_bayesian_approaches(bets, historical_data, calibrated_priors)
        
        # Save results to CSV
        output_file = "data/bayesian_comparison.csv"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        results_df.to_csv(output_file, index=False)
        logger.info(f"Saved comparison results to {output_file}")
        
        # Print summary statistics
        logger.info("\n=== BAYESIAN APPROACH COMPARISON ===")
        logger.info(f"Total bets analyzed: {len(results_df)}")
        
        # Calculate mean absolute error for each approach (if ground truth available)
        if not all(results_df["actual_beat_clv"].isna()):
            # Convert actual_beat_clv to 0-100 scale (100 if True, 0 if False)
            results_df["actual_score"] = results_df["actual_beat_clv"].map({True: 100, False: 0})
            
            # Calculate errors
            results_df["current_error"] = abs(results_df["current_bayesian_score"] - results_df["actual_score"])
            results_df["true_error"] = abs(results_df["true_bayesian_score"] - results_df["actual_score"])
            results_df["new_error"] = abs(results_df["new_bayesian_score"] - results_df["actual_score"])
            
            # Log mean errors
            logger.info(f"Current approach mean error: {results_df['current_error'].mean():.2f}")
            logger.info(f"True Bayesian approach mean error: {results_df['true_error'].mean():.2f}")
            logger.info(f"New Bayesian approach mean error: {results_df['new_error'].mean():.2f}")
        
        # Average scores
        logger.info(f"Current approach average score: {results_df['current_bayesian_score'].mean():.2f}")
        logger.info(f"True Bayesian approach average score: {results_df['true_bayesian_score'].mean():.2f}")
        logger.info(f"New Bayesian approach average score: {results_df['new_bayesian_score'].mean():.2f}")
        
        logger.info("========================================")
        
        print(f"Analysis complete! Results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()