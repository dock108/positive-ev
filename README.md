# 🎲 Positive EV Sports Betting System

```ascii
    ____            _           _    __     ___    ___
   / __ \____  ____(_)__  _____/ |  / /__  / _ \  / _ \
  / /_/ / __ \/ __/ / _ \/ ___/  | / / _ \/ / / / / / / /
 / ____/ /_/ / /_/ /  __/ /  | | |/ /  __/ /_/ / / /_/ /
/_/    \____/\__/_/\___/_/   |_|___/\___/\____/  \____/
```

> *Because why gamble on your future when you can mathematically optimize it?* 🤓

## 🚀 Features

### 📊 Real-time Odds Monitoring
```ascii
┌─────────────────────────────────┐
│  Live Odds Tracking System      │
├─────────────────────────────────┤
│  ⚡ Real-time updates           │
│  🔄 Automated comparisons      │
│  📈 Historical analysis        │
└─────────────────────────────────┘
```
- Live tracking of odds across multiple sportsbooks.
- Automated odds comparison and arbitrage detection.
- Historical odds tracking and analysis to inform betting strategies.

### 🎯 Bet Evaluation System
```ascii
┌─────────────────────────────────┐
│  Advanced Grading Algorithm     │
├─────────────────────────────────┤
│  ⭐ Quality assessment         │
│  📊 Performance tracking       │
│  💰 Risk optimization         │
└─────────────────────────────────┘
```
- Multi-factor grading system that considers:
  - Expected Value (55%): Primary financial indicator
  - Timing Score (15%): Proximity to event start time
  - EV Trend Score (15%): How EV has changed since discovery
  - Bayesian Confidence (15%): Sophisticated confidence measure
- Advanced EV normalization with capping for realistic assessment
- Historical trend analysis using initial bet details
- Comprehensive debug logging for transparent decision making
- Override rules for unrealistically high EV percentages

### 💾 Data Management
```ascii
┌─────────────────────────────────┐
│  Data Integrity Pipeline       │
├─────────────────────────────────┤
│  🔄 Automated collection      │
│  💾 Secure storage            │
│  🔒 Backup systems           │
└─────────────────────────────────┘
```
- Automated data collection and storage.
- Historical data analysis.
- Backup and recovery systems.
- Data integrity validation.

### 🌐 Cross-platform Support
```ascii
┌─────────────────────────────────┐
│  Platform Compatibility        │
├─────────────────────────────────┤
│  🍎 macOS                     │
│  🐧 Linux                     │
│  🍓 Raspberry Pi              │
└─────────────────────────────────┘
```
- macOS, Linux, and Raspberry Pi compatibility.
- Automated environment detection.
- Platform-specific optimizations.

## 🛠️ Prerequisites

```ascii
┌─────────────────────────────────┐
│  Required Components           │
├─────────────────────────────────┤
│  🐍 Python 3.8+               │
│  🌐 Chrome/Chromium          │
│  🔧 Git                      │
│  ☁️ Vercel (optional)        │
│  📦 pip                      │
└─────────────────────────────────┘
```

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/positive-ev.git
   cd positive-ev
   ```

2. **Set up Python environment**:
   ```bash
   # Create and activate virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate  # On Unix/macOS
   # or
   .\venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   # Install all required packages
   pip install -r requirements.txt
   
   # If you encounter any issues, try installing key packages individually:
   pip install supabase
   pip install selenium
   pip install pandas
   pip install numpy
   ```

4. **Set up Chrome/Chromium profile**:
   ```ascii
   ┌─────────────────────────────────┐
   │  Chrome Profile Locations      │
   ├─────────────────────────────────┤
   │  🍎 macOS:                     │
   │     ~/Library/Application      │
   │     Support/Google/Chrome/     │
   │  🐧 Linux:                     │
   │     ~/.config/google-chrome/   │
   │  🍓 Raspberry Pi:              │
   │     ~/.config/chromium/        │
   └─────────────────────────────────┘
   ```

5. **Configure environment variables**:
   ```bash
   # Create .env file
   touch .env
   
   # Add required variables
   echo "BETFAIR_API_KEY=your_api_key" >> .env
   echo "BETFAIR_SESSION_TOKEN=your_session_token" >> .env
   echo "SUPABASE_URL=your_supabase_url" >> .env
   echo "SUPABASE_KEY=your_supabase_key" >> .env
   ```

## 📁 Project Structure

```ascii
positive-ev/
├── src/                    # 🧠 Source code
│   ├── scraper.py         # 🕷️ Odds scraping
│   ├── grade_calculator.py # 📊 Bet evaluation
│   ├── config.py          # ⚙️ Configuration
│   └── utils/             # 🛠️ Utilities
├── logs/                   # 📝 Application logs
├── data/                   # 💾 Data storage
│   ├── odds/              # 📈 Historical odds
│   ├── bets/              # 🎲 Bet history
│   └── backups/           # 💾 Data backups
├── tests/                  # 🧪 Test suite
├── docs/                   # 📚 Documentation
└── scripts/               # 🔧 Utility scripts
```

## 🚀 Usage

### 🏠 Local Development

1. **Set PYTHONPATH**:
   ```bash
   # For Unix/macOS
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   
   # For Windows (PowerShell)
   $env:PYTHONPATH = "$env:PYTHONPATH;$(pwd)"
   ```

2. **Start the scraper**:
   ```bash
   python src/scraper.py
   ```

3. **Run bet evaluation**:
   ```bash
   python src/grade_calculator.py
   ```

### ⏰ Automated Scheduling

```ascii
┌─────────────────────────────────┐
│  Crontab Configuration         │
├─────────────────────────────────┤
│  */5 * * * *                   │
│  └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘      │
│    │     │     │     └─ Day   │
│    │     │     └────── Month  │
│    │     └──────────── Week   │
│    └────────────────── Hour    │
└─────────────────────────────────┘
```

```bash
# Add to crontab (crontab -e)
*/5 * * * * cd /path/to/project && \
    PYTHONPATH=/path/to/project \
    /path/to/python src/scraper.py && \
    PYTHONPATH=/path/to/project \
    /path/to/python src/grade_calculator.py
