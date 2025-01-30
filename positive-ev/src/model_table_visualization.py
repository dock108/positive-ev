import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Database and table configuration
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"


def load_data_from_db():
    """Load data from the model_work_table."""
    conn = sqlite3.connect(DB_PATH)
    try:
        query = """
        SELECT *
        FROM model_work_table
        """
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"Error loading data from the database: {e}")
    finally:
        conn.close()


def visualize_ev_distribution(df):
    """Visualize EV Percent distribution."""
    plt.figure(figsize=(10, 6))
    sns.histplot(df['ev_percent'], kde=True, bins=20, color='blue')
    plt.title("EV Percent Distribution", fontsize=16)
    plt.xlabel("EV Percent", fontsize=12)
    plt.ylabel("Frequency", fontsize=12)
    plt.show()


def visualize_time_to_event(df):
    """Visualize time to event distribution."""
    plt.figure(figsize=(10, 6))
    sns.histplot(df['time_to_event'], kde=True, bins=20, color='green')
    plt.title("Time to Event Distribution", fontsize=16)
    plt.xlabel("Time to Event (minutes)", fontsize=12)
    plt.ylabel("Frequency", fontsize=12)
    plt.show()


def visualize_bets_by_sport(df):
    """Visualize the number of bets per sport league."""
    plt.figure(figsize=(12, 6))
    sport_counts = df["sport_league"].value_counts()
    sns.barplot(x=sport_counts.index, y=sport_counts.values, palette="muted")
    plt.title("Bets by Sport League", fontsize=16)
    plt.xlabel("Sport League", fontsize=12)
    plt.ylabel("Count", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.show()


def visualize_odds_vs_opportunity(df):
    """Scatter plot of odds vs opportunity value."""
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x="odds", y="opportunity_value", hue="sport_league", palette="deep")
    plt.title("Odds vs Opportunity Value", fontsize=16)
    plt.xlabel("Odds", fontsize=12)
    plt.ylabel("Opportunity Value", fontsize=12)
    plt.legend(title="Sport League")
    plt.axvline(-100, color='red', linestyle='--', label='Skipped Range (-100 to 100)')
    plt.axvline(100, color='red', linestyle='--')
    plt.grid(True)
    plt.show()


def calculate_net_profit_loss(df):
    """Calculate net profit/loss."""
    df["net"] = 0.0

    for index, row in df.iterrows():
        bet_size = row["bet_size"]
        odds = row["odds"]
        result = row["result"]  # Assuming 'W' for win, 'L' for loss

        # Calculate payout based on American odds
        if odds > 0:  # Positive odds
            payout = bet_size * (odds / 100)
        else:  # Negative odds
            payout = bet_size / abs(odds) * 100

        # Calculate net profit/loss
        if result == "W":
            net = payout
        elif result == "L":
            net = -bet_size
        else:
            net = 0  # In case of unexpected result value
        
        df.at[index, "net"] = net

    return df


def visualize_net_profit_loss(df):
    """Visualize net profit/loss by sport league."""
    net_by_sport = df.groupby("sport_league")["net"].sum()

    plt.figure(figsize=(10, 6))
    net_by_sport.plot(kind="bar", color=["green" if x > 0 else "red" for x in net_by_sport], alpha=0.8)
    plt.title("Net Profit/Loss by Sport League", fontsize=16)
    plt.xlabel("Sport League", fontsize=12)
    plt.ylabel("Net Profit/Loss", fontsize=12)
    plt.axhline(0, color="black", linewidth=0.8, linestyle="--")
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.xticks(rotation=45)
    plt.show()


def visualize_results(df):
    """Bar chart of wins/losses by sport league."""
    plt.figure(figsize=(10, 6))
    results = df.groupby(["sport_league", "result"]).size().unstack(fill_value=0)
    results.plot(kind="bar", stacked=False, figsize=(10, 6), colormap="viridis")
    
    plt.title("Wins and Losses by Sport League", fontsize=16)
    plt.xlabel("Sport League", fontsize=12)
    plt.ylabel("Count", fontsize=12)
    plt.legend(title="Result")
    plt.xticks(rotation=45)
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.show()


def main():
    """Main function to load data and create visualizations."""
    # Load data
    print("Loading data from the database...")
    df = load_data_from_db()

    if df is not None and not df.empty:
        print(f"Data loaded successfully. Rows: {len(df)}, Columns: {len(df.columns)}")

        # Calculate net profit/loss
        df = calculate_net_profit_loss(df)

        # Generate visualizations
        print("Creating visualizations...")
        visualize_ev_distribution(df)
        visualize_time_to_event(df)
        visualize_bets_by_sport(df)
        visualize_odds_vs_opportunity(df)
        visualize_results(df)
        visualize_net_profit_loss(df)
    else:
        print("No data found in the model_work_table.")


if __name__ == "__main__":
    main()
