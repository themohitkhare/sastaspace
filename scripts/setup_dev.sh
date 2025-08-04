#!/bin/bash
# Setup script for local development

# Backend setup
cd ../backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Reminder: Copy .env.example to .env and fill in secrets
