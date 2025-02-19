import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import pytz

# Ensure the EDA output folder exists
eda_folder = "eda"
os.makedirs(eda_folder, exist_ok=True)

# Load data
file_path = "data/oddsjam-bet-tracker.csv"
data = pd.read_csv(file_path)

# Update datetime handling
data['created_at'] = pd.to_datetime(data['created_at'], errors='coerce')
data['event_time'] = pd.to_datetime(data['event_time'], format='%Y-%m-%d %H:%M', errors='coerce')

# Ensure timezone consistency (if needed)
data['created_at'] = data['created_at'].dt.tz_convert('US/Eastern')
# Note: event_time is already in a standard format, no timezone conversion needed

# Filter data to include only the last 3 days
us_eastern = pytz.timezone('US/Eastern')
last_3_days = datetime.now(us_eastern) - timedelta(days=3)
data = data[data['created_at'] >= last_3_days]

# Exclude specific sportsbooks
excluded_sportsbooks = ['Novig', 'Sporttrade', 'Prophet X']
data = data[~data['sportsbook'].isin(excluded_sportsbooks)]

# Compute minutes to event
data['minutes_to_event'] = (data['event_time'] - data['created_at']).dt.total_seconds() / 60

# Create a bell curve value scale based on minutes to event
def assign_bet_value(minutes):
    if minutes < 0:
        return None  # Invalid case
    elif 20 <= minutes <= 40:
        return 5  # Peak value range
    elif 40 < minutes <= 120:
        return 4  # Secondary range
    elif 0 <= minutes < 20:
        return 3  # Pre-peak range
    elif 120 < minutes <= 480:
        return 2  # Near baseline
    else:
        return 1  # Baseline (480+ mins)

data['bet_value_scale'] = data['minutes_to_event'].apply(assign_bet_value)

# Summary statistics by bet value scale
bet_value_dist = data['bet_value_scale'].value_counts()
print("\nBet Value Scale Distribution:")
print(bet_value_dist)

# Save the bet value scale distribution to a CSV file
bet_value_dist.to_csv(os.path.join(eda_folder, "bet_value_scale_distribution.csv"))

# Visualization: Distribution of minutes to event
plt.figure(figsize=(10, 6))
sns.histplot(data['minutes_to_event'], bins=30, kde=True)
plt.title('Distribution of Minutes to Event (Last 3 Days, Excluded Sportsbooks)')
plt.xlabel('Minutes to Event')
plt.ylabel('Frequency')
plt.grid(True)
plt.savefig(os.path.join(eda_folder, "minutes_to_event_distribution.png"))
plt.close()

# Visualization: Average stake by bet value scale
data['stake'] = data['stake'].astype(float)  # Ensure stake is numeric
avg_stake = data.groupby('bet_value_scale')['stake'].mean().reset_index()

plt.figure(figsize=(10, 6))
sns.barplot(x='bet_value_scale', y='stake', data=avg_stake, palette='viridis')
plt.title('Average Stake by Bet Value Scale (Last 3 Days, Excluded Sportsbooks)')
plt.xlabel('Bet Value Scale (1 = 480+ mins, 5 = 20-40 mins)')
plt.ylabel('Average Stake')
plt.grid(True)
plt.savefig(os.path.join(eda_folder, "average_stake_by_value_scale.png"))
plt.close()

# Correlation between minutes to event and stake
corr = data[['minutes_to_event', 'stake']].corr()
print("\nCorrelation between Minutes to Event and Stake:")
print(corr)

# Save correlation matrix to a CSV file
corr.to_csv(os.path.join(eda_folder, "correlation_minutes_to_event_stake.csv"))

# Visualization: Scatter plot of minutes to event vs. stake
plt.figure(figsize=(10, 6))
sns.scatterplot(x='minutes_to_event', y='stake', data=data, alpha=0.7)
plt.title('Stake vs. Minutes to Event (Last 3 Days, Excluded Sportsbooks)')
plt.xlabel('Minutes to Event')
plt.ylabel('Stake')
plt.grid(True)
plt.savefig(os.path.join(eda_folder, "stake_vs_minutes_to_event.png"))
plt.close()

# Save the filtered data for reference
data.to_csv(os.path.join(eda_folder, "filtered_betting_data.csv"), index=False)

print("\nEDA Completed. All outputs saved to the 'eda/' folder.")
