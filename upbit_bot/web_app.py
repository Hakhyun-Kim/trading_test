from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import asyncio
import logging
from .backtest import EnhancedUpbitBacktest, BacktestConfig, ArbitrageStrategy
from .trading_bot import UpbitTradingBot, TradingConfig
import uuid
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enhanced Upbit Trading Bot", version="2.0.0")

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Global state management
active_sessions: Dict[str, Dict[str, Any]] = {}
virtual_traders: Dict[str, UpbitTradingBot] = {}
connection_manager = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.session_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if session_id not in self.session_connections:
            self.session_connections[session_id] = []
        self.session_connections[session_id].append(websocket)
        
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        self.active_connections.remove(websocket)
        if session_id in self.session_connections:
            self.session_connections[session_id].remove(websocket)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_personal_message(self, message: dict, session_id: str):
        if session_id in self.session_connections:
            for connection in self.session_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "active_sessions": len(active_sessions),
            "virtual_traders": len(virtual_traders)
        }
    )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/backtest", response_class=JSONResponse)
async def run_backtest_api(
    start_date: str = Form(...),
    end_date: str = Form(...),
    initial_balance: float = Form(10000.0),
    max_trade_amount: float = Form(1000.0),
    price_threshold: float = Form(0.5),
    stop_loss: float = Form(2.0),
    take_profit: float = Form(1.0),
    max_trades_per_day: int = Form(10),
    use_real_data: bool = Form(False)
):
    """Run backtest via API"""
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Validate inputs
        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        if initial_balance <= 0 or max_trade_amount <= 0:
            raise HTTPException(status_code=400, detail="Amounts must be positive")
        
        # Create backtest configuration
        config = BacktestConfig(
            initial_balance_usd=initial_balance,
            initial_balance_krw=0.0,  # API endpoint doesn't support KRW yet
            max_trade_amount=max_trade_amount,
            price_threshold=price_threshold,
            stop_loss_threshold=stop_loss,
            take_profit_threshold=take_profit,
            max_trades_per_day=max_trades_per_day
        )
        
        # Run backtest
        backtest = EnhancedUpbitBacktest(config)
        result = backtest.run_backtest(start_dt, end_dt, use_real_data=use_real_data)
        
        # Return structured result
        return {
            "success": True,
            "result": {
                "initial_balance": result.initial_balance,
                "final_balance": result.final_balance,
                "total_return": result.total_return,
                "return_percentage": result.return_percentage,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "average_win": result.average_win,
                "average_loss": result.average_loss
            },
            "trades": [
                {
                    "timestamp": trade.timestamp,
                    "action": trade.action,
                    "amount_usd": trade.amount_usd,
                    "usdt_krw_price": trade.usdt_krw_price,
                    "usd_krw_rate": trade.usd_krw_rate,
                    "difference_percentage": trade.difference_percentage,
                    "success": trade.success
                }
                for trade in result.trades
            ],
            "daily_returns": result.daily_returns,
            "equity_curve": result.equity_curve
        }
        
    except Exception as e:
        logger.error(f"Backtest error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-backtest", response_class=HTMLResponse)
async def run_backtest_form(
    request: Request,
    start_date: str = Form(...),
    end_date: str = Form(...),
    initial_balance: float = Form(10000.0),
    initial_balance_krw: float = Form(0.0),
    max_trade_amount: float = Form(1000.0),
    price_threshold: float = Form(0.5),
    stop_loss: float = Form(2.0),
    take_profit: float = Form(1.0),
    max_trades_per_day: int = Form(10),
    use_real_data: bool = Form(False)
):
    """Run backtest and return HTML results"""
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Create backtest configuration
        config = BacktestConfig(
            initial_balance_usd=initial_balance,
            initial_balance_krw=initial_balance_krw,
            max_trade_amount=max_trade_amount,
            price_threshold=price_threshold,
            stop_loss_threshold=stop_loss,
            take_profit_threshold=take_profit,
            max_trades_per_day=max_trades_per_day
        )
        
        # Run backtest
        backtest = EnhancedUpbitBacktest(config)
        result = backtest.run_backtest(start_dt, end_dt, use_real_data=use_real_data)
        
        # Format trades for template
        formatted_trades = []
        for trade in result.trades:
            formatted_trades.append({
                'date': datetime.fromisoformat(trade.timestamp.replace('Z', '+00:00')),
                'action': trade.action,
                'amount_usd': trade.amount_usd,
                'usd_krw_rate': trade.usd_krw_rate,
                'usdt_krw_price': trade.usdt_krw_price,
                'difference_percentage': trade.difference_percentage,
                'success': trade.success
            })
        
        # Format results for template
        template_results = {
            'initial_balance_usd': result.initial_balance,
            'final_balance_usd': result.final_balance,
            'profit_loss_usd': result.total_return,
            'profit_loss_percentage': result.return_percentage,
            'max_drawdown': result.max_drawdown,
            'sharpe_ratio': result.sharpe_ratio,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'average_win': result.average_win,
            'average_loss': result.average_loss
        }
        
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "results": template_results,
                "trades": formatted_trades,
                "config": config,
                "equity_curve": result.equity_curve,
                "daily_returns": result.daily_returns
            }
        )
        
    except Exception as e:
        logger.error(f"Backtest form error: {str(e)}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": str(e),
                "error_type": "Backtest Error"
            }
        )

