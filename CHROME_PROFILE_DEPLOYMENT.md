# Chrome Profile Deployment Guide

This guide explains the different options for deploying Chrome profiles with the Positive EV application to Vercel.

## Why Chrome Profiles Are Needed

The Positive EV scraper requires a Chrome profile with valid authentication cookies to access the betting data. When deploying to Vercel, there are several ways to handle this requirement.

## Option 1: Automated Deployment Script (Recommended)

The simplest approach is to use our automated deployment script, which handles the Chrome profile export and Vercel deployment in one step:

```bash
# Make the script executable
chmod +x deploy_to_vercel.sh

# Run the deployment script
./deploy_to_vercel.sh
```

This script:
1. Exports your Chrome profile from your local machine
2. Deploys the application to Vercel with the profile included
3. Optionally cleans up temporary files

## Option 2: Remote Chrome Profile

For more advanced deployments, you can store your Chrome profile in a remote location and have it downloaded during function initialization:

### Step 1: Export Your Chrome Profile

```bash
# Export your Chrome profile
python export_chrome_profile.py

# Create a ZIP file of the profile
cd chrome-profile
zip -r ../chrome-profile.zip .
cd ..
```

### Step 2: Upload the ZIP File

Upload the `chrome-profile.zip` file to a secure location that's accessible via HTTP(S), such as:
- Amazon S3
- GitHub (private repository)
- Google Cloud Storage
- Azure Blob Storage
- Any other file hosting service

Make sure to set appropriate access controls so that only your application can access the file.

### Step 3: Set Environment Variables

In your Vercel project settings, add the following environment variable:

```
CHROME_PROFILE_URL=https://your-storage-service.com/path/to/chrome-profile.zip
```

### Step 4: Deploy to Vercel

```bash
vercel --prod
```

### How It Works

When your Vercel function is initialized:
1. The `setup_chrome_profile_vercel.py` script checks for the `CHROME_PROFILE_URL` environment variable
2. If found, it downloads the ZIP file and extracts it to the Chrome profile directory
3. If not found, it falls back to using a local profile (if included in the deployment)

## Option 3: Manual Profile Inclusion

You can manually include the Chrome profile in your deployment:

1. Export your Chrome profile:
   ```bash
   python export_chrome_profile.py
   ```

2. Deploy to Vercel with the profile included:
   ```bash
   vercel --prod
   ```

The `vercel.json` file is already configured to include the `chrome-profile` directory in the deployment:
```json
"includeFiles": [
  "chrome-profile/**"
]
```

## Troubleshooting

### Profile Not Found

If you see an error like "Chrome profile directory does not exist":

1. Check that your Chrome profile was properly exported or downloaded
2. Verify that the `CHROME_PROFILE` environment variable is set correctly
3. Check the Vercel function logs for more details

### Authentication Issues

If the scraper can't access the betting data:

1. Make sure your Chrome profile has valid authentication cookies
2. Try logging in again on your local machine and re-exporting the profile
3. Check if the cookies have expired (they typically last 2-4 weeks)

### Deployment Size Limits

Vercel has deployment size limits. If your Chrome profile is too large:

1. Use the remote profile option to avoid including the profile in the deployment
2. Clean up unnecessary files from your Chrome profile before exporting
3. Consider using a minimal profile with only the essential cookies

## Security Considerations

Chrome profiles may contain sensitive information. To enhance security:

1. Use a dedicated Chrome profile for scraping only
2. Don't include payment information or other sensitive data in the profile
3. Use secure, private storage for remote profiles
4. Regularly rotate credentials and update your profile 