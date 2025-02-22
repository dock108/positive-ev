# Automated Bet Outcome Evaluation System

This system automatically evaluates the outcomes of sports bets using o3-mini-high's internet search capabilities. It runs daily at 2 AM to process ungraded bets and can also be run on-demand for specific date ranges.

## Components

1. `add_outcome_evaluation_table.py`: Creates the database table for storing bet outcomes
2. `eval_bets.py`: Main script for evaluating bet outcomes
3. `setup_cron.py`: Sets up the daily cron job

## Database Schema

### bet_outcome_evaluation
- `evaluation_id`: Primary key
- `bet_id`: Foreign key to betting_data table
- `outcome`: WIN, LOSS, TIE, or UNCERTAIN
- `confidence_score`: 0-100 score indicating AI's confidence
- `evaluated_at`: Timestamp of evaluation
- `reasoning`: Explanation from o3-mini-high

## Usage

### Initial Setup

1. Create the evaluation table:
```bash
python add_outcome_evaluation_table.py
```

2. Set up the daily cron job:
```bash
python setup_cron.py
```

### Manual Evaluation

To evaluate bets for a specific date range:
```bash
python eval_bets.py --start 2024-02-01 --end 2024-02-15
```

To evaluate all ungraded bets:
```bash
python eval_bets.py
```

## Confidence Thresholds

- Confidence >= 80%: Outcome is automatically applied to betting_data table
- Confidence < 80%: Outcome is stored but requires manual review
- UNCERTAIN results: Always require manual review

## Logging

Logs are stored in `logs/bet_evaluation.log` and include:
- Number of bets evaluated
- Evaluation results and confidence scores
- Errors and exceptions

## Dependencies

Required Python packages:
- requests==2.31.0
- python-crontab==3.0.0

## Error Handling

The system handles various error cases:
- API failures
- Database errors
- Invalid bet data
- Network timeouts

All errors are logged for review and the system continues processing remaining bets. 