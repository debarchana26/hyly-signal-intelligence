#!/bin/bash

echo "Setting up Python environment for km-signal-pipeline..."

# Install required libraries
pip install notion-client google-api-python-client google-auth-httplib2 google-auth-oauthlib

echo ""
echo "Now you need to provide:"
echo "1. NOTION_TOKEN - Your Notion integration token"
echo "2. GOOGLE_CREDENTIALS - Path to your Google service account JSON"
echo ""
echo "Run with:"
echo "export NOTION_TOKEN='secret_...'"
echo "export GOOGLE_CREDENTIALS='/path/to/credentials.json'"
echo ""
echo "Then we can run the pipeline with Python directly."