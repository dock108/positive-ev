import os
import glob
import logging
import sqlite3
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, LassoCV
from sklearn.model_selection import train_test_split, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# Paths
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"
MODEL_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/models"
OUTPUT_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/analysis/model_analysis"
LOG_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/logs/"
LOG_FILE = os.path.join(LOG_DIR, "win_loss_model.log")

# Ensure directories exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Starting win_loss_model.py")

def clean_logs():
    """Clean up logs older than 7 days."""
    cutoff_date = datetime.now() - timedelta(days=7)
    for log_file in glob.glob(os.path.join(LOG_DIR, "*.log")):
        if datetime.fromtimestamp(os.path.getmtime(log_file)) < cutoff_date:
            os.remove(log_file)
            logging.info(f"Deleted old log file: {log_file}")

def load_data():
    """Load and prepare data for modeling."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT *
    FROM model_work_table
    WHERE result IN ('W', 'L')
    ORDER BY event_time
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def prepare_features(df):
    """Enhanced feature preparation with interaction terms and transformations."""
    # Convert categorical variables
    df['result_binary'] = (df['result'] == 'W').astype(int)
    df['bet_time_encoded'] = pd.Categorical(df['bet_time_category']).codes
    
    # Basic features with potential
    base_features = [
        'ev_percent', 'time_to_event', 'bet_time_encoded',
        'line_movement', 'clv_percent', 'market_implied_prob'
    ]
    
    # Create interaction terms
    df['ev_by_time'] = df['ev_percent'] * df['time_to_event']
    df['clv_by_ev'] = df['clv_percent'] * df['ev_percent']
    
    # Add non-linear transformations
    df['ev_squared'] = df['ev_percent'] ** 2
    df['time_log'] = np.log1p(df['time_to_event'])
    
    # Add momentum features
    df['line_movement_direction'] = np.sign(df['line_movement'])
    df['large_line_move'] = (abs(df['line_movement']) > df['line_movement'].std()).astype(int)
    
    # Add more complex interactions
    df['ev_by_clv_by_time'] = df['ev_percent'] * df['clv_percent'] * df['time_to_event']
    df['market_prob_by_ev'] = df['market_implied_prob'] * df['ev_percent']
    
    # Add rolling averages if timestamps available
    if 'event_time' in df.columns:
        df = df.sort_values('event_time')
        df['rolling_win_rate'] = df['result_binary'].rolling(10, min_periods=1).mean()
        df['rolling_ev'] = df['ev_percent'].rolling(10, min_periods=1).mean()
    
    # Combine all features
    feature_cols = base_features + [
        'ev_by_time', 'clv_by_ev', 'ev_squared', 'time_log',
        'line_movement_direction', 'large_line_move',
        'ev_by_clv_by_time', 'market_prob_by_ev',
        'rolling_win_rate', 'rolling_ev'
    ]
    
    # Add player stat columns if they exist
    stat_cols = [col for col in df.columns if any(x in col for x in [
        '_avg', '_std', '_trend', '_consistency', 'health_score'])]
    feature_cols.extend(stat_cols)
    
    # Remove any null values
    df = df.dropna(subset=feature_cols + ['result_binary'])
    
    return df[feature_cols], df['result_binary'], feature_cols

def select_best_features(X, y, feature_names):
    """Use LASSO path to select most stable features."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Fit LassoCV with less aggressive regularization
    lasso = LassoCV(cv=5, random_state=42, eps=1e-4, n_alphas=100)
    lasso.fit(X_scaled, y)
    
    # Get selected features with a more lenient threshold
    selected_features = []
    for idx, (name, coef) in enumerate(zip(feature_names, lasso.coef_)):
        if abs(coef) > 0.0001:  # Reduced threshold
            selected_features.append((name, coef))
    
    # Sort by absolute coefficient value
    selected_features.sort(key=lambda x: abs(x[1]), reverse=True)
    
    print("\nSelected Features:")
    for name, coef in selected_features:
        print(f"{name}: {coef:.4f}")
    
    return [f[0] for f in selected_features]

