#!/bin/bash

echo "Starting project structure cleanup..."

# Ensure we are in the correct directory
if [ ! -d "app" ]; then
    echo "❌ Error: 'app' folder not found."
    echo "   Please make sure you are inside the 'backend' folder."
    exit 1
fi

# 1. Fix the nested 'app/app' issue
if [ -d "app/app" ]; then
    echo "🔄 Found nested 'app/app'. Moving files up..."
    
    # Move the 'routers' folder and any other files up one level
    # We use cp -r then rm to be safer on some Windows setups
    cp -r app/app/* app/
    rm -rf app/app
    
    echo "✅ Moved contents from 'app/app' to 'app/'."
else
    echo "ℹ️  No nested 'app/app' found. Skipping."
fi

# 2. Delete unused folders (models, routes)
if [ -d "app/models" ]; then
    rm -rf app/models
    echo "🗑️  Removed unused 'app/models' folder."
fi

if [ -d "app/routes" ]; then
    rm -rf app/routes
    echo "🗑️  Removed unused 'app/routes' folder (we use 'routers' now)."
fi

echo "-----------------------------------"
echo "✅ Structure fixed successfully!"
echo "-----------------------------------"