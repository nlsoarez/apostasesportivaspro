"""
Vercel entry point for Flask application.
This file imports the Flask app from main.py and exposes it to Vercel.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Vercel expects the app to be available as 'app'
# This is already done by importing from main
