# Positive EV

A betting analytics platform that scrapes positive EV betting opportunities and calculates bet grades.

## Deployment to Vercel

This project is configured for deployment to Vercel with automated cron jobs for scraping and grading.

### Prerequisites

1. A Vercel account
2. Vercel CLI installed: `npm install -g vercel`
3. A GitHub account (for automated deployments)

### Deployment Methods

#### Option 1: Automated Deployment Script (Recommended)

We now provide an automated deployment script that handles the Chrome profile export and Vercel deployment in one step:

```bash
# Make the script executable
chmod +x deploy_to_vercel.sh

# Run the deployment script
./deploy_to_vercel.sh
```

The script will:
1. Export your Chrome profile from your local machine
2. Deploy the application to Vercel
3. Clean up temporary files (optional)

#### Option 2: Remote Chrome Profile (Advanced)

For more advanced deployments, you can store your Chrome profile in a remote location (e.g., S3, GitHub, etc.) and have it downloaded during function initialization:

1. Export your Chrome profile to a ZIP file:
   ```bash
   python export_chrome_profile.py
   cd chrome-profile
   zip -r ../chrome-profile.zip .
   ```

2. Upload the ZIP file to a secure location (e.g., S3, GitHub, etc.)

3. Set the `CHROME_PROFILE_URL` environment variable in your Vercel project to point to the ZIP file URL

4. Deploy to Vercel:
   ```bash
   vercel --prod
   ```

The application will automatically download and set up the Chrome profile during initialization.

#### Option 3: GitHub Actions (CI/CD)

This project uses GitHub Actions to automatically deploy to Vercel whenever changes are pushed to:
- `main` branch → Production environment
- `staging` branch → Preview/Staging environment

For setup instructions, see [GitHub Actions Setup Guide](./docs/GITHUB_ACTIONS_SETUP.md).

#### Option 4: Manual Deployment

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/positive-ev.git
cd positive-ev
```

2. **Set up environment variables**

Create a `.env` file based on the example:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SOURCE_CHROME_PROFILE=/path/to/local/chrome/profile
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up Chrome profile**

If you want to use an existing Chrome profile (recommended for maintaining session cookies):

```bash
# Set the SOURCE_CHROME_PROFILE environment variable
export SOURCE_CHROME_PROFILE=/path/to/your/chrome/profile

# Run the setup script
python src/setup_chrome_profile.py
```

5. **Login to Vercel**

```bash
vercel login
```

6. **Deploy to Vercel**

```bash
# For development/staging deployment
vercel

# For production deployment
vercel --prod
```

### Cron Jobs Configuration

The project is set up to run the following cron job:

1. **Scraper & Grade Calculator**: Runs every 5 minutes
   - Path: `/api/run_scraper`
   - Schedule: `*/5 * * * *`
   - The grade calculator automatically runs immediately after the scraper completes

### Additional Configuration

- **Chrome Profile**: The Chrome profile is set up automatically during deployment and used by the scraper.
  
- **Logs**: All logs are stored in the `/logs` directory.

- **Environment Variables**: For automated deployments, environment variables are managed through GitHub Secrets.

## Development

### Running Locally

```bash
# Run the scraper
python src/scraper.py

# Run the grade calculator
python src/grade_calculator.py
```

### Update Dependencies

```bash
pip freeze > requirements.txt
```

## Troubleshooting

If you encounter issues with the Chrome profile or scraper:

1. Check the logs in the Vercel dashboard
2. Ensure the Chrome profile is set up correctly
3. Verify that your Supabase credentials are correct
4. Check that the scraper is able to access the target website 