def train_model_with_cv(X, y, feature_names):
    """Train with cross-validation to better assess model stability."""
    print("\nPerforming Cross-Validation...")
    
    # Convert to numpy arrays for CV
    X_array = X.values if isinstance(X, pd.DataFrame) else X
    y_array = y.values if isinstance(y, pd.Series) else y
    
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = []
    cv_high_conf_scores = []
    feature_importances = np.zeros(X_array.shape[1])
    
    for fold, (train_idx, val_idx) in enumerate(kf.split(X_array)):
        X_train, X_val = X_array[train_idx], X_array[val_idx]
        y_train, y_val = y_array[train_idx], y_array[val_idx]
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        
        model = LogisticRegression(penalty='l1', solver='saga', max_iter=1000)
        model.fit(X_train_scaled, y_train)
        
        y_val_pred = model.predict(X_val_scaled)
        y_val_proba = model.predict_proba(X_val_scaled)
        
        # Basic accuracy
        fold_acc = (y_val_pred == y_val).mean()
        
        # High confidence accuracy
        high_conf = y_val_proba.max(axis=1) > 0.6
        if high_conf.any():
            high_conf_acc = (y_val[high_conf] == y_val_pred[high_conf]).mean()
            cv_high_conf_scores.append(high_conf_acc)
        
        cv_scores.append(fold_acc)
        feature_importances += abs(model.coef_[0])
        print(f"Fold {fold+1} Accuracy: {fold_acc:.2%}")
    
    # Average feature importances across folds
    feature_importances /= 5
    
    print(f"\nCross-validation accuracy: {np.mean(cv_scores):.2%} ± {np.std(cv_scores):.2%}")
    if cv_high_conf_scores:
        print(f"High confidence accuracy: {np.mean(cv_high_conf_scores):.2%} ± {np.std(cv_high_conf_scores):.2%}")
    
    return np.mean(cv_scores), feature_importances

