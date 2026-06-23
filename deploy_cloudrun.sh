#!/bin/bash
# CivicFix Google Cloud Run Deploy Helper Script
# Run this inside Google Cloud Shell (https://shell.cloud.google.com) or a configured terminal.

echo "===================================================="
echo "🚀 Preparing CivicFix Deployment to Google Cloud Run..."
echo "===================================================="

# Check if we are logged in
if ! gcloud auth list --format="value(account)" | grep -q "@"; then
    echo "❌ Error: You are not logged in to Google Cloud."
    echo "Please run 'gcloud auth login' or run this from Google Cloud Shell."
    exit 1
fi

# Ask for the configuration parameters (or read them from local environment)
READ_API_KEY=""
READ_DB_URL=""

if [ -z "$GOOGLE_API_KEY" ]; then
    read -p "Enter your GOOGLE_API_KEY (Gemini API key): " READ_API_KEY
else
    READ_API_KEY="$GOOGLE_API_KEY"
fi

if [ -z "$DATABASE_URL" ]; then
    read -p "Enter your DATABASE_URL (Supabase/Neon PostgreSQL string): " READ_DB_URL
else
    READ_DB_URL="$DATABASE_URL"
fi

if [ -z "$READ_API_KEY" ] || [ -z "$READ_DB_URL" ]; then
    echo "❌ Error: GOOGLE_API_KEY and DATABASE_URL are required to run the service."
    exit 1
fi

echo "📦 Building container and deploying to Cloud Run..."
gcloud run deploy civicfix \
    --source . \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_API_KEY="$READ_API_KEY",DATABASE_URL="$READ_DB_URL"

echo "===================================================="
echo "✅ Deployment Attempt Finished!"
echo "Check the URL printed above to test your live app."
echo "===================================================="
