# Vercel Deployment Guide

This guide explains how to deploy the Positive EV betting data pipeline to Vercel with scheduled runs every 5 minutes.

## Prerequisites

1. A Vercel account
2. The Vercel CLI installed (`npm i -g vercel`)
3. A Chrome profile with any necessary login sessions

## Deployment Steps

### 1. Prepare Your Environment Variables

Copy the `.env.example` file to a new `.env` file and fill in your actual values:

```bash
cp .env.example .env
```

Edit the `.env` file with your actual values:
- `SUPABASE_URL` and `SUPABASE_KEY`: Your Supabase credentials
- `CHROME_PROFILE`: Set to `/tmp/chrome-profile` for Vercel
- `SOURCE_CHROME_PROFILE`: Path to your local Chrome profile with login sessions

### 2. Export Your Chrome Profile

To use your existing Chrome profile on Vercel, you need to export the essential files:

1. Locate your Chrome profile directory (typically in `~/.config/google-chrome/Default` on Linux, `~/Library/Application Support/Google/Chrome/Default` on macOS, or `%LOCALAPPDATA%\Google\Chrome\User Data\Default` on Windows)

2. Create a ZIP file of the essential profile files:
   ```bash
   cd /path/to/your/chrome/profile
   zip -r chrome-profile.zip Cookies Preferences Login\ Data Web\ Data Bookmarks History Favicons Shortcuts "Local Storage"
   ```

3. Upload this ZIP file to a secure location (e.g., a private S3 bucket)

4. In your Vercel deployment, you'll need to download and extract this ZIP file to the `/tmp/chrome-profile` directory during initialization

### 3. Set Up Vercel Environment Variables

When deploying to Vercel, you'll need to set up the following environment variables:

1. Log in to your Vercel dashboard
2. Go to your project settings
3. Navigate to the "Environment Variables" section
4. Add all the variables from your `.env` file
5. Add an additional variable `CHROME_PROFILE_URL` pointing to your uploaded Chrome profile ZIP file

### 4. Deploy to Vercel

Deploy your project to Vercel using the CLI:

```bash
vercel
```

Follow the prompts to link your project to your Vercel account.

### 5. Enable Cron Jobs

Vercel Cron Jobs are available on paid plans. To enable the cron job:

1. Go to your project settings in the Vercel dashboard
2. Navigate to the "Cron Jobs" section
3. Verify that the cron job is set up to run every 5 minutes (`*/5 * * * *`)
4. Enable the cron job

## How It Works

1. The cron job triggers the `/api/run_pipeline` endpoint every 5 minutes
2. The API handler:
   - Sets up the Chrome profile by downloading and extracting your profile ZIP
   - Runs the scraper to collect new betting data
   - Runs the grade calculator to grade new bets
   - Returns a JSON response with the results

## Troubleshooting

### Chrome Profile Issues

If you encounter issues with the Chrome profile:

1. Check the logs in the Vercel dashboard
2. Verify that your Chrome profile ZIP file is accessible
3. Try running with a fresh profile by setting `SOURCE_CHROME_PROFILE` to an empty string

### Cron Job Not Running

If the cron job isn't running:

1. Verify that you're on a paid Vercel plan
2. Check the cron job logs in the Vercel dashboard
3. Try manually triggering the API endpoint to verify it works

### Selenium Issues on Vercel

Vercel's serverless environment has limitations for running browser automation. If you encounter issues:

1. Consider using a headless browser configuration
2. Increase the function timeout in your Vercel settings
3. For more complex scraping needs, consider using a dedicated server instead of Vercel

## Monitoring

Monitor your deployment through:

1. Vercel dashboard logs
2. Function invocation metrics
3. Cron job execution history

## Limitations

Be aware of Vercel's serverless limitations:

1. Function execution timeout (default is 10 seconds, can be increased)
2. Memory limitations (1GB on the Pro plan)
3. Ephemeral filesystem (files written to disk are temporary)
4. Cold starts may affect performance 