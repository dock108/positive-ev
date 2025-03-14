# Chrome Profile Setup Guide

This guide explains how to set up and manage Chrome profiles for the Positive EV scraper, both for local development and for deployment to Vercel.

## Overview

The scraper requires a Chrome profile with valid authentication cookies to access the betting data. There are two main scenarios:

1. **Local Development**: Uses your local Chrome profile directly
2. **Vercel Deployment**: Requires exporting the profile and including it in the deployment

## Local Development Setup

For local development, the scraper can use a Chrome profile directly from your machine:

1. Create a dedicated Chrome profile for scraping:
   - Open Chrome
   - Click on your profile icon in the top-right corner
   - Click "Add" to create a new profile
   - Name it "ScraperProfile" (or any name you prefer)
   - Log in to the required websites

2. Set the environment variable in your `.env` file:
   ```
   IS_LOCAL=1
   ```

3. If you named your profile something other than "ScraperProfile", specify the path:
   ```
   CHROME_PROFILE=~/Library/Application Support/Google/Chrome/YourProfileName
   ```

## Vercel Deployment Setup

For deployment to Vercel, you need to export your Chrome profile and include it in the deployment:

1. Ensure you have a working Chrome profile on your local machine

2. Run the export script to copy the essential files to the project root:
   ```bash
   python export_chrome_profile.py
   ```

3. This will create a `chrome-profile` directory in your project root with the necessary files

4. The `vercel.json` file is already configured to include this directory in the deployment:
   ```json
   "includeFiles": [
     "chrome-profile/**"
   ]
   ```

5. Deploy to Vercel:
   ```bash
   vercel --prod
   ```

## Troubleshooting

If you encounter issues with the Chrome profile:

1. **Profile not found**: Ensure the profile exists at the expected location
   - For local development: `~/Library/Application Support/Google/Chrome/ScraperProfile`
   - For Vercel: `./chrome-profile` in the project root

2. **Missing cookies or authentication**: Make sure you're logged in to the required websites in the Chrome profile

3. **Deployment issues**: Check the Vercel logs to ensure the profile is being included in the deployment

4. **Permission issues**: Ensure the Chrome profile files have the correct permissions

## Maintenance

Chrome profiles may need periodic updates as cookies expire. To update:

1. Log in again using your local Chrome profile
2. Re-run the export script:
   ```bash
   python export_chrome_profile.py
   ```
3. Re-deploy to Vercel

## Script Reference

### export_chrome_profile.py

This script exports your local Chrome profile to the project root for deployment:

```bash
# Export from the default location
python export_chrome_profile.py

# Export from a custom location
python export_chrome_profile.py "/path/to/your/profile"
```

### setup_chrome_profile.py

This script verifies the Chrome profile during runtime:

- Checks if the profile directory exists
- Verifies essential files are present
- Creates a "First Run" file to skip Chrome's first-run experience 