#!/usr/bin/env python3
"""
Simple launcher for the Upbit Trading Bot Desktop Application
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from desktop_app import UpbitTradingBotGUI
    
    if __name__ == "__main__":
        print("Starting Upbit Trading Bot Desktop Application...")
        app = UpbitTradingBotGUI()
        app.run()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please make sure all dependencies are installed:")
    print("pip install matplotlib pandas")
    
except Exception as e:
    print(f"Error starting application: {e}")
    input("Press Enter to exit...") 