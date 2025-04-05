#!/usr/bin/env python3
"""
Run script for AI Desk Buddy with environment variable support
"""
import os
import sys
import subprocess
import dotenv

def main():
    # Load environment variables from .env file
    dotenv.load_dotenv()
    
    # Execute main.py with the current Python interpreter
    cmd = [sys.executable, 'main.py']
    subprocess.run(cmd)

if __name__ == "__main__":
    main()