import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

# Database and table configuration
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"
OUTPUT_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/analysis/visualizations"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_data_from_db():
    """Load data from the model_work_table."""
    conn = sqlite3.connect(DB_PATH)
    try:
        query = """
        SELECT *
        FROM model_work_table
        """
        df = pd.read_sql_query(query, conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['event_time'] = pd.to_datetime(df['event_time'])
        return df
    except Exception as e:
        print(f"Error loading data from the database: {e}")
    finally:
        conn.close()


def visualize_ev_distribution(df):
    """Visualize EV Percent distribution."""
    plt.figure(figsize=(12, 6))
    sns.histplot(data=df, x='ev_percent', hue='bet_time_category', multiple="stack", bins=30)
    plt.title("EV Distribution by Bet Timing Category")
    plt.xlabel("EV Percent")
    plt.ylabel("Count")
    plt.savefig(f"{OUTPUT_DIR}/ev_distribution.png")
    plt.close()


def visualize_player_stats(df):
    """Visualize player stats correlations."""
    # Get all player stat columns
    stat_cols = [col for col in df.columns if any(x in col for x in ['_avg', '_std', '_trend', '_consistency'])]
    if stat_cols:
        plt.figure(figsize=(15, 12))
        correlation_matrix = df[stat_cols].corr()
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, fmt='.2f')
        plt.title("Player Stats Correlation Matrix")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/player_stats_correlation.png")
        plt.close()


def visualize_win_rates(df):
    """Visualize win rates across different dimensions."""
    # Win rate by bet timing
    plt.figure(figsize=(10, 6))
    win_rates = df.groupby('bet_time_category')['result'].apply(
        lambda x: (x == 'W').mean()
    ).sort_values(ascending=False)
    
    sns.barplot(x=win_rates.index, y=win_rates.values)
    plt.title('Win Rate by Bet Timing Category')
    plt.ylabel('Win Rate')
    plt.savefig(f"{OUTPUT_DIR}/win_rates_timing.png")
    plt.close()

    # Win rate by EV bucket
    plt.figure(figsize=(10, 6))
    df['ev_bucket'] = pd.qcut(df['ev_percent'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
    win_rates_ev = df.groupby('ev_bucket')['result'].apply(lambda x: (x == 'W').mean())
    
    sns.barplot(x=win_rates_ev.index, y=win_rates_ev.values)
    plt.title('Win Rate by EV Bucket')
    plt.ylabel('Win Rate')
    plt.savefig(f"{OUTPUT_DIR}/win_rates_ev.png")
    plt.close()


def visualize_clv_analysis(df):
    """Visualize Closing Line Value analysis."""
    plt.figure(figsize=(12, 6))
    sns.boxplot(x='bet_time_category', y='clv_percent', data=df)
    plt.title('CLV Distribution by Bet Timing')
    plt.ylabel('CLV Percent')
    plt.savefig(f"{OUTPUT_DIR}/clv_by_timing.png")
    plt.close()

    # CLV trend over time
    plt.figure(figsize=(12, 6))
    daily_clv = df.groupby(df['timestamp'].dt.date)['clv_percent'].mean()
    daily_clv.plot(kind='line')
    plt.title('Average Daily CLV%')
    plt.xlabel('Date')
    plt.ylabel('Average CLV%')
    plt.grid(True)
    plt.savefig(f"{OUTPUT_DIR}/clv_trend.png")
    plt.close()


def generate_summary_report(df):
    """Generate a summary report of key metrics."""
    with open(f"{OUTPUT_DIR}/summary_report.txt", 'w') as f:
        f.write("Model Performance Summary\n")
        f.write("=======================\n\n")
        
        # Overall metrics
        f.write(f"Total Bets Analyzed: {len(df)}\n")
        f.write(f"Overall Win Rate: {(df['result'] == 'W').mean():.2%}\n")
        f.write(f"Average EV%: {df['ev_percent'].mean():.2f}%\n")
        f.write(f"Average CLV%: {df['clv_percent'].mean():.2f}%\n\n")
        
        # Win rates by timing
        f.write("Win Rates by Timing:\n")
        timing_wins = df.groupby('bet_time_category')['result'].apply(
            lambda x: f"{(x == 'W').mean():.2%}"
        )
        for category, rate in timing_wins.items():
            f.write(f"{category}: {rate}\n")
        
        # Player stats summary
        f.write("\nPlayer Stats Summary:\n")
        stat_cols = [col for col in df.columns if '_avg' in col]
        for col in stat_cols:
            f.write(f"{col}: {df[col].mean():.2f}\n")


def main():
    """Main function to generate all visualizations."""
    print("Loading data from database...")
    df = load_data_from_db()

    if df is not None and not df.empty:
        print(f"Data loaded successfully. Found {len(df)} rows.")
        
        print("Generating visualizations...")
        visualize_ev_distribution(df)
        visualize_player_stats(df)
        visualize_win_rates(df)
        visualize_clv_analysis(df)
        generate_summary_report(df)
        
        print("Visualizations completed. Check the output directory for results.")
    else:
        print("No data found in the model_work_table.")


if __name__ == "__main__":
    main()