@app.get("/virtual", response_class=HTMLResponse)
async def virtual_trading(request: Request):
    """Virtual trading interface"""
    return templates.TemplateResponse(
        "virtual.html",
        {"request": request}
    )

@app.get("/live", response_class=HTMLResponse)
async def live_trading(request: Request):
    """Live trading interface"""
    return templates.TemplateResponse(
        "live.html",
        {"request": request}
    )

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request):
    """Analytics dashboard"""
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request}
    )

@app.get("/api/sessions")
async def get_active_sessions():
    """Get active trading sessions"""
    return {
        "active_sessions": len(active_sessions),
        "virtual_traders": len(virtual_traders),
        "sessions": [
            {
                "id": session_id,
                "created": session_data.get("created"),
                "type": session_data.get("type"),
                "status": session_data.get("status")
            }
            for session_id, session_data in active_sessions.items()
        ]
    }

@app.post("/api/sessions")
async def create_trading_session(
    session_type: str = Form(...),
    config: str = Form(...)
):
    """Create a new trading session"""
    try:
        session_id = str(uuid.uuid4())
        config_data = json.loads(config)
        
        # Create trading configuration
        trading_config = TradingConfig(
            max_trade_amount=config_data.get("max_trade_amount", 1000.0),
            price_threshold=config_data.get("price_threshold", 0.5),
            stop_loss_threshold=config_data.get("stop_loss_threshold", 2.0),
            take_profit_threshold=config_data.get("take_profit_threshold", 1.0),
            max_trades_per_day=config_data.get("max_trades_per_day", 10),
            max_daily_loss=config_data.get("max_daily_loss", 500.0),
            emergency_stop_loss=config_data.get("emergency_stop_loss", 5.0)
        )
        
        # Create trading bot
        if session_type == "virtual":
            bot = UpbitTradingBot(
                virtual_mode=True,
                initial_balance_usd=config_data.get("initial_balance", 10000.0),
                config=trading_config
            )
        else:
            api_key = config_data.get("api_key")
            secret_key = config_data.get("secret_key")
            if not api_key or not secret_key:
                raise HTTPException(status_code=400, detail="API keys required for live trading")
            
            bot = UpbitTradingBot(
                api_key=api_key,
                secret_key=secret_key,
                virtual_mode=False,
                config=trading_config
            )
        
        # Store session
        active_sessions[session_id] = {
            "created": datetime.now().isoformat(),
            "type": session_type,
            "status": "active",
            "config": config_data
        }
        
        virtual_traders[session_id] = bot
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"{session_type.title()} trading session created"
        }
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def stop_trading_session(session_id: str):
    """Stop a trading session"""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Stop the bot
        if session_id in virtual_traders:
            virtual_traders[session_id].stop_bot()
            del virtual_traders[session_id]
        
        # Remove session
        del active_sessions[session_id]
        
        return {
            "success": True,
            "message": "Trading session stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/trading/{session_id}")
