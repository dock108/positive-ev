# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.0] - 2025-03-15

### Added
- Comprehensive file header documentation for all Python modules
- New `get_most_recent_timestamp()` function in supabase_client.py
- Enhanced grading logic to use most recent timestamp from database
- Improved error handling and logging across all modules

### Changed
- Updated author information to "highlyprofitable108"
- Streamlined module imports and organization
- Improved code documentation and type hints
- Enhanced error handling in database operations
- Optimized database queries for better performance

### Removed
- Unused functions from supabase_client.py:
  - get_all_records()
  - get_existing_grades()
  - upsert_single_record()
  - get_most_recent_bets()

## [2.3.0] - 2025-03-14

### Changed
- Simplified Chrome profile configuration to automatically detect OS
- Removed IS_LOCAL and IS_VERCEL environment variables
- Streamlined directory configuration for logs and backups
- Updated deployment documentation for Raspberry Pi support

### Added
- Support for Raspberry Pi deployment with automatic Chrome profile detection
- Cross-platform Chrome profile path handling (macOS and Linux)

### Removed
- Redundant environment variables and configuration checks
- Legacy Chrome profile export functionality

## [2.2.0] - 2025-03-13

### Changed
- Simplified Vercel deployment architecture
  - Removed complex API routing in favor of single endpoint
  - Streamlined serverless function implementation
  - Configured daily cron job for automated pipeline runs
  - Improved error handling and response formatting

### Fixed
- Resolved Vercel serverless function handler issues
- Fixed Python module import problems in Vercel environment
- Corrected HTTP response handling in API endpoint

### Removed
- Removed unnecessary API complexity
- Cleaned up redundant documentation files
- Removed unused deployment configurations

## [2.1.0] - 2025-02-23

### Added
- Enhanced bet details popup functionality:
  - Added metrics summary section showing EV%, Edge%, Win Probability, and Kelly%
  - Added paginated odds history display (10 items per page)
  - Added automatic URL hyperlinking in descriptions and reasoning text
  - Added validation status dropdown in popup
  - Added comprehensive odds history with timestamps and sportsbook info

### Changed
- Improved thirty_day_results page:
  - Updated to 25 items per page for better readability
  - Made sport column font smaller and more compact
  - Adjusted confidence score column positioning
  - Improved date format display (removed year for compactness)
  - Enhanced filter button with expandable advanced options
  - Summary statistics now show complete 30-day data regardless of filters

### Fixed
- Fixed summary statistics calculation to use complete 30-day data
- Fixed pagination display and navigation
- Fixed validation status updates in popup
- Fixed odds history display formatting

## [2.0.0] - 2025-02-22

### Added
- Automated database backup before schema changes
- Sport and league columns to betting_data table
- New indexes for improved query performance:
  - idx_betting_data_sport_league
  - idx_betting_data_event_time
  - idx_betting_data_composite
- Whitelist of supported leagues with standardized names:
  - Basketball: NBA, NCAAB
  - Hockey: NHL
  - Tennis: WTA, ATP, ATP Challenger, ITF Men
  - Soccer: Saudi League, Premier League, FA Cup, La Liga, Champions League, Europa League, Serie A
  - Baseball: MLB
  - Football: NFL, NCAAF
  - MMA: UFC

### Changed
- Updated sport detection logic to use standardized sport/league pairs
- Modified bet evaluation to filter for supported leagues only
- Improved search queries to include league information
- Enhanced sport-specific instructions in evaluation prompts

### Fixed
- SQLite compatibility issues with ALTER TABLE syntax
- Sport detection accuracy by using standardized league names
- Search relevance by including league information in queries

### Security
- Added automatic database backup before schema changes
- Improved error handling for database operations

## [1.0.0] - 2025-02-21

Initial release

## [Unreleased]

### Added
- Network accessibility feature
  - Configured Flask application to listen on all network interfaces (0.0.0.0)
  - Enabled access to the betting dashboard from any device on local network
  - Maintained port 5001 for application access
  - Preserved debug mode for development purposes

- Enhanced Opportunity Tracking Features
  - Implemented unique opportunity tracking to prevent duplicate entries
  - Added comprehensive odds history tracking with timestamps
  - Improved opportunity details popup with complete odds movement history
  - Added sportsbook-specific opportunity tracking and filtering
  - Implemented "Already Bet" marking functionality
  - Added sport-specific filtering and analysis
  - Enhanced grade distribution insights

- Advanced Parlay Calculator Improvements
  - Added smart bet size recommendations based on individual legs
  - Implemented correlation risk warnings and adjustments
  - Added detailed market comparison analysis
  - Enhanced parlay grading system
  - Added comprehensive insights and recommendations
  - Implemented true vs. market probability comparison
  - Added parlay-specific Kelly criterion calculations
  - Added risk-adjusted expected value calculations

- UI/UX Improvements
  - Right-justified "Already Bet" checkbox for better visibility
  - Streamlined odds history display in opportunity details popup
  - Improved sportsbook information display
  - Enhanced sorting and filtering options for opportunities

### Fixed
- Fixed SQL query in thirty_day_results to properly handle unique opportunities
- Resolved template syntax error in opportunity details popup
- Fixed odds history display to show correct sportsbook information
- Improved error handling in opportunity details API endpoint

### Security
- Local network access is restricted to internal network devices only
- Debug mode remains active for development - not recommended for production use

### Performance
- Optimized SQL queries for better performance
- Improved data archiving process for historical odds
- Enhanced opportunity tracking system efficiency

## [Unreleased]

### Added
- Network accessibility feature
  - Configured Flask application to listen on all network interfaces (0.0.0.0)
  - Enabled access to the betting dashboard from any device on local network
  - Maintained port 5001 for application access
  - Preserved debug mode for development purposes

### Security
- Local network access is restricted to internal network devices only
- Debug mode remains active for development - not recommended for production use 