# Bayesian Analysis Plan for Betting Optimization

## Overview

This document outlines our plan to implement a comprehensive Bayesian analysis framework for betting optimization. The core goal is to develop a model that accurately calculates P(beat closing line value|signals) using proper Bayesian methods and historical bet data.

## Current Status

We've created a prototype implementation in `src/bayes_ideas.py` that:

1. Fetches recent betting records from the `betting_data` table
2. Retrieves historical bet outcomes from the `actual_bets` table
3. Calibrates Bayesian priors based on historical data
4. Compares three approaches:
   - Current heuristic-based confidence score
   - Existing `calculate_true_bayesian_confidence` implementation
   - New proper Bayesian approach

## Implementation Phases

### Phase 1: Data Preparation and Exploration (Current)

- [x] Create prototype Bayesian implementation
- [ ] Fix linter issues in prototype code
- [ ] Ensure proper linking between `betting_data` and `actual_bets` tables
- [ ] Define and create schema for `actual_bets` table
- [ ] Perform exploratory data analysis on historical bets:
  - Analyze distribution of CLV outcomes
  - Identify correlations between signals and CLV outcomes
  - Visualize timing/EV change patterns

### Phase 2: Model Refinement

- [ ] Refine calibration process:
  - Incorporate more features beyond EV changes and timing
  - Explore non-linear relationships in the data
  - Calculate proper conditional probabilities from historical data
- [ ] Implement cross-validation to evaluate model stability
- [ ] Create visualizations to interpret model behavior
- [ ] Add confidence intervals to Bayesian estimates

### Phase 3: Integration and Production

- [ ] Integrate refined Bayesian model into the grade calculator
- [ ] Create weekly learning process to continuously update priors
- [ ] Implement scikit-learn models for comparison:
  - Logistic regression as baseline
  - Random Forest for nonlinear patterns
  - Gradient Boosting for optimal performance
- [ ] Develop A/B testing framework to evaluate model performance in production

### Phase 4: Advanced Features

- [ ] Implement hierarchical Bayesian modeling to account for:
  - Sport-specific differences
  - Bookmaker-specific patterns
  - Time-based effects (season, day of week)
- [ ] Add Bayesian decision theory for bet sizing optimization
- [ ] Implement sequential Bayesian updating for real-time CLV predictions

## Data Sources

1. **Betting Data Table**
   - Contains all available betting opportunities
   - Features: EV percent, odds, win probability, event time, timestamp
   - Available for all potential bets

2. **Actual Bets Table**
   - Contains historical bets we've placed
   - Includes outcomes: win/loss and whether bet beat the closing line
   - Will be used for training and validation
   
   Schema Requirements:
   ```sql
   CREATE TABLE actual_bets (
       bet_id TEXT PRIMARY KEY,
       timestamp TIMESTAMP NOT NULL,      -- When bet was placed
       event_time TIMESTAMP NOT NULL,     -- When event starts
       odds NUMERIC NOT NULL,             -- Odds we got
       closing_odds NUMERIC NOT NULL,     -- Final odds before event
       bet_amount NUMERIC NOT NULL,       -- Amount wagered
       win_loss BOOLEAN,                  -- Outcome (NULL if pending)
       beat_closing_line BOOLEAN,         -- Whether we beat closing line
       ev_percent NUMERIC NOT NULL,       -- EV at time of bet
       win_probability NUMERIC NOT NULL,  -- Win prob at time of bet
       sport TEXT NOT NULL,               -- Sport category
       bookmaker TEXT NOT NULL,           -- Sportsbook used
       bet_type TEXT NOT NULL,           -- Type of bet (spread, ML, etc.)
       line NUMERIC,                     -- Line/spread if applicable
       closing_line NUMERIC,             -- Final line/spread
       profit_loss NUMERIC,              -- Actual P/L (NULL if pending)
       FOREIGN KEY (bet_id) REFERENCES betting_data(bet_id)
   )
   ```

3. **Initial Bet Details Table**
   - Contains the initial values when bets were first seen
   - Used to calculate changes in EV and other metrics over time

## Bayesian Framework

Our core Bayesian approach will focus on:

P(Beat CLV|Signals) = P(Signals|Beat CLV) × P(Beat CLV) / P(Signals)

Where:
- P(Beat CLV) = Prior probability of beating closing line value
- P(Signals|Beat CLV) = Likelihood of observing our signals given a bet beats CLV
- P(Signals) = Overall probability of observing these signals

### Signals to Include

1. **EV Change Patterns**
   - Direction (positive/negative)
   - Magnitude
   - Rate of change
   - Volatility

2. **Timing Factors**
   - Hours until event
   - Time of day
   - Day of week
   - Season factors

3. **Market Signals**
   - Line movement patterns
   - Volume indicators (if available)
   - Sharp book vs. square book differences

4. **Historical Performance**
   - Sport-specific CLV rates
   - Book-specific CLV rates
   - Similar bet type performance

## Integration with Grade Calculator

The Bayesian model will integrate with the grade calculator by:
1. Providing a more accurate confidence score
2. Improving the overall grade by better weighting CLV probability
3. Offering better risk assessment for bet sizing

## Weekly Learning Process

We'll implement a weekly learning process that:
1. Processes new actual bet outcomes
2. Updates prior probabilities
3. Recalibrates conditional probabilities
4. Validates model against recent performance
5. Generates reports on model accuracy

## Next Steps

1. Fix linter issues in the prototype code
2. Build data exploration pipeline
3. Create and populate actual_bets table with historical data
4. Implement initial scikit-learn models for comparison
5. Develop visualization framework for evaluating model performance 