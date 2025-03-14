# Positive EV

A betting analytics platform that scrapes positive EV betting opportunities and calculates bet grades.

## Features

- Automated scraping of betting opportunities
- Advanced bet grading system
- Real-time analytics and insights
- Cross-platform support (macOS, Linux, Raspberry Pi)
- Automated deployment to Vercel
- Daily scheduled pipeline runs

## Quick Start

### Prerequisites

1. A Vercel account (optional, for cloud deployment)
2. Vercel CLI installed: `npm install -g vercel` (optional)
3. Python 3.8 or higher
4. Chrome/Chromium browser

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
- Other settings as needed

### Deployment Options

#### Local Development (macOS)
The scraper will automatically use your Chrome profile at:
```
~/Library/Application Support/Google/Chrome/ScraperProfile
```

#### Raspberry Pi Deployment
The scraper will automatically use the Chromium profile at:
```
~/.config/chromium/Default
```

#### Vercel Deployment (Optional)
For cloud deployment:
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
- See `.env.example` for all options

### Chrome/Chromium Profile

The application automatically detects and uses the appropriate Chrome/Chromium profile based on your operating system:
- macOS: `~/Library/Application Support/Google/Chrome/ScraperProfile`
- Linux/Raspberry Pi: `~/.config/chromium/Default`

### Scheduled Runs

The pipeline runs automatically:
- Every 5 minutes (configurable)
- At 2 and 32 minutes past every hour
- Configurable via crontab

## Documentation

- [Deployment Guide](./DEPLOYMENT.md) - Detailed deployment instructions
- [Changelog](./CHANGELOG.md) - Version history and updates

## Troubleshooting

### Common Issues

1. **Chrome/Chromium Profile Issues**
   - Verify profile exists and has valid cookies
   - Check logs for detailed error messages
   - Ensure proper permissions on profile directory

2. **Pipeline Failures**
   - Check logs in the `logs` directory
   - Verify Supabase connection
   - Check Chrome/Chromium profile status

3. **Deployment Issues**
   - Review deployment logs
   - Check environment variables
   - Verify file permissions

### Getting Help

1. Check the error message in the logs
2. Review the relevant log files
3. Check Chrome/Chromium profile status
4. Verify environment variables

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 