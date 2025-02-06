import os
import sqlite3
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Paths
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"
LOG_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/logs/"
LOG_FILE = os.path.join(LOG_DIR, "eda.log")
OUTPUT_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/analysis"

# Ensure directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=LOG_FILE, 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_data():
    """Load and preprocess data from model_work_table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM model_work_table", conn)
        conn.close()
        logging.info(f"Loaded {len(df)} rows from model_work_table")
        
        # Convert timestamps and event times
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['event_time'] = pd.to_datetime(df['event_time'])
        
        # Convert numeric columns
        numeric_cols = [
            'ev_percent', 'first_odds', 'final_odds', 'line_movement',
            'bet_size', 'win_probability', 'market_implied_prob', 'clv_percent',
            'time_to_event'
        ]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Add derived features
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        df['month'] = df['timestamp'].dt.month_name()
        
        return df
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        raise

def analyze_win_rates(df):
    """Analyze win rates across different dimensions."""
    plt.figure(figsize=(15, 10))
    
    # Win rate by bet timing
    win_rates = df.groupby('bet_time_category')['result'].apply(
        lambda x: (x == 'W').mean()
    ).sort_values(ascending=False)
    
    sns.barplot(x=win_rates.index, y=win_rates.values)
    plt.title('Win Rate by Bet Timing Category')
    plt.ylabel('Win Rate')
    plt.savefig(os.path.join(OUTPUT_DIR, 'win_rates_timing.png'))
    plt.close()
    
    # Win rate by EV% buckets
    df['ev_bucket'] = pd.qcut(df['ev_percent'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
    win_rates_ev = df.groupby('ev_bucket')['result'].apply(
        lambda x: (x == 'W').mean()
    )
    
    plt.figure(figsize=(15, 10))
    sns.barplot(x=win_rates_ev.index, y=win_rates_ev.values)
    plt.title('Win Rate by EV% Bucket')
    plt.ylabel('Win Rate')
    plt.savefig(os.path.join(OUTPUT_DIR, 'win_rates_ev.png'))
    plt.close()

def analyze_player_stats(df):
    """Analyze player statistics and their relationship with outcomes."""
    player_stats = [col for col in df.columns if any(x in col for x in ['_avg', '_std', '_trend', '_consistency'])]
    
    if not player_stats:
        logging.info("No player stats columns found")
        return
        
    # Correlation with win probability
    stats_corr = df[player_stats + ['win_probability']].corr()['win_probability'].sort_values()
    
    plt.figure(figsize=(15, 10))
    sns.heatmap(df[player_stats].corr(), annot=True, cmap='coolwarm', center=0)
    plt.title('Player Stats Correlation Matrix')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'player_stats_correlation.png'))
    plt.close()
    
    # Win rate by consistency score buckets
    consistency_cols = [col for col in df.columns if 'consistency' in col]
    for col in consistency_cols:
        df[f'{col}_bucket'] = pd.qcut(df[col].fillna(df[col].mean()), q=5, 
                                    labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
        win_rates = df.groupby(f'{col}_bucket')['result'].apply(
            lambda x: (x == 'W').mean()
        )
        
        plt.figure(figsize=(12, 8))
        sns.barplot(x=win_rates.index, y=win_rates.values)
        plt.title(f'Win Rate by {col}')
        plt.ylabel('Win Rate')
        plt.savefig(os.path.join(OUTPUT_DIR, f'win_rates_{col}.png'))
        plt.close()

def analyze_market_dynamics(df):
    """Analyze market dynamics and their impact on outcomes."""
    plt.figure(figsize=(15, 10))
    
    # Line movement analysis
    sns.boxplot(x='result', y='line_movement', data=df)
    plt.title('Line Movement Distribution by Result')
    plt.savefig(os.path.join(OUTPUT_DIR, 'line_movement_by_result.png'))
    plt.close()
    
    # CLV analysis
    plt.figure(figsize=(15, 10))
    sns.boxplot(x='result', y='clv_percent', data=df)
    plt.title('CLV Distribution by Result')
    plt.savefig(os.path.join(OUTPUT_DIR, 'clv_by_result.png'))
    plt.close()
    
    # Time series of average CLV
    daily_clv = df.groupby(df['timestamp'].dt.date)['clv_percent'].mean()
    plt.figure(figsize=(15, 10))
    daily_clv.plot()
    plt.title('Average Daily CLV%')
    plt.savefig(os.path.join(OUTPUT_DIR, 'daily_clv_trend.png'))
    plt.close()

def generate_summary_report(df):
    """Generate a summary report of key findings."""
    with open(os.path.join(OUTPUT_DIR, 'summary_report.txt'), 'w') as f:
        f.write("Model Work Table Analysis Summary\n")
        f.write("================================\n\n")
        
        f.write(f"Total Bets Analyzed: {len(df)}\n")
        f.write(f"Overall Win Rate: {(df['result'] == 'W').mean():.2%}\n")
        f.write(f"Average EV%: {df['ev_percent'].mean():.2f}%\n")
        f.write(f"Average CLV%: {df['clv_percent'].mean():.2f}%\n\n")
        
        f.write("Win Rate by Timing Category:\n")
        win_rates = df.groupby('bet_time_category')['result'].apply(
            lambda x: (x == 'W').mean()
        )
        for category, rate in win_rates.items():
            f.write(f"{category}: {rate:.2%}\n")

if __name__ == "__main__":
    logging.info("Starting EDA process")
    
    try:
        df = load_data()
        
        analyze_win_rates(df)
        logging.info("Completed win rate analysis")
        
        analyze_player_stats(df)
        logging.info("Completed player stats analysis")
        
        analyze_market_dynamics(df)
        logging.info("Completed market dynamics analysis")
        
        generate_summary_report(df)
        logging.info("Generated summary report")
        
    except Exception as e:
        logging.error(f"Error in EDA process: {e}", exc_info=True)
    
    logging.info("EDA process completed")
