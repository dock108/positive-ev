import os
import sqlite3
import logging
import pandas as pd
import numpy as np

# Paths
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"
LOG_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/logs/"
LOG_FILE = os.path.join(LOG_DIR, "eda_model_work_table.log")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=LOG_FILE, level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("Starting EDA on model_work_table")

# Load data
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM model_work_table", conn)
        conn.close()
        logging.info("Data loaded successfully from database.")
        
        # Convert percentage and dollar values to numeric
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].str.replace('%', '').str.replace('$', '').astype(str)
        
        # Convert result column to numeric for analysis
        if 'result' in df.columns:
            df['result_numeric'] = df['result'].map({'W': 1, 'L': 0})
        
        # Remove redundant columns
        if 'line_movement' in df.columns:
            df.drop(columns=['line_movement'], inplace=True)
            logging.info("Dropped redundant column: line_movement")
        
        if 'market_implied_prob' in df.columns and 'win_probability' in df.columns:
            df.drop(columns=['market_implied_prob'], inplace=True)
            logging.info("Dropped redundant column: market_implied_prob")
        
        # Create categorical bins for time_to_event
        df['bet_time_category'] = pd.cut(
            df['time_to_event'],
            bins=[0, 120, 720, np.inf],  # 2 hours, 12 hours, everything else
            labels=['Short', 'Mid', 'Long']
        )
        logging.info("Created bet_time_category bins")
        
        logging.info("Converted percentage, dollar values, and result to numeric.")
        return df
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        raise

# EDA Functions
def basic_info(df):
    logging.info(f"Dataset shape: {df.shape}")
    logging.info(f"Column names: {df.columns.tolist()}")
    logging.info(f"Missing values:\n{df.isnull().sum()}")
    logging.info(f"Basic statistics:\n{df.describe()}")
    print("Dataset shape:", df.shape)
    print("Column names:", df.columns.tolist())
    print("Missing values:\n", df.isnull().sum())
    print("Basic statistics:\n", df.describe())

# Check class balance
def class_balance(df):
    if 'result' in df.columns:
        balance = df['result'].value_counts(normalize=True)
        logging.info(f"Class balance:\n{balance}")
        print("Class balance:\n", balance)
    else:
        logging.warning("Column 'result' not found in the dataset.")

# Check correlation between numerical features
def correlation_matrix(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if 'result_numeric' in df.columns:
        numeric_cols = list(set(numeric_cols))  # Remove duplicates
    
    corr_matrix = df[numeric_cols].corr()
    logging.info(f"Feature Correlation Matrix:\n{corr_matrix}")
    print("Feature Correlation Matrix:\n", corr_matrix)

# Check feature distributions
def feature_distributions(df):
    logging.info("Feature distributions:")
    for column in df.select_dtypes(include=[np.number]).columns:
        logging.info(f"{column}: mean={df[column].mean()}, std={df[column].std()}, min={df[column].min()}, max={df[column].max()}")
        print(f"{column}: mean={df[column].mean():.4f}, std={df[column].std():.4f}, min={df[column].min()}, max={df[column].max()}")

if __name__ == "__main__":
    df = load_data()
    basic_info(df)
    class_balance(df)
    correlation_matrix(df)
    feature_distributions(df)
    logging.info("EDA script execution complete.")
