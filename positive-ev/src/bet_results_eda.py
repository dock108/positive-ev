import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import pytz

# Load data
file_path = "data/oddsjam-bet-tracker.csv"
data = pd.read_csv(file_path)

# Convert datetime columns
data['created_at'] = pd.to_datetime(data['created_at'], errors='coerce')
data['event_start_date'] = pd.to_datetime(data['event_start_date'], errors='coerce')

# Ensure timezone consistency
data['created_at'] = data['created_at'].dt.tz_convert('US/Eastern')
data['event_start_date'] = data['event_start_date'].dt.tz_convert('US/Eastern')

# Filter data to include only the last 3 days
us_eastern = pytz.timezone('US/Eastern')
last_3_days = datetime.now(us_eastern) - timedelta(days=3)
data = data[data['created_at'] >= last_3_days]

# Exclude specific sportsbooks
excluded_sportsbooks = ['Novig', 'Sporttrade', 'Prophet X']
data = data[~data['sportsbook'].isin(excluded_sportsbooks)]

# Compute minutes to event
data['minutes_to_event'] = (data['event_start_date'] - data['created_at']).dt.total_seconds() / 60

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
print("\nBet Value Scale Distribution:")
print(data['bet_value_scale'].value_counts())

# Visualization: Distribution of minutes to event
plt.figure(figsize=(10, 6))
sns.histplot(data['minutes_to_event'], bins=30, kde=True)
plt.title('Distribution of Minutes to Event (Last 3 Days, Excluded Sportsbooks)')
plt.xlabel('Minutes to Event')
plt.ylabel('Frequency')
plt.grid(True)
plt.show()

# Visualization: Average stake by bet value scale
data['stake'] = data['stake'].astype(float)  # Ensure stake is numeric
avg_stake = data.groupby('bet_value_scale')['stake'].mean().reset_index()

plt.figure(figsize=(10, 6))
sns.barplot(x='bet_value_scale', y='stake', data=avg_stake, palette='viridis')
plt.title('Average Stake by Bet Value Scale (Last 3 Days, Excluded Sportsbooks)')
plt.xlabel('Bet Value Scale (1 = 480+ mins, 5 = 20-40 mins)')
plt.ylabel('Average Stake')
plt.grid(True)
plt.show()

# Correlation between minutes to event and stake
corr = data[['minutes_to_event', 'stake']].corr()
print("\nCorrelation between Minutes to Event and Stake:")
print(corr)

# Visualization: Scatter plot of minutes to event vs. stake
plt.figure(figsize=(10, 6))
sns.scatterplot(x='minutes_to_event', y='stake', data=data, alpha=0.7)
plt.title('Stake vs. Minutes to Event (Last 3 Days, Excluded Sportsbooks)')
plt.xlabel('Minutes to Event')
plt.ylabel('Stake')
plt.grid(True)
plt.show()

print("\nEDA Completed.")
