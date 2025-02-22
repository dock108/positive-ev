#!/usr/bin/env python3
import os
import sys
from crontab import CronTab

def setup_cron():
    """Set up cron job to run bet evaluation at 2 AM daily."""
    try:
        # Get the absolute path to the eval_bets.py script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        eval_script = os.path.join(script_dir, 'eval_bets.py')
        python_path = sys.executable
        
        # Create a new cron tab for the current user
        cron = CronTab(user=True)
        
        # Remove any existing bet evaluation jobs
        cron.remove_all(comment='bet_evaluation')
        
        # Create new job
        job = cron.new(
            command=f'{python_path} {eval_script}',
            comment='bet_evaluation'
        )
        
        # Set schedule for 2 AM daily
        job.hour.on(2)
        job.minute.on(0)
        
        # Write the changes
        cron.write()
        
        print("Successfully set up cron job for daily bet evaluation at 2 AM")
        return True
        
    except Exception as e:
        print(f"Error setting up cron job: {str(e)}")
        return False

if __name__ == "__main__":
    setup_cron() 