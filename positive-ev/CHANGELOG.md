# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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