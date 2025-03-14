# Deployment Guide

This guide explains how to deploy the Positive EV betting data pipeline on a Raspberry Pi with scheduled runs.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Chrome Setup](#chrome-setup)
4. [Environment Configuration](#environment-configuration)
5. [Scheduling](#scheduling)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

1. Raspberry Pi (3B+ or newer recommended)
2. Python 3.8 or higher
3. Chrome browser
4. Supabase account and credentials
5. Internet connection

## Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/positive-ev.git
   cd positive-ev
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create required directories:
   ```bash
   mkdir -p logs backups
   ```

## Chrome Setup

1. Install Chrome on Raspberry Pi:
   ```bash
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_arm64.deb
   sudo dpkg -i google-chrome-stable_current_arm64.deb
   sudo apt-get install -f
   ```

2. Create a Chrome profile for the scraper:
   - Open Chrome
   - Go to chrome://version
   - Note the "Profile Path"
   - Create a new profile named "ScraperProfile"

3. Configure Chrome for headless operation:
   ```bash
   mkdir -p ~/.config/chromium/ScraperProfile
   ```

## Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   - `SUPABASE_URL` and `SUPABASE_KEY`: Your Supabase credentials
   - `CHROME_PROFILE`: Set to "ScraperProfile"
   - Other variables can be left as default

## Scheduling

1. Open crontab:
   ```bash
   crontab -e
   ```

2. Add the following line to run every 5 minutes:
   ```bash
   */5 * * * * cd /home/pi/positive-ev && PYTHONPATH=/home/pi/positive-ev python3 src/scraper.py && PYTHONPATH=/home/pi/positive-ev python3 src/grade_calculator.py
   ```

## Monitoring & Maintenance

1. Check logs:
   ```bash
   tail -f logs/scraper.log
   ```

2. Monitor backups:
   ```bash
   ls -l backups/
   ```

3. Check system resources:
   ```bash
   top
   ```

## Troubleshooting

1. If Chrome fails to start:
   - Check Chrome installation: `google-chrome --version`
   - Verify profile path in logs
   - Try running with `--no-sandbox` flag

2. If scraper fails:
   - Check logs for specific errors
   - Verify internet connection
   - Check Supabase credentials

3. If cron job isn't running:
   - Check cron logs: `grep CRON /var/log/syslog`
   - Verify cron service: `sudo service cron status`
   - Test cron job manually 