def train_final_model(X, y):
    """Train the final model on all data."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = LogisticRegression(penalty='l1', solver='saga', max_iter=1000)
    model.fit(X_scaled, y)
    
    y_pred = model.predict(X_scaled)
    y_pred_proba = model.predict_proba(X_scaled)
    
    return model, scaler, y_pred, y_pred_proba

def analyze_coefficients(model, feature_names):
    """Analyze and visualize logistic regression coefficients."""
    coefficients = model.coef_[0]
    coef_df = pd.DataFrame({
        'Feature': feature_names,
        'Coefficient': coefficients
    })
    coef_df = coef_df.sort_values('Coefficient', key=abs, ascending=False)
    
    plt.figure(figsize=(12, 8))
    plt.title("Feature Coefficients (Absolute Impact)")
    plt.barh(range(len(coefficients)), abs(coef_df['Coefficient']))
    plt.yticks(range(len(coefficients)), coef_df['Feature'])
    plt.xlabel('Absolute Coefficient Value')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/feature_coefficients.png")
    plt.close()
    
    # Save coefficients to text file
    with open(f"{OUTPUT_DIR}/feature_coefficients.txt", 'w') as f:
        f.write("Feature Coefficients (sorted by absolute impact):\n")
        for _, row in coef_df.iterrows():
            f.write(f"{row['Feature']}: {row['Coefficient']:.4f}\n")

def analyze_predictions(y_test, y_pred):
    """Analyze prediction performance."""
    # Generate confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig(f"{OUTPUT_DIR}/confusion_matrix.png")
    plt.close()
    
    # Save classification report
    report = classification_report(y_test, y_pred)
    with open(f"{OUTPUT_DIR}/classification_report.txt", 'w') as f:
        f.write("Classification Report:\n")
        f.write(report)

def save_model(model, scaler, feature_names):
    """Save the model and associated artifacts."""
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    model_path = os.path.join(MODEL_DIR, f"logistic_model_{timestamp}.joblib")
    scaler_path = os.path.join(MODEL_DIR, f"scaler_{timestamp}.joblib")
    
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    
    # Save feature names
    with open(os.path.join(MODEL_DIR, f"feature_names_{timestamp}.txt"), 'w') as f:
        f.write("\n".join(feature_names))
    
    print(f"Model saved to {model_path}")

def evaluate_model_viability(y_true, y_pred, y_pred_proba, cv_accuracy):
    """Enhanced model viability evaluation."""
    print("\n=== Model Viability Analysis ===")
    
    # Calculate metrics
    accuracy = (y_true == y_pred).mean()
    win_rate = y_pred.mean()
    
    # Calculate ROI assuming equal bet sizes
    true_wins = (y_true == 1).sum()
    true_win_rate = true_wins / len(y_true)
    
    print("\nKey Metrics:")
    print(f"Accuracy: {accuracy:.2%} (Target: >52%)")
    print(f"Cross-Validation Accuracy: {cv_accuracy:.2%}")
    print(f"True Win Rate: {true_win_rate:.2%}")
    print(f"Predicted Win Rate: {win_rate:.2%}")
    
    # Try different confidence thresholds
    thresholds = [0.55, 0.60, 0.65]
    print("\nConfidence Threshold Analysis:")
    for threshold in thresholds:
        high_conf_mask = (y_pred_proba.max(axis=1) > threshold)
        if high_conf_mask.any():
            high_conf_acc = (y_true[high_conf_mask] == y_pred[high_conf_mask]).mean()
            print(f"\nPredictions with >{threshold*100:.0f}% confidence:")
            print(f"Count: {high_conf_mask.sum()} ({high_conf_mask.mean():.1%} of all predictions)")
            print(f"Accuracy: {high_conf_acc:.2%}")
    
    # Use 0.55 threshold for viability check
    high_conf_mask = (y_pred_proba.max(axis=1) > 0.55)
    high_conf_acc = (y_true[high_conf_mask] == y_pred[high_conf_mask]).mean() if high_conf_mask.any() else 0
    
    # Viability checks
    print("\nViability Checks:")
    checks = [
        (accuracy > 0.52, "Base Accuracy > 52%"),
        (cv_accuracy > 0.52, "CV Accuracy > 52%"),
        (high_conf_mask.any() and high_conf_acc > 0.55, "High Confidence Accuracy > 55%"),
        (high_conf_mask.mean() > 0.1, "At least 10% high confidence predictions"),
    ]
    
    num_passed = sum(check[0] for check in checks)
    print(f"\nPassed {num_passed}/{len(checks)} viability checks:")
    for check_passed, description in checks:
        print(f"{'✓' if check_passed else '✗'} {description}")
    
    # Consider viable if passes at least 2 checks
    is_viable = num_passed >= 2
    
    # Add summary of why it's viable/not viable
    if is_viable:
        print(f"\nModel passed {num_passed} out of {len(checks)} checks - VIABLE")
    else:
        print(f"\nModel only passed {num_passed} out of {len(checks)} checks - NOT VIABLE")
    
    return is_viable

def main():
    clean_logs()
    
    print("\nLoading data...")
    df = load_data()
    print(f"Total samples: {len(df)}")
    print(f"Win rate in data: {(df['result'] == 'W').mean():.2%}")
    
    print("\nPreparing features...")
    X, y, feature_names = prepare_features(df)
    print(f"Initial features: {len(feature_names)}")
    
    print("\nSelecting best features...")
    selected_features = select_best_features(X, y, feature_names)
    X = X[selected_features]
    print(f"Selected features: {len(selected_features)}")
    
    print("\nTraining model with cross-validation...")
    cv_accuracy, feature_importances = train_model_with_cv(X, y, selected_features)
    
    print("\nTraining final model...")
    model, scaler, y_pred, y_pred_proba = train_final_model(X, y)
    
    # Evaluate model viability
    is_viable = evaluate_model_viability(y, y_pred, y_pred_proba, cv_accuracy)
    
    print("\nAnalyzing results...")
    analyze_coefficients(model, selected_features)
    analyze_predictions(y, y_pred)
    
    print("\nSaving model...")
    save_model(model, scaler, selected_features)
    
    print(f"\nModel {'IS' if is_viable else 'IS NOT'} considered viable for POC")
    print("\nModel training and analysis complete. Check the output directory for detailed results.")

if __name__ == "__main__":
    main()
