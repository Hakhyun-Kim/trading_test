# Upbit Trading Bot - Web Interface

🚀 **Modern Web Interface** for cryptocurrency trading with real-time updates!

## ✨ Features

- **🌐 Modern Web UI**: Beautiful responsive design that works on any device
- **⚡ Real-time Updates**: WebSocket-powered live data and progress tracking
- **🔧 No Unicode Issues**: Completely eliminates the cp949 encoding problems
- **📱 Better Debugging**: Use browser dev tools for advanced debugging
- **🎯 All Functionality**: Everything from the desktop app, but better!

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Web Interface

```bash
python run_web.py
```

The application will:
- ✅ Check all dependencies
- 🔥 Start the web server on `http://127.0.0.1:8000`
- 🌐 Automatically open your browser

### 3. Access the Interface

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

## 📊 Interface Overview

### 🔹 Backtest Tab
- Configure backtest parameters
- Real-time progress updates
- Detailed results display
- Debug mode with live alerts

### 🔹 Trading Tab
- Live trading configuration
- Virtual & real trading modes
- Real-time status updates
- Safe API key handling

### 🔹 Optimization Tab
- Parameter optimization
- Progress tracking
- Best parameter discovery
- Performance comparison

### 🔹 Monitor Tab
- Live system monitoring
- Activity logs
- Connection status
- Kimchi premium tracking

## 🎯 Key Advantages Over Desktop App

| Feature | Desktop App | Web App |
|---------|-------------|---------|
| **UI Framework** | tkinter (outdated) | Modern HTML/CSS/JS |
| **Debugging** | Print statements | Browser dev tools |
| **Real-time Updates** | Polling | WebSocket |
| **Unicode Support** | ❌ cp949 issues | ✅ Full UTF-8 |
| **Responsiveness** | Fixed layout | Responsive design |
| **Accessibility** | Local only | Network accessible |
| **Maintenance** | Complex GUI code | Simple web standards |

## 🔧 Technical Details

### Backend
- **FastAPI**: Modern, fast web framework
- **WebSocket**: Real-time bidirectional communication
- **Async/Await**: Non-blocking operations
- **Pydantic**: Data validation and serialization

### Frontend
- **Vanilla JavaScript**: No complex frameworks
- **CSS Grid/Flexbox**: Modern responsive layout
- **WebSocket Client**: Real-time updates
- **Progressive Enhancement**: Works without JavaScript

### Architecture
```
Client (Browser) <--WebSocket--> FastAPI Server <--> Trading Bot Logic
```

## 🚀 API Endpoints

- `GET /`: Main web interface
- `POST /api/backtest`: Run backtest
- `POST /api/trading/start`: Start trading
- `POST /api/trading/stop`: Stop trading
- `GET /api/kimchi-premium`: Get kimchi premium
- `POST /api/optimize`: Optimize parameters
- `GET /api/status`: System status
- `WS /ws`: WebSocket connection

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
python run_web.py

# Access at http://127.0.0.1:8000
```

### Production Deployment
```bash
# Install production dependencies
pip install -r requirements.txt

# Run with production settings
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

## 🔒 Security Notes

- API keys are handled securely
- Virtual mode enabled by default
- Local-only access by default
- No sensitive data in logs

## 🆚 Migration from Desktop App

### Old Way (Desktop)
```bash
python run_desktop.py
```

### New Way (Web)
```bash
python run_web.py
```

**All your existing configuration and trading logic remain unchanged!**

## 📝 Changelog

### Web Interface v1.0
- ✅ Complete desktop app replacement
- ✅ Real-time WebSocket updates
- ✅ Modern responsive UI
- ✅ Unicode encoding fixes
- ✅ Better error handling
- ✅ Enhanced debugging capabilities

## 🤝 Support

If you encounter any issues:
1. Check the browser console for errors
2. Review the server logs
3. Ensure all dependencies are installed
4. Try refreshing the browser

## 🎉 Enjoy Your New Web Interface!

No more tkinter headaches, no more Unicode issues, just pure modern web technology! 🚀 