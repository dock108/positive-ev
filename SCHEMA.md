# Database Schema

This document outlines the database schema used in the Positive EV application, which utilizes Supabase as its database backend.

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

### bet_grades

Stores grades and evaluation scores for betting opportunities.

| Column | Type | Description |
|--------|------|-------------|
| bet_id | Text | Unique identifier for each bet |
| grade | Text | Letter grade (A, B, C, D, F) assigned to the bet |
| calculated_at | Timestamp | When the grade was calculated |
| ev_score | Decimal | Score based on Expected Value (0-100) |
| timing_score | Decimal | Score based on time until event (0-100) |
| ev_trend_score | Decimal | Score based on EV changes since first seen (0-100) |
| bayesian_confidence | Decimal | Bayesian confidence score using multiple factors (0-100) |
| composite_score | Decimal | Weighted combination of all component scores |
| grading_method | Text | Method used for grading (currently "absolute") |

**Primary Key**: bet_id  
**Indexes**:  
- bet_id
- grade
- calculated_at