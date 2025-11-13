"""
Vercel entry point for Flask application.
This file imports the Flask app from main.py and exposes it to Vercel.
"""
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import the Flask app from main.py
from main import app

# Vercel will automatically use the 'app' variable
