# Positive EV

A betting analytics platform that scrapes positive EV betting opportunities and calculates bet grades.

## Features

- Automated scraping of betting opportunities
- Advanced bet grading system
- Real-time analytics and insights
- Automated deployment to Vercel
- Daily scheduled pipeline runs

## Quick Start

### Prerequisites

1. A Vercel account
2. Vercel CLI installed: `npm install -g vercel`
3. A Chrome profile with necessary login sessions
4. Python 3.8 or higher

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/positive-ev.git
cd positive-ev
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the example environment file:
```bash
cp .env.example .env
```

4. Edit `.env` with your configuration:
- `SUPABASE_URL` and `SUPABASE_KEY`: Your Supabase credentials
- `CHROME_PROFILE`: Path to your Chrome profile
- Other settings as needed

### Deployment

The recommended way to deploy is using our automated script:

```bash
chmod +x deploy_to_vercel.sh
./deploy_to_vercel.sh
```

For detailed deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Development

### Running Locally

```bash
# Run the complete pipeline
python src/run_pipeline.py

# Or run individual components
python src/scraper.py
python src/grade_calculator.py
```

### Project Structure

```
positive-ev/
├── api/                # Vercel serverless function
├── src/               # Source code
│   ├── scraper.py    # Web scraping logic
│   ├── grade_calculator.py  # Bet grading logic
│   └── ...
├── tests/            # Test files
└── docs/             # Documentation
```

### Key Components

1. **Scraper**: Collects betting opportunities from various sources
2. **Grade Calculator**: Analyzes and grades betting opportunities
3. **Pipeline**: Orchestrates the entire process
4. **API**: Single serverless endpoint for scheduled runs

## Configuration

### Environment Variables

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase API key
- `CHROME_PROFILE`: Path to Chrome profile
- See `.env.example` for all options

### Chrome Profile

The application requires a Chrome profile with valid authentication cookies. This profile is:
- Manually exported from your local machine
- Deployed to Vercel with your application
- Used for authenticated scraping

### Scheduled Runs

The pipeline runs automatically:
- Once per day at midnight UTC
- Configurable via `vercel.json`
- Manually triggerable via API endpoint

## Documentation

- [Deployment Guide](./DEPLOYMENT.md) - Detailed deployment instructions
- [Changelog](./CHANGELOG.md) - Version history and updates

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
   - Check environment variables
   - Review deployment logs

### Getting Help

1. Check the [Troubleshooting](./DEPLOYMENT.md#troubleshooting) section
2. Review Vercel function logs
3. Open an issue on GitHub

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 