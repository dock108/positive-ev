import os
import glob
import logging
import sqlite3
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Paths
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"
MODEL_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/models/"
LOG_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/logs/"
LOG_FILE = os.path.join(LOG_DIR, "win_loss_model.log")

# Ensure directories exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Starting win_loss_model.py")

# Clean up old logs (retain logs for 7 days)
def clean_logs():
    cutoff_date = datetime.now() - timedelta(days=7)
    for log_file in glob.glob(os.path.join(LOG_DIR, "*.log")):
        if datetime.fromtimestamp(os.path.getmtime(log_file)) < cutoff_date:
            os.remove(log_file)
            logging.info(f"Deleted old log file: {log_file}")

clean_logs()

# Load data
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("""
            SELECT ev_percent, final_odds, bet_size, time_to_event, 
                   clv_percent, bet_time_category, win_probability, 
                   (market_implied_prob - win_probability) AS diff_market_vs_model, 
                   result
            FROM model_work_table
        """, conn)
        conn.close()
        logging.info("Data loaded successfully from database.")
        logging.debug(f"Data Sample:\n{df.head()}")
        
        # Convert categorical values to numerical
        df['bet_time_category'] = df['bet_time_category'].map({'Early': 0, 'Mid': 1, 'Late': 2})
        
        # Apply transformations
        df['bet_size'] = np.log1p(df['bet_size'])
        df['time_to_event'] = np.log1p(df['time_to_event'])
        
        # Add interaction features
        df['adjusted_ev_size'] = df['bet_size'] * df['ev_percent']
        df['clv_weighted_bet'] = df['bet_size'] * df['clv_percent']
        
        logging.debug(f"Processed Data Sample:\n{df.head()}")
        logging.info("Feature engineering applied successfully.")
        return df
    except Exception as e:
        logging.error(f"Error loading or processing data: {e}")
        raise

# Train model
def train_model(df):
    features = ['ev_percent', 'final_odds', 'bet_size', 'time_to_event', 'clv_percent', 'bet_time_category', 'diff_market_vs_model', 'adjusted_ev_size', 'clv_weighted_bet']
    X = df[features]
    y = df['result'].map({'W': 1, 'L': 0})
    
    logging.debug(f"Target variable distribution:\n{y.value_counts()}")
    
    if len(y.unique()) < 2:
        logging.error("Only one class found in target variable. Model training will fail.")
        raise ValueError("Target variable contains only one class.")
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, os.path.join(MODEL_DIR, 'scaler.pkl'))  # Save scaler
    
    X_train, X_temp, y_train, y_temp = train_test_split(X_scaled, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
    
    logging.info(f"Training Set Size: {len(X_train)}, Validation Set Size: {len(X_val)}, Test Set Size: {len(X_test)}")
    
    # Train Logistic Regression with L1 Regularization
    logging.info("Training Logistic Regression with L1 Regularization...")
    logistic_model = LogisticRegression(penalty='l1', solver='saga', max_iter=1000, random_state=42, verbose=1)
    logistic_model.fit(X_train, y_train)
    logging.info("Logistic Regression model training complete.")
    
    # Save the logistic regression model
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    logistic_model_path = os.path.join(MODEL_DIR, f'logistic_model_{timestamp}.pkl')
    joblib.dump(logistic_model, logistic_model_path)
    logging.info(f"Logistic Regression model trained and saved: {logistic_model_path}")

    # Evaluate Logistic Regression model
    evaluate_model(logistic_model, X_val, y_val)

    return logistic_model, X_val, y_val

# Evaluate model
def evaluate_model(model, X_val, y_val):
    logging.info("Starting model evaluation...")
    y_pred = model.predict(X_val)
    y_prob = model.predict_proba(X_val)[:, 1]
    accuracy = accuracy_score(y_val, y_pred)
    precision = precision_score(y_val, y_pred)
    recall = recall_score(y_val, y_pred)
    logloss = log_loss(y_val, y_prob)
    
    logging.info(f"Validation Accuracy: {accuracy:.4f}")
    logging.info(f"Precision: {precision:.4f}")
    logging.info(f"Recall: {recall:.4f}")
    logging.info(f"Log Loss: {logloss:.4f}")
    
    print(f"Validation Accuracy: {accuracy:.4f} (Ideally >55% for POC, >60% for real use)")
    print(f"Precision: {precision:.4f} (Should be >0.5 for reliable predictions)")
    print(f"Recall: {recall:.4f} (Higher recall means fewer missed value bets)")
    print(f"Log Loss: {logloss:.4f} (Lower is better, <0.69 is a decent start)")
    logging.info("Model evaluation complete.")

if __name__ == "__main__":
    df = load_data()
    model, X_val, y_val = train_model(df)
    logging.info("Evaluating Logistic Regression model")
    evaluate_model(model, X_val, y_val)
    logging.info("Script execution complete.") 