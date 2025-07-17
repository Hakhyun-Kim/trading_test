#!/usr/bin/env python3
"""
Web launcher for Upbit Trading Bot
Replaces the desktop tkinter application with a modern web interface
"""

import os
import sys
import webbrowser
import threading
import time
import logging
import signal
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'websockets',
        'pydantic',
        'pandas',
        'numpy',
        'ccxt',
        'requests'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def open_browser(url, delay=2):
    """Open browser after a delay"""
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
            print(f"🌐 Opening browser at {url}")
        except Exception as e:
            print(f"❌ Failed to open browser: {e}")
            print(f"Please manually open: {url}")
    
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('upbit_bot.log')
        ]
    )

def main():
    """Main entry point"""
    print("🚀 Upbit Trading Bot - Web Interface")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup logging
    setup_logging()
    
    # Import the web app
    try:
        from web_app import app
        import uvicorn
    except ImportError as e:
        print(f"❌ Failed to import web app: {e}")
        sys.exit(1)
    
    # Configuration
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"
    
    print(f"📡 Starting web server at {url}")
    print("⚡ Features:")
    print("  • Modern responsive web interface")
    print("  • Real-time WebSocket updates")
    print("  • No Unicode encoding issues")
    print("  • Better debugging with browser dev tools")
    print("  • All existing functionality preserved")
    print()
    
    # Open browser automatically
    open_browser(url, delay=3)
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        print("\n🛑 Shutting down web server...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the server
        print("🔥 Server starting...")
        print(f"📱 Access the web interface at: {url}")
        print("🔧 Use Ctrl+C to stop the server")
        print()
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 