```

### ☁️ Vercel Deployment

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Deploy to Vercel**:
   ```bash
   ./deploy_to_vercel.sh
   ```

3. **Configure environment variables** in Vercel dashboard

## 💾 Data Management

### 🔄 Backup System

```ascii
┌─────────────────────────────────┐
│  Backup Rotation Schedule      │
├─────────────────────────────────┤
│  📅 Daily backups              │
│  🔄 7-day rotation            │
│  🧹 Auto cleanup              │
└─────────────────────────────────┘
```

### 📝 Logging

```ascii
┌─────────────────────────────────┐
│  Log File Structure           │
├─────────────────────────────────┤
│  scraper.log                  │
│  ├── Odds scraping           │
│  └── Data collection         │
│  grade_calculator.log         │
│  ├── Bet evaluation          │
│  └── Performance metrics     │
│  error.log                    │
│  └── Error tracking          │
└─────────────────────────────────┘
```

## 🔧 Troubleshooting

### 🚨 Common Issues

1. **Import Errors**
   ```ascii
   ┌─────────────────────────────────┐
   │  Import Error Solutions        │
   ├─────────────────────────────────┤
   │  1. Set PYTHONPATH            │
   │  2. Check virtual environment  │
   │  3. Verify package install     │
   └─────────────────────────────────┘
   ```
   - Ensure PYTHONPATH is set correctly
   - Verify you're in the virtual environment
   - Check if all packages are installed

2. **Chrome Profile Not Found**
   ```ascii
   ┌─────────────────────────────────┐
   │  Troubleshooting Steps        │
   ├─────────────────────────────────┤
   │  1. Verify installation       │
   │  2. Check profile path        │
   │  3. Verify permissions        │
   └─────────────────────────────────┘
   ```

3. **API Connection Issues**
   ```ascii
   ┌─────────────────────────────────┐
   │  Connection Checklist          │
   ├─────────────────────────────────┤
   │  🔑 API keys valid            │
   │  🌐 Internet connected        │
   │  ⚡ Rate limits ok            │
   └─────────────────────────────────┘
   ```

4. **Data Collection Errors**
   ```ascii
   ┌─────────────────────────────────┐
   │  Error Resolution             │
   ├─────────────────────────────────┤
   │  📝 Check logs                │
   │  🔒 Verify permissions        │
   │  💾 Check disk space          │
   └─────────────────────────────────┘
   ```

## 🤝 Contributing

```ascii
┌─────────────────────────────────┐
│  Contribution Process          │
├─────────────────────────────────┤
│  1. 🍴 Fork repository         │
│  2. 🌿 Create feature branch   │
│  3. 💾 Commit changes          │
│  4. 📤 Push to branch          │
│  5. 🔄 Create Pull Request     │
└─────────────────────────────────┘
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 💬 Support

For support, please open an issue in the GitHub repository or contact the maintainers.

---

*Made with ❤️ by math-loving betting enthusiasts* 🎲 