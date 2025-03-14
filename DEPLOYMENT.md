# Deployment Guide

This guide explains how to deploy the Positive EV betting data pipeline to Vercel with scheduled daily runs.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Options](#deployment-options)
3. [Chrome Profile Management](#chrome-profile-management)
4. [Monitoring & Maintenance](#monitoring--maintenance)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

1. A Vercel account
2. Vercel CLI installed: `npm install -g vercel`
3. A Chrome profile with necessary login sessions
4. Python 3.8 or higher
5. Bash shell (macOS/Linux) or Git Bash/WSL (Windows)

## Deployment Options

### Option 1: Automated Deployment Script (Recommended)

The simplest approach is to use our automated deployment script:

```bash
# Make the script executable
chmod +x deploy_to_vercel.sh

# Run the deployment script
./deploy_to_vercel.sh
```

The script will:
1. Export your Chrome profile from your local machine
2. Ensure the `.vercelignore` file is properly configured
3. Deploy the application to Vercel
4. Clean up temporary files (optional)

### Option 2: Manual Deployment Steps

If you prefer to perform the steps manually:

1. **Prepare Environment Variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your values:
   - `SUPABASE_URL` and `SUPABASE_KEY`: Your Supabase credentials
   - `CHROME_PROFILE`: Set to `/tmp/chrome-profile` for Vercel
   - Other settings as needed

2. **Export Chrome Profile**
   ```bash
   python export_chrome_profile.py
   ```

3. **Configure .vercelignore**
   ```bash
   # Ensure Chrome profile is not ignored
   echo "!chrome-profile/" >> .vercelignore
   ```

4. **Deploy to Vercel**
   ```bash
   vercel --prod
   ```

## Chrome Profile Management

### Why Chrome Profiles Are Needed

The scraper requires a Chrome profile with valid authentication cookies to access betting data. This profile must be:
- Manually exported from your local machine
- Deployed to Vercel with your application
- Updated when cookies expire

### Important Note on CI/CD Deployments

**CI/CD deployments will NOT include the Chrome profile.** The Chrome profile must be manually deployed from your local machine to Vercel. This is by design to ensure that:
1. Sensitive authentication cookies are only handled by you
2. The profile is only deployed when explicitly needed
3. CI/CD pipelines remain clean and focused on code deployment

### Updating the Chrome Profile

When cookies expire or you need to update the profile:

1. Log in to required websites using your local Chrome profile
2. Run the deployment script:
   ```bash
   ./deploy_to_vercel.sh
   ```

### Initial Setup

#### Local Development Profile

1. Create a dedicated Chrome profile for scraping:
   - Open Chrome
   - Click on your profile icon in the top-right corner
   - Click "Add" to create a new profile
   - Name it "ScraperProfile" (or any name you prefer)
   - Log in to the required websites

2. Set the environment variables in your `.env` file:
   ```
   IS_LOCAL=1
   CHROME_PROFILE=~/Library/Application Support/Google/Chrome/ScraperProfile
   ```

#### Vercel Deployment Profile

1. Ensure you have a working local Chrome profile
2. The deployment script will automatically:
   - Export your profile using `export_chrome_profile.py`
   - Create a `chrome-profile` directory in the project root
   - Include this directory in the Vercel deployment

## Monitoring & Maintenance

### Scheduled Runs

The pipeline is configured to run once per day at midnight UTC. This schedule is defined in `vercel.json`:

```json
{
  "crons": [
    {
      "path": "/api/run",
      "schedule": "0 0 * * *"
    }
  ]
}
```

### Manual Runs

You can trigger the pipeline manually by visiting:
```
https://your-vercel-app.vercel.app/api/run
```

### Monitoring Tools

1. **Vercel Dashboard**
   - View function execution logs
   - Monitor cron job runs
   - Check error rates and performance

2. **Application Logs**
   - Pipeline execution status
   - Scraping results
   - Grading calculations

## Troubleshooting

### Common Issues

1. **Chrome Profile Issues**
   - Verify profile exists and has valid cookies
   - Check Vercel function logs
   - Try re-deploying with updated profile

2. **Pipeline Failures**
   - Check Vercel function logs
   - Verify Supabase connection
   - Check Chrome profile status

3. **Deployment Issues**
   - Verify Chrome profile was exported correctly
   - Check `.vercelignore` configuration
   - Review deployment logs

### Getting Help

1. Check the error message in the API response
2. Review Vercel function logs
3. Check Chrome profile status
4. Verify environment variables 