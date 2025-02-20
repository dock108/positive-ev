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

### Security
- Local network access is restricted to internal network devices only
- Debug mode remains active for development - not recommended for production use 