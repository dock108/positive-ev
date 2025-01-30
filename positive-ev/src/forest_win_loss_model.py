import sqlite3
import pandas as pd
import numpy as np
import os
import logging
import glob
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, log_loss
import joblib

# Paths
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"
MODEL_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/models/"
LOG_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/logs/"
LOG_FILE = os.path.join(LOG_DIR, "forest_win_loss_model.log")

# Ensure directories exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Starting forest_win_loss_model.py")

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
        
        df['bet_time_category'] = df['bet_time_category'].map({'Early': 0, 'Mid': 1, 'Late': 2})
        df['bet_size'] = np.log1p(df['bet_size'])
        df['time_to_event'] = np.log1p(df['time_to_event'])
        df['adjusted_ev_size'] = df['bet_size'] * df['ev_percent']
        df['clv_weighted_bet'] = df['bet_size'] * df['clv_percent']
        
        logging.info("Feature engineering applied successfully.")
        return df
    except Exception as e:
        logging.error(f"Error loading or processing data: {e}")
        raise

# Train model with Grid Search
def train_model(df):
    features = ['ev_percent', 'final_odds', 'bet_size', 'time_to_event', 'clv_percent', 'bet_time_category', 'diff_market_vs_model', 'adjusted_ev_size', 'clv_weighted_bet']
    X = df[features]
    y = df['result'].map({'W': 1, 'L': 0})
    
    if len(y.unique()) < 2:
        logging.error("Only one class found in target variable. Model training will fail.")
        raise ValueError("Target variable contains only one class.")
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, os.path.join(MODEL_DIR, 'scaler.pkl'))
    
    X_train, X_temp, y_train, y_temp = train_test_split(X_scaled, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
    
    logging.info(f"Training Set Size: {len(X_train)}, Validation Set Size: {len(X_val)}, Test Set Size: {len(X_test)}")
    
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [None, 10, 20],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'class_weight': [None, 'balanced']
    }
    
    grid_search = GridSearchCV(RandomForestClassifier(random_state=42), param_grid, cv=5, scoring='accuracy', verbose=1)
    grid_search.fit(X_train, y_train)
    best_params = grid_search.best_params_
    logging.info(f"Best parameters found: {best_params}")
    
    model = RandomForestClassifier(**best_params, random_state=42)
    model.fit(X_train, y_train)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    model_path = os.path.join(MODEL_DIR, f'random_forest_{timestamp}.pkl')
    latest_model_path = os.path.join(MODEL_DIR, 'random_forest_latest.pkl')
    joblib.dump(model, model_path)
    joblib.dump(model, latest_model_path)
    
    logging.info(f"Random Forest model trained and saved: {model_path}")
    return model, X_val, y_val

# Evaluate model
def evaluate_model(model, X_val, y_val):
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

if __name__ == "__main__":
    df = load_data()
    model, X_val, y_val = train_model(df)
    evaluate_model(model, X_val, y_val)
    logging.info("Script execution complete.")