async def trading_websocket(websocket: WebSocket, session_id: str):
    """Enhanced WebSocket for real-time trading updates"""
    await manager.connect(websocket, session_id)
    
    try:
        # Initialize session if not exists
        if session_id not in virtual_traders:
            virtual_traders[session_id] = UpbitTradingBot(virtual_mode=True)
            active_sessions[session_id] = {
                "created": datetime.now().isoformat(),
                "type": "virtual",
                "status": "active"
            }
        
        trader = virtual_traders[session_id]
        
        while True:
            try:
                # Get current market status
                opportunity = trader.calculate_arbitrage_opportunity()
                balance = trader.get_current_balance()
                performance = trader.get_performance_summary()
                
                # Send comprehensive update
                await manager.send_personal_message({
                    "type": "market_update",
                    "timestamp": datetime.now().isoformat(),
                    "opportunity": opportunity,
                    "balance": balance,
                    "performance": performance,
                    "trade_history": [
                        {
                            "timestamp": trade.timestamp,
                            "action": trade.action,
                            "amount_usd": trade.amount_usd,
                            "usdt_krw_price": trade.usdt_krw_price,
                            "success": trade.success,
                            "profit_loss": trade.profit_loss
                        }
                        for trade in trader.trade_history[-10:]  # Last 10 trades
                    ]
                }, session_id)
                
                # Check for client messages
                try:
                    message = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                    
                    if message["type"] == "execute_trade":
                        action = message["action"]
                        amount = float(message.get("amount", trader.config.max_trade_amount))
                        
                        result = trader.execute_trade(action, amount)
                        
                        await manager.send_personal_message({
                            "type": "trade_result",
                            "result": result,
                            "timestamp": datetime.now().isoformat()
                        }, session_id)
                    
                    elif message["type"] == "get_performance":
                        await manager.send_personal_message({
                            "type": "performance_update",
                            "performance": performance,
                            "timestamp": datetime.now().isoformat()
                        }, session_id)
                    
                    elif message["type"] == "stop_bot":
                        trader.stop_bot()
                        await manager.send_personal_message({
                            "type": "bot_stopped",
                            "message": "Trading bot stopped",
                            "timestamp": datetime.now().isoformat()
                        }, session_id)
                        break
                        
                except asyncio.TimeoutError:
                    pass
                except json.JSONDecodeError:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Invalid JSON message",
                        "timestamp": datetime.now().isoformat()
                    }, session_id)
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in trading loop: {str(e)}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }, session_id)
                await asyncio.sleep(5)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        manager.disconnect(websocket, session_id)

@app.get("/api/market-data")
async def get_market_data():
    """Get current market data"""
    try:
        # Create a temporary bot to get market data
        temp_bot = UpbitTradingBot(virtual_mode=True)
        opportunity = temp_bot.calculate_arbitrage_opportunity()
        
        return {
            "success": True,
            "data": opportunity,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting market data: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/optimize")
async def optimize_strategy(
    start_date: str,
    end_date: str,
    param_ranges: Optional[str] = None
):
    """Optimize trading strategy parameters"""
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Parse parameter ranges
        if param_ranges:
            ranges = json.loads(param_ranges)
        else:
            ranges = {
                'price_threshold': (0.1, 2.0, 0.1),
                'max_trade_amount': (500, 2000, 250),
                'stop_loss_threshold': (1.0, 5.0, 0.5)
            }
        
        # Run optimization
        backtest = EnhancedUpbitBacktest()
        optimization_result = backtest.optimize_parameters(start_dt, end_dt, ranges)
        
        return {
            "success": True,
            "optimization_result": optimization_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Optimization error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Enhanced Upbit Trading Bot Web App starting up...")
    
    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("exports", exist_ok=True)
    
    logger.info("Web app initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Enhanced Upbit Trading Bot Web App...")
    
    # Stop all active trading sessions
    for session_id, trader in virtual_traders.items():
        try:
            trader.stop_bot()
            logger.info(f"Stopped trading session {session_id}")
        except Exception as e:
            logger.error(f"Error stopping session {session_id}: {str(e)}")
    
    # Clear all sessions
    active_sessions.clear()
    virtual_traders.clear()
    
    logger.info("Web app shutdown complete")

# Legacy endpoint for backward compatibility
@app.websocket("/ws/virtual/{client_id}")
async def virtual_trading_websocket_legacy(websocket: WebSocket, client_id: str):
    """Legacy WebSocket endpoint for backward compatibility"""
    await trading_websocket(websocket, client_id) 