# Database Schema

This document outlines the database schema used in the Positive EV application. The application uses Supabase as its database backend.

## Tables

### betting_data

Stores raw betting opportunities scraped from various sources.

| Column | Type | Description |
|--------|------|-------------|
| bet_id | Text | Unique identifier for each bet |
| timestamp | Timestamp | When the bet was scraped |
| event_time | Timestamp | When the event takes place |
| sport | Text | Sport category (e.g., Basketball, Hockey) |
| league | Text | Specific league (e.g., NBA, NHL) |
| description | Text | Full bet description |
| participant | Text | Player/Team the bet is for |
| bet_line | Text | Specific line for the bet |
| bet_type | Text | Type of bet (e.g., Moneyline, Point Spread) |
| bet_category | Text | Category (e.g., Player Props, Moneyline) |
| odds | Text | Betting odds |
| sportsbook | Text | Sportsbook offering the bet |
| win_probability | Decimal | Calculated win probability |
| ev_percent | Decimal | Expected value percentage |
| bet_size | Decimal | Recommended bet size |
| betid_timestamp | Text | Composite unique key (bet_id:timestamp) |

**Primary Key**: betid_timestamp
**Indexes**: 
- bet_id
- timestamp
- event_time
- sport, league
- betid_timestamp

### initial_bet_details

Stores the initial state of betting opportunities when first discovered.

| Column | Type | Description |
|--------|------|-------------|
| bet_id | Text | Unique identifier for each bet |
| initial_ev | Decimal | Expected value when bet was first seen |
| initial_odds | Text | Initial odds value when first seen |
| initial_line | Text | Initial betting line when first seen |
| first_seen | Timestamp | When the bet was first discovered |

**Primary Key**: bet_id
**Indexes**:
- bet_id
- first_seen

### bet_grades

Stores calculated grades and evaluation metrics for betting opportunities.

| Column | Type | Description |
|--------|------|-------------|
| bet_id | Text | Reference to betting_data.bet_id |
| grade | Char(1) | Letter grade (A-F) |
| calculated_at | Timestamp | When the grade was calculated |
| ev_score | Decimal | Expected value score (0-100) |
| timing_score | Decimal | Timing score (0-100) |
| historical_edge | Decimal | Historical edge score (0-100) |
| kelly_score | Decimal | Kelly Criterion score (0-100) |
| composite_score | Decimal | Overall weighted score (0-100) |

**Primary Key**: bet_id
**Indexes**:
- bet_id
- grade
- calculated_at

## Supported Values

### Sports
- Basketball
- Hockey
- Tennis
- Soccer
- Baseball
- Football
- MMA

### Leagues
- Basketball: NBA, NCAAB
- Hockey: NHL
- Tennis: WTA, ATP, ATP Challenger, ITF Men
- Soccer: Saudi League, Premier League, FA Cup, La Liga, Champions League, Europa League, Serie A
- Baseball: MLB
- Football: NFL, NCAAF
- MMA: UFC

### Bet Categories
- Moneyline
- Point Spread
- Player Props
- Total
- Other

## Grade Calculation Weights
- Expected Value (EV): 60%
- Market Edge: 30%
- Timing Score: 5%
- Kelly Criterion: 5%

## Grade Scale
- A: >= 90
- B: >= 80
- C: >= 70
- D: >= 65
- F: < 65 