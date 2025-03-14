# Positive EV

A betting analytics platform that scrapes positive EV betting opportunities and calculates bet grades.

## Deployment to Vercel

This project is configured for deployment to Vercel with automated cron jobs for scraping and grading.

### Prerequisites

1. A Vercel account
2. Vercel CLI installed: `npm install -g vercel`
3. A GitHub account (for automated deployments)

### Deployment Methods

#### Option 1: Automated Deployment (Recommended)

This project uses GitHub Actions to automatically deploy to Vercel whenever changes are pushed to:
- `main` branch → Production environment
- `staging` branch → Preview/Staging environment

For setup instructions, see [GitHub Actions Setup Guide](./docs/GITHUB_ACTIONS_SETUP.md).

**Note**: The Chrome profile setup must still be done manually after deployment.

#### Option 2: Manual Deployment

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