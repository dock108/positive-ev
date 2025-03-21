"""
Comparison script for analyzing betting grades using both old and new Bayesian methods.
This script fetches the last 100 records and grades them using both methods for comparison.
"""

import os
import sys
from tabulate import tabulate

# Add the project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.grade_calculator import (
    calculate_bet_grade,
    get_supabase_client
)

def get_last_100_bets():
    """Get the last 100 unique bets from the betting_data table."""
    supabase = get_supabase_client()
    
    try:
        # Get the last 100 records ordered by timestamp
        response = supabase.table("betting_data").select("*").order("timestamp", desc=True).limit(100).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching bets: {e}")
        return []

def analyze_grades(bets):
    """Analyze each bet using both grading methods."""
    results = []
    
    for bet in bets:
        bet_id = bet.get('bet_id')
        
        # Calculate grades using both methods
        old_grade = calculate_bet_grade(bet, use_new_bayesian=False)
        new_grade = calculate_bet_grade(bet, use_new_bayesian=True)
        
        if old_grade and new_grade:  # Only include if both calculations succeeded
            result = {
                'bet_id': bet_id,
                'timestamp': bet.get('timestamp'),
                'ev_percent': bet.get('ev_percent'),
                'old_grade': old_grade.get('grade'),
                'old_score': old_grade.get('composite_score'),
                'new_grade': new_grade.get('grade'),
                'new_score': new_grade.get('composite_score'),
                'old_bayesian': old_grade.get('bayesian_confidence'),
                'new_bayesian': new_grade.get('bayesian_confidence'),
                'difference': (new_grade.get('composite_score', 0) - old_grade.get('composite_score', 0))
            }
            results.append(result)
    
    return results

def print_comparison(results):
    """Print formatted comparison of grading methods."""
    if not results:
        print("No results to compare")
        return
        
    # Prepare table data
    table_data = []
    grade_changes = 0
    significant_changes = 0  # Changes > 5 points
    
    for r in results:
        table_data.append([
            r['bet_id'][:8] + '...',  # Truncate bet_id for display
            r['ev_percent'],
            f"{r['old_grade']} ({r['old_score']:.1f})",
            f"{r['new_grade']} ({r['new_score']:.1f})",
            f"{r['difference']:+.1f}",
            f"{r['old_bayesian']:.1f}",
            f"{r['new_bayesian']:.1f}"
        ])
        
        if r['old_grade'] != r['new_grade']:
            grade_changes += 1
        if abs(r['difference']) > 5:
            significant_changes += 1
    
    # Print summary statistics
    print("\n=== Grade Comparison Summary ===")
    print(f"Total bets analyzed: {len(results)}")
    print(f"Grade changes: {grade_changes} ({(grade_changes/len(results))*100:.1f}%)")
    print(f"Significant changes (>5 points): {significant_changes} ({(significant_changes/len(results))*100:.1f}%)")
    print(f"Average absolute change: {sum(abs(r['difference']) for r in results)/len(results):.2f} points")
    
    # Print detailed comparison table
    print("\n=== Detailed Comparison ===")
    headers = ['Bet ID', 'EV%', 'Old Grade', 'New Grade', 'Diff', 'Old Bayes', 'New Bayes']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    # Print distribution of changes
    changes = [r['difference'] for r in results]
    print("\n=== Change Distribution ===")
    print(f"Max increase: {max(changes):+.1f} points")
    print(f"Max decrease: {min(changes):+.1f} points")
    print(f"Median change: {sorted(changes)[len(changes)//2]:+.1f} points")

def main():
    """Main function to run comparison analysis."""
    print("Fetching last 100 bets...")
    bets = get_last_100_bets()
    
    if not bets:
        print("No bets found to analyze")
        return
        
    print(f"Analyzing {len(bets)} bets...")
    results = analyze_grades(bets)
    print_comparison(results)

if __name__ == "__main__":
    main() 