#!/bin/bash
# Automated Vercel Deployment Script
# This script automates the process of exporting the Chrome profile and deploying to Vercel

set -e  # Exit on any error

echo "=== Positive EV Vercel Deployment Script ==="
echo "This script will:"
echo "1. Export your Chrome profile"
echo "2. Deploy to Vercel"
echo "3. Clean up temporary files"
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "Error: Vercel CLI is not installed."
    echo "Please install it with: npm i -g vercel"
    exit 1
fi

# Check if user is logged in to Vercel
vercel whoami &> /dev/null || {
    echo "You need to log in to Vercel first."
    vercel login
}

# Step 1: Export Chrome profile
echo "=== Step 1: Exporting Chrome profile ==="
python export_chrome_profile.py

# Check if export was successful
if [ ! -d "chrome-profile" ]; then
    echo "Error: Chrome profile export failed."
    exit 1
fi

echo "Chrome profile exported successfully."

# Step 2: Deploy to Vercel
echo "=== Step 2: Deploying to Vercel ==="
echo "Would you like to deploy to production? (y/n)"
read -r deploy_prod

if [[ "$deploy_prod" =~ ^[Yy]$ ]]; then
    echo "Deploying to production..."
    vercel --prod
else
    echo "Deploying to preview environment..."
    vercel
fi

# Step 3: Clean up (optional)
echo "=== Step 3: Clean up ==="
echo "Would you like to remove the local chrome-profile directory? (y/n)"
read -r cleanup

if [[ "$cleanup" =~ ^[Yy]$ ]]; then
    echo "Removing chrome-profile directory..."
    rm -rf chrome-profile
    echo "Chrome profile directory removed."
else
    echo "Keeping chrome-profile directory for future deployments."
fi

echo ""
echo "=== Deployment Complete ==="
echo "Your application has been deployed to Vercel."
echo "Check the Vercel dashboard for deployment status and logs." 