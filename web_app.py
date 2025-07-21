"""
Modern Web Interface for Upbit Trading Bot
FastAPI backend with WebSocket support for real-time updates
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

# Import existing trading bot modules
from upbit_bot.backtest import BacktestConfig, EnhancedUpbitBacktest
from upbit_bot.trading_bot import TradingConfig, UpbitTradingBot
from upbit_bot.kimchi_premium import KimchiPremiumCalculator
from debug_backtest import DebugUpbitBacktest
from upbit_bot.bitcoin_backtest import BitcoinBacktestConfig, BitcoinBacktester

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Upbit Trading Bot", description="Modern web interface for cryptocurrency trading")

# Global variables
active_connections: List[WebSocket] = []
running_tasks: Dict[str, bool] = {}
bot_instance: Optional[UpbitTradingBot] = None
kimchi_calculator: Optional[KimchiPremiumCalculator] = None

# Pydantic models for API
class BacktestRequest(BaseModel):
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    initial_balance: float = Field(10000, description="Initial balance in USD")
    max_trade_amount: float = Field(1000, description="Maximum trade amount")
    price_threshold: float = Field(0.5, description="Price threshold percentage")
    buy_threshold: float = Field(0.3, description="Buy when kimchi premium < this %")
    sell_threshold: float = Field(2.0, description="Sell when kimchi premium > this %")
    stop_loss: float = Field(2.0, description="Stop loss percentage")
    take_profit: float = Field(1.0, description="Take profit percentage")
    max_trades_per_day: int = Field(10, description="Maximum trades per day")
    use_real_data: bool = Field(True, description="Use real historical data")
    debug_mode: bool = Field(False, description="Enable debug mode")
    verbose_debug: bool = Field(False, description="Enable verbose debug")
    show_signals: bool = Field(False, description="Show trading signals")

class TradingRequest(BaseModel):
    api_key: Optional[str] = Field(None, description="Upbit API key")
    secret_key: Optional[str] = Field(None, description="Upbit secret key")
    virtual_mode: bool = Field(True, description="Enable virtual trading mode")
    initial_balance: float = Field(10000, description="Initial balance for virtual mode")
    max_trade_amount: float = Field(1000, description="Maximum trade amount")
    price_threshold: float = Field(0.5, description="Price threshold percentage")
    stop_loss: float = Field(2.0, description="Stop loss percentage")
    take_profit: float = Field(1.0, description="Take profit percentage")
    max_trades_per_day: int = Field(10, description="Maximum trades per day")

class OptimizationRequest(BaseModel):
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    initial_balance: float = Field(10000, description="Initial balance in USD")
    max_trade_amount: float = Field(1000, description="Maximum trade amount")
    threshold_min: float = Field(0.1, description="Minimum threshold to test")
    threshold_max: float = Field(2.0, description="Maximum threshold to test")
    threshold_step: float = Field(0.1, description="Threshold step size")

class BitcoinArbitrageRequest(BaseModel):
    """Request model for Bitcoin arbitrage strategy"""
    entry_premium_threshold: float = Field(0.3, description="Enter position when kimchi premium < this %")
    exit_premium_threshold: float = Field(1.3, description="Exit position when kimchi premium > this %")
    max_position_size_btc: float = Field(0.1, description="Maximum BTC position size")
    tick_offset: int = Field(1, description="Number of ticks for limit orders on Upbit")
    max_open_positions: int = Field(3, description="Maximum simultaneous positions")
    use_market_orders_binance: bool = Field(True, description="Use market orders on Binance")

class BitcoinBacktestRequest(BaseModel):
    """Request model for Bitcoin arbitrage backtesting"""
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    initial_balance_krw: float = Field(13_500_000, description="Initial KRW balance")
    initial_balance_usdt: float = Field(10_000, description="Initial USDT balance")
    entry_premium_threshold: float = Field(0.3, description="Entry threshold %")
    exit_premium_threshold: float = Field(1.3, description="Exit threshold %")
    max_position_size_btc: float = Field(0.1, description="Max BTC per position")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def send_data(self, data: Dict[str, Any]):
        """Send structured data to all connected clients"""
        def json_serializer(obj):
            """Custom JSON serializer for datetime objects"""
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif isinstance(obj, (int, float, str, bool, list, dict, type(None))):
                return obj
            else:
                return str(obj)
        
        try:
            message = json.dumps(data, default=json_serializer)
            await self.broadcast(message)
        except Exception as e:
            logger.error(f"Error serializing data to JSON: {e}")
            # Send error message instead
            error_message = json.dumps({
                "type": "serialization_error",
                "error": str(e)
            })
            await self.broadcast(error_message)

manager = ConnectionManager()

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo received data (can be used for client-server communication)
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# API Routes
@app.get("/")
async def root():
    """Serve the main web interface"""
    return HTMLResponse(content=get_html_content(), status_code=200)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """Run backtest with given parameters"""
    if "backtest" in running_tasks and running_tasks["backtest"]:
        raise HTTPException(status_code=409, detail="Backtest is already running")
    
    background_tasks.add_task(execute_backtest, request)
    return {"status": "started", "message": "Backtest started successfully"}

@app.post("/api/trading/start")
async def start_trading(request: TradingRequest, background_tasks: BackgroundTasks):
    """Start live trading"""
    global bot_instance
    
    if "trading" in running_tasks and running_tasks["trading"]:
        raise HTTPException(status_code=409, detail="Trading is already running")
    
    background_tasks.add_task(execute_trading, request)
    return {"status": "started", "message": "Trading started successfully"}

@app.post("/api/trading/stop")
async def stop_trading():
    """Stop live trading"""
    global bot_instance
    
    if bot_instance:
        try:
            bot_instance.stop_bot()
            bot_instance = None
            running_tasks["trading"] = False
            
            await manager.send_data({
                "type": "trading_stopped",
                "message": "Trading stopped successfully"
            })
            
            return {"status": "stopped", "message": "Trading stopped successfully"}
        except Exception as e:
            logger.error(f"Error stopping trading: {e}")
            raise HTTPException(status_code=500, detail=f"Error stopping trading: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="No trading session is currently active")

@app.get("/api/kimchi-premium")
async def get_kimchi_premium():
    """Get current kimchi premium"""
    global kimchi_calculator
    
    try:
        if not kimchi_calculator:
            kimchi_calculator = KimchiPremiumCalculator()
        
        result = kimchi_calculator.calculate_kimchi_premium()
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting kimchi premium: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting kimchi premium: {str(e)}")

@app.get("/api/bitcoin-kimchi-premium")
async def get_bitcoin_kimchi_premium():
    """Get current Bitcoin kimchi premium"""
    try:
        from upbit_bot.bitcoin_kimchi_strategy import BitcoinKimchiPremiumCalculator
        
        calculator = BitcoinKimchiPremiumCalculator()
        result = calculator.calculate_bitcoin_kimchi_premium()
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Bitcoin kimchi premium: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting Bitcoin kimchi premium: {str(e)}")

@app.post("/api/bitcoin-backtest")
async def run_bitcoin_backtest(request: BitcoinBacktestRequest, background_tasks: BackgroundTasks):
    """Run Bitcoin arbitrage strategy backtest"""
    if "bitcoin_backtest" in running_tasks and running_tasks["bitcoin_backtest"]:
        raise HTTPException(status_code=409, detail="Bitcoin backtest is already running")
    
    background_tasks.add_task(execute_bitcoin_backtest, request)
    return {"status": "started", "message": "Bitcoin arbitrage backtest started"}

@app.post("/api/bitcoin-arbitrage/start")
async def start_bitcoin_arbitrage(request: BitcoinArbitrageRequest):
    """Start Bitcoin arbitrage strategy"""
    if "bitcoin_arbitrage" in running_tasks and running_tasks["bitcoin_arbitrage"]:
        raise HTTPException(status_code=409, detail="Bitcoin arbitrage is already running")
    
    try:
        from upbit_bot.bitcoin_kimchi_strategy import BitcoinArbitrageConfig, BitcoinArbitrageStrategy
        
        config = BitcoinArbitrageConfig(
            entry_premium_threshold=request.entry_premium_threshold,
            exit_premium_threshold=request.exit_premium_threshold,
            max_position_size_btc=request.max_position_size_btc,
            tick_offset=request.tick_offset,
            max_open_positions=request.max_open_positions,
            use_market_orders_binance=request.use_market_orders_binance
        )
        
        # Store strategy instance globally if needed
        global bitcoin_strategy
        bitcoin_strategy = BitcoinArbitrageStrategy(config)
        
        running_tasks["bitcoin_arbitrage"] = True
        
        return {
            "status": "started",
            "message": "Bitcoin arbitrage strategy started",
            "config": {
                "entry_threshold": config.entry_premium_threshold,
                "exit_threshold": config.exit_premium_threshold,
                "max_position_size": config.max_position_size_btc
            }
        }
    except Exception as e:
        logger.error(f"Error starting Bitcoin arbitrage: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting Bitcoin arbitrage: {str(e)}")

@app.get("/api/bitcoin-arbitrage/status")
async def get_bitcoin_arbitrage_status():
    """Get Bitcoin arbitrage strategy status"""
    try:
        if "bitcoin_strategy" not in globals() or not bitcoin_strategy:
            return {
                "status": "inactive",
                "message": "Bitcoin arbitrage strategy is not running"
            }
        
        status = bitcoin_strategy.get_strategy_status()
        return {
            "status": "active",
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Bitcoin arbitrage status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting Bitcoin arbitrage status: {str(e)}")

@app.post("/api/optimize")
async def optimize_parameters(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """Optimize trading parameters"""
    if "optimization" in running_tasks and running_tasks["optimization"]:
        raise HTTPException(status_code=409, detail="Optimization is already running")
    
    background_tasks.add_task(execute_optimization, request)
    return {"status": "started", "message": "Parameter optimization started"}

@app.get("/api/status")
async def get_status():
    """Get current system status"""
    return {
        "running_tasks": running_tasks,
        "active_connections": len(manager.active_connections),
        "bot_active": bot_instance is not None,
        "timestamp": datetime.now().isoformat()
    }

# Background task functions
async def execute_backtest(request: BacktestRequest):
    """Execute backtest in background"""
    running_tasks["backtest"] = True
    
    try:
        logger.info("Starting backtest execution")
        
        await manager.send_data({
            "type": "backtest_started",
            "message": "Backtest started"
        })
        
        # Parse dates
        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        # Create configuration with error handling
        try:
            config = BacktestConfig(
                initial_balance_usd=float(request.initial_balance),
                max_trade_amount=float(request.max_trade_amount),
                price_threshold=float(request.price_threshold),
                buy_threshold=float(request.buy_threshold),
                sell_threshold=float(request.sell_threshold),
                stop_loss_threshold=float(request.stop_loss),
                take_profit_threshold=float(request.take_profit),
                max_trades_per_day=int(request.max_trades_per_day)
            )
            logger.info(f"Backtest config created: initial_balance_usd={config.initial_balance_usd}, buy_threshold={config.buy_threshold}, sell_threshold={config.sell_threshold}")
        except Exception as e:
            logger.error(f"Error creating BacktestConfig: {e}")
            await manager.send_data({
                "type": "backtest_error",
                "error": f"Configuration error: {str(e)}"
            })
            return
        
        # Create debug configuration
        debug_config = {
            'debug_mode': request.debug_mode,
            'verbose_debug': request.verbose_debug,
            'show_signals': request.show_signals
        }
        
        # Create a simple queue-like system for WebSocket updates
        class WebSocketQueue:
            def __init__(self, manager):
                self.manager = manager
                self.pending_tasks = []
                
            def put(self, item):
                task = asyncio.create_task(self.manager.send_data({
                    "type": "backtest_update",
                    "data": item
                }))
                self.pending_tasks.append(task)
                
            async def wait_for_pending(self):
                if self.pending_tasks:
                    await asyncio.gather(*self.pending_tasks)
        
        ws_queue = WebSocketQueue(manager)
        
        # Create backtest instance
        backtest = DebugUpbitBacktest(config, debug_config, ws_queue)
        
        # Run backtest with progress tracking
        await manager.send_data({
            "type": "backtest_progress",
            "progress": 30,
            "message": "Running backtest simulation..."
        })
        
        # Create a progress-aware backtest wrapper
        async def run_with_progress():
            # Store original calculate_signal method
            original_calculate_signal = backtest.strategy.calculate_signal
            total_days = (end_dt - start_dt).days
            current_day = 0
            
            def progress_aware_calculate_signal(data):
                nonlocal current_day
                current_day += 1
                if current_day % max(1, total_days // 20) == 0:  # Update every 5%
                    progress = 30 + int((current_day / total_days) * 60)  # 30-90%
                    asyncio.create_task(manager.send_data({
                        "type": "backtest_progress",
                        "progress": min(90, progress),
                        "message": f"Processing day {current_day}/{total_days}..."
                    }))
                return original_calculate_signal(data)
            
            # Replace with progress-aware version
            backtest.strategy.calculate_signal = progress_aware_calculate_signal
            
            # Run the backtest with real data as requested
            result = backtest.run_backtest(start_dt, end_dt, use_real_data=request.use_real_data)
            
            # Restore original method
            backtest.strategy.calculate_signal = original_calculate_signal
            
            return result
        
        result = await run_with_progress()
        
        # Wait for any pending WebSocket messages
        await ws_queue.wait_for_pending()
        
        # Send completion progress
        await manager.send_data({
            "type": "backtest_progress",
            "progress": 100,
            "message": "Backtest completed!"
        })
        
        # Send results
        logger.info(f"Sending backtest results via WebSocket: return={result.return_percentage:.2f}%, trades={result.total_trades}")
        
        # Ensure we have active connections
        if not manager.active_connections:
            logger.error("No active WebSocket connections to send results to!")
        
        await manager.send_data({
            "type": "backtest_complete",
            "data": {
                "initial_balance": float(result.initial_balance),
                "final_balance": float(result.final_balance),
                "total_return": float(result.total_return),
                "return_percentage": float(result.return_percentage),
                "max_drawdown": float(result.max_drawdown),
                "sharpe_ratio": float(result.sharpe_ratio),
                "win_rate": float(result.win_rate),
                "profit_factor": float(result.profit_factor),
                "total_trades": int(result.total_trades),
                "winning_trades": int(result.winning_trades),
                "losing_trades": int(result.losing_trades),
                "average_win": float(result.average_win),
                "average_loss": float(result.average_loss),
                "trades": [
                    {
                        "timestamp": trade.timestamp if isinstance(trade.timestamp, str) else trade.timestamp.isoformat() if hasattr(trade.timestamp, 'isoformat') else str(trade.timestamp),
                        "action": trade.action,
                        "amount_usd": float(trade.amount_usd),
                        "usdt_krw_price": float(trade.usdt_krw_price),
                        "usd_krw_rate": float(trade.usd_krw_rate),
                        "difference_percentage": float(trade.difference_percentage),
                        "success": bool(trade.success),
                        "profit_loss": float(trade.profit_loss)
                    }
                    for trade in result.trades[-10:]  # Last 10 trades
                ]
            }
        })
        
        logger.info("Backtest results sent successfully")
        
        # Small delay to ensure messages are sent
        await asyncio.sleep(0.5)
        
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        await manager.send_data({
            "type": "backtest_error",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        running_tasks["backtest"] = False

async def execute_trading(request: TradingRequest):
    """Execute trading in background"""
    global bot_instance
    running_tasks["trading"] = True
    
    try:
        await manager.send_data({
            "type": "trading_started",
            "message": "Trading started"
        })
        
        # Create trading configuration
        config = TradingConfig(
            max_trade_amount=request.max_trade_amount,
            price_threshold=request.price_threshold,
            stop_loss_threshold=request.stop_loss,
            take_profit_threshold=request.take_profit,
            max_trades_per_day=request.max_trades_per_day,
            max_daily_loss=request.max_trade_amount * 5,
            emergency_stop_loss=5.0
        )
        
        # Create bot instance
        if request.virtual_mode:
            bot_instance = UpbitTradingBot(
                virtual_mode=True,
                initial_balance_usd=request.initial_balance,
                config=config
            )
        else:
            if not request.api_key or not request.secret_key:
                raise ValueError("API keys required for live trading")
            
            bot_instance = UpbitTradingBot(
                api_key=request.api_key,
                secret_key=request.secret_key,
                virtual_mode=False,
                config=config
            )
        
        # Run trading bot
        await asyncio.create_task(run_trading_bot(bot_instance))
        
    except Exception as e:
        logger.error(f"Trading error: {e}")
        await manager.send_data({
            "type": "trading_error",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        running_tasks["trading"] = False

async def run_trading_bot(bot: UpbitTradingBot):
    """Run trading bot with WebSocket updates"""
    try:
        # This would need to be adapted based on your trading bot implementation
        # For now, we'll simulate trading activity
        while running_tasks.get("trading", False):
            await asyncio.sleep(60)  # Check every minute
            
            # Send status update
            await manager.send_data({
                "type": "trading_status",
                "message": f"Bot is running - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            })
            
    except Exception as e:
        logger.error(f"Trading bot error: {e}")
        await manager.send_data({
            "type": "trading_error",
            "error": str(e)
        })

async def execute_optimization(request: OptimizationRequest):
    """Execute parameter optimization in background"""
    running_tasks["optimization"] = True
    
    try:
        await manager.send_data({
            "type": "optimization_started",
            "message": "Parameter optimization started"
        })
        
        # Parse dates
        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        # Generate parameter combinations
        import numpy as np
        thresholds = np.arange(request.threshold_min, request.threshold_max + request.threshold_step, request.threshold_step)
        
        results = []
        best_return = float('-inf')
        best_params = None
        
        total_combinations = len(thresholds)
        
        for i, threshold in enumerate(thresholds):
            try:
                # Create configuration
                config = BacktestConfig(
                    initial_balance_usd=float(request.initial_balance),
                    max_trade_amount=float(request.max_trade_amount),
                    price_threshold=float(threshold),
                    stop_loss_threshold=2.0,
                    take_profit_threshold=1.0,
                    max_trades_per_day=10
                )
                
                # Run backtest
                backtest = EnhancedUpbitBacktest(config)
                result = backtest.run_backtest(start_dt, end_dt, use_real_data=False)
                
                # Store result
                result_data = {
                    "threshold": float(threshold),
                    "return_pct": float(result.return_percentage),
                    "max_drawdown": float(result.max_drawdown),
                    "trades": int(result.total_trades),
                    "win_rate": float(result.win_rate)
                }
                results.append(result_data)
                
                if result.return_percentage > best_return:
                    best_return = result.return_percentage
                    best_params = result_data
                
                # Send progress update
                progress = ((i + 1) / total_combinations) * 100
                await manager.send_data({
                    "type": "optimization_progress",
                    "progress": progress,
                    "message": f"Testing threshold {threshold:.2f}% - {i+1}/{total_combinations}"
                })
                
            except Exception as e:
                logger.error(f"Optimization error for threshold {threshold}: {e}")
                continue
        
        # Send results
        await manager.send_data({
            "type": "optimization_complete",
            "data": {
                "best_params": best_params,
                "all_results": results
            }
        })
        
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        await manager.send_data({
            "type": "optimization_error",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        running_tasks["optimization"] = False

async def execute_bitcoin_backtest(request: BitcoinBacktestRequest):
    """Execute Bitcoin arbitrage backtest in background"""
    running_tasks["bitcoin_backtest"] = True
    
    try:
        logger.info("Starting Bitcoin arbitrage backtest")
        
        await manager.send_data({
            "type": "bitcoin_backtest_started",
            "message": "Bitcoin arbitrage backtest started"
        })
        
        from upbit_bot.bitcoin_backtest import BitcoinBacktestConfig, BitcoinBacktester
        
        # Create configuration
        config = BitcoinBacktestConfig(
            initial_balance_krw=request.initial_balance_krw,
            initial_balance_usdt=request.initial_balance_usdt,
            entry_premium_threshold=request.entry_premium_threshold,
            exit_premium_threshold=request.exit_premium_threshold,
            max_position_size_btc=request.max_position_size_btc
        )
        
        # Create and run backtest
        backtester = BitcoinBacktester(config)
        
        # Send progress updates
        await manager.send_data({
            "type": "bitcoin_backtest_progress",
            "progress": 20,
            "message": "Fetching historical data..."
        })
        
        result = backtester.run_backtest(request.start_date, request.end_date)
        
        # Send completion
        await manager.send_data({
            "type": "bitcoin_backtest_complete",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Bitcoin backtest error: {e}")
        await manager.send_data({
            "type": "bitcoin_backtest_error",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        running_tasks["bitcoin_backtest"] = False

def get_html_content():
    """Return the HTML content for the web interface"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upbit Trading Bot</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            
            .header h1 {
                color: #2c3e50;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            
            .status-bar {
                background: rgba(255, 255, 255, 0.9);
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
            }
            
            .status-item {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .status-dot {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #27ae60;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
            
            .tabs {
                display: flex;
                background: rgba(255, 255, 255, 0.9);
                border-radius: 10px;
                padding: 5px;
                margin-bottom: 20px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
            }
            
            .tab {
                flex: 1;
                padding: 15px;
                text-align: center;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-weight: 500;
            }
            
            .tab.active {
                background: #3498db;
                color: white;
                box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
            }
            
            .tab:hover:not(.active) {
                background: rgba(52, 152, 219, 0.1);
            }
            
            .tab-content {
                display: none;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                backdrop-filter: blur(10px);
            }
            
            .tab-content.active {
                display: block;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-row {
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
            }
            
            .form-row .form-group {
                flex: 1;
                margin-bottom: 0;
            }
            
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: 500;
                color: #2c3e50;
            }
            
            input, select, textarea {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s ease;
            }
            
            input:focus, select:focus, textarea:focus {
                outline: none;
                border-color: #3498db;
                box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
            }
            
            button {
                background: linear-gradient(45deg, #3498db, #2980b9);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                transition: all 0.3s ease;
                box-shadow: 0 4px 16px rgba(52, 152, 219, 0.3);
            }
            
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(52, 152, 219, 0.4);
            }
            
            button:active {
                transform: translateY(0);
            }
            
            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .btn-danger {
                background: linear-gradient(45deg, #e74c3c, #c0392b);
                box-shadow: 0 4px 16px rgba(231, 76, 60, 0.3);
            }
            
            .btn-danger:hover {
                box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
            }
            
            .btn-success {
                background: linear-gradient(45deg, #27ae60, #229954);
                box-shadow: 0 4px 16px rgba(39, 174, 96, 0.3);
            }
            
            .btn-success:hover {
                box-shadow: 0 6px 20px rgba(39, 174, 96, 0.4);
            }
            
            .progress-bar {
                width: 100%;
                height: 20px;
                background: #ecf0f1;
                border-radius: 10px;
                overflow: hidden;
                margin: 15px 0;
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #3498db, #2980b9);
                width: 0%;
                transition: width 0.3s ease;
                border-radius: 10px;
            }
            
            .results {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
                border-left: 4px solid #3498db;
            }
            
            .results h3 {
                color: #2c3e50;
                margin-bottom: 15px;
            }
            
            .result-item {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .result-item:last-child {
                border-bottom: none;
            }
            
            .result-label {
                font-weight: 500;
                color: #555;
            }
            
            .result-value {
                font-weight: 600;
                color: #2c3e50;
            }
            
            .logs {
                background: #2c3e50;
                color: #ecf0f1;
                padding: 20px;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                max-height: 400px;
                overflow-y: auto;
                margin-top: 20px;
            }
            
            .log-entry {
                margin-bottom: 5px;
                padding: 5px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .log-timestamp {
                color: #3498db;
                font-weight: 500;
            }
            
            .log-error {
                color: #e74c3c;
            }
            
            .log-success {
                color: #27ae60;
            }
            
            .log-warning {
                color: #f39c12;
            }
            
            .checkbox-group {
                display: flex;
                gap: 20px;
                margin-top: 10px;
            }
            
            .checkbox-item {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .checkbox-item input[type="checkbox"] {
                width: auto;
            }
            
            .hidden {
                display: none;
            }
            
            @media (max-width: 768px) {
                .form-row {
                    flex-direction: column;
                    gap: 0;
                }
                
                .tabs {
                    flex-direction: column;
                }
                
                .status-bar {
                    flex-direction: column;
                    gap: 10px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Upbit Trading Bot</h1>
                <p>Modern Web Interface for Cryptocurrency Trading</p>
            </div>
            
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-dot" id="connectionStatus"></div>
                    <span id="connectionText">Connecting...</span>
                </div>
                <div class="status-item">
                    <span id="kimchiPremium">Kimchi Premium: Loading...</span>
                </div>
                <div class="status-item">
                    <span id="currentTime"></span>
                </div>
            </div>
            
            <div class="tabs">
                <div class="tab active" onclick="showTab('backtest')">📊 Backtest</div>
                <div class="tab" onclick="showTab('trading')">💰 Trading</div>
                <div class="tab" onclick="showTab('optimization')">🔧 Optimization</div>
                <div class="tab" onclick="showTab('monitor')">📈 Monitor</div>
            </div>
            
            <!-- Backtest Tab -->
            <div id="backtest" class="tab-content active">
                <h2>📊 Backtest Configuration</h2>
                <form id="backtestForm">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="startDate">Start Date:</label>
                            <input type="date" id="startDate" name="startDate" required>
                        </div>
                        <div class="form-group">
                            <label for="endDate">End Date:</label>
                            <input type="date" id="endDate" name="endDate" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="initialBalance">Initial Balance (USD):</label>
                            <input type="number" id="initialBalance" name="initialBalance" value="10000" step="100" required>
                        </div>
                        <div class="form-group">
                            <label for="maxTradeAmount">Max Trade Amount (USD):</label>
                            <input type="number" id="maxTradeAmount" name="maxTradeAmount" value="1000" step="100" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="buyThreshold">Buy Threshold (%):</label>
                            <input type="number" id="buyThreshold" name="buyThreshold" value="0.3" min="-5" max="5" step="0.1" required>
                            <small style="color: #666;">Buy when kimchi premium is below this value</small>
                        </div>
                        <div class="form-group">
                            <label for="sellThreshold">Sell Threshold (%):</label>
                            <input type="number" id="sellThreshold" name="sellThreshold" value="2.0" min="0" max="10" step="0.1" required>
                            <small style="color: #666;">Sell when kimchi premium is above this value</small>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="priceThreshold">Price Threshold (%) [Legacy]:</label>
                            <input type="number" id="priceThreshold" name="priceThreshold" value="0.5" step="0.1" required>
                        </div>
                        <div class="form-group">
                            <label for="stopLoss">Stop Loss (%):</label>
                            <input type="number" id="stopLoss" name="stopLoss" value="2.0" step="0.1" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="takeProfit">Take Profit (%):</label>
                            <input type="number" id="takeProfit" name="takeProfit" value="1.0" step="0.1" required>
                        </div>
                        <div class="form-group">
                            <label for="maxTradesPerDay">Max Trades Per Day:</label>
                            <input type="number" id="maxTradesPerDay" name="maxTradesPerDay" value="10" step="1" required>
                        </div>
                    </div>
                    
                    <div class="checkbox-group">
                        <div class="checkbox-item">
                            <input type="checkbox" id="useRealData" name="useRealData" checked>
                            <label for="useRealData">Use Real Data</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="debugMode" name="debugMode">
                            <label for="debugMode">Debug Mode</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="verboseDebug" name="verboseDebug">
                            <label for="verboseDebug">Verbose Debug</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="showSignals" name="showSignals">
                            <label for="showSignals">Show Signals</label>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn-success">🚀 Run Backtest</button>
                </form>
                
                <div id="backtestProgress" class="hidden">
                    <div class="progress-bar">
                        <div class="progress-fill" id="backtestProgressFill"></div>
                    </div>
                    <p id="backtestProgressText">Preparing backtest...</p>
                </div>
                
                <div id="backtestResults" class="results hidden">
                    <h3>📊 Backtest Results</h3>
                    <div id="backtestResultsContent"></div>
                </div>
            </div>
            
            <!-- Trading Tab -->
            <div id="trading" class="tab-content">
                <h2>💰 Live Trading</h2>
                <form id="tradingForm">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="apiKey">API Key (optional for virtual mode):</label>
                            <input type="password" id="apiKey" name="apiKey" placeholder="Enter your Upbit API key">
                        </div>
                        <div class="form-group">
                            <label for="secretKey">Secret Key (optional for virtual mode):</label>
                            <input type="password" id="secretKey" name="secretKey" placeholder="Enter your Upbit secret key">
                        </div>
                    </div>
                    
                    <div class="checkbox-group">
                        <div class="checkbox-item">
                            <input type="checkbox" id="virtualMode" name="virtualMode" checked>
                            <label for="virtualMode">Virtual Mode (Paper Trading)</label>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="tradingInitialBalance">Initial Balance (USD):</label>
                            <input type="number" id="tradingInitialBalance" name="tradingInitialBalance" value="10000" step="100" required>
                        </div>
                        <div class="form-group">
                            <label for="tradingMaxTradeAmount">Max Trade Amount (USD):</label>
                            <input type="number" id="tradingMaxTradeAmount" name="tradingMaxTradeAmount" value="1000" step="100" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="tradingPriceThreshold">Price Threshold (%):</label>
                            <input type="number" id="tradingPriceThreshold" name="tradingPriceThreshold" value="0.5" step="0.1" required>
                        </div>
                        <div class="form-group">
                            <label for="tradingStopLoss">Stop Loss (%):</label>
                            <input type="number" id="tradingStopLoss" name="tradingStopLoss" value="2.0" step="0.1" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="tradingTakeProfit">Take Profit (%):</label>
                            <input type="number" id="tradingTakeProfit" name="tradingTakeProfit" value="1.0" step="0.1" required>
                        </div>
                        <div class="form-group">
                            <label for="tradingMaxTradesPerDay">Max Trades Per Day:</label>
                            <input type="number" id="tradingMaxTradesPerDay" name="tradingMaxTradesPerDay" value="10" step="1" required>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 10px;">
                        <button type="submit" class="btn-success">▶️ Start Trading</button>
                        <button type="button" class="btn-danger" onclick="stopTrading()">⏹️ Stop Trading</button>
                    </div>
                </form>
                
                <div id="tradingStatus" class="results hidden">
                    <h3>💰 Trading Status</h3>
                    <div id="tradingStatusContent"></div>
                </div>
            </div>
            
            <!-- Optimization Tab -->
            <div id="optimization" class="tab-content">
                <h2>🔧 Parameter Optimization</h2>
                <form id="optimizationForm">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="optStartDate">Start Date:</label>
                            <input type="date" id="optStartDate" name="optStartDate" required>
                        </div>
                        <div class="form-group">
                            <label for="optEndDate">End Date:</label>
                            <input type="date" id="optEndDate" name="optEndDate" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="optInitialBalance">Initial Balance (USD):</label>
                            <input type="number" id="optInitialBalance" name="optInitialBalance" value="10000" step="100" required>
                        </div>
                        <div class="form-group">
                            <label for="optMaxTradeAmount">Max Trade Amount (USD):</label>
                            <input type="number" id="optMaxTradeAmount" name="optMaxTradeAmount" value="1000" step="100" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="thresholdMin">Threshold Min (%):</label>
                            <input type="number" id="thresholdMin" name="thresholdMin" value="0.1" step="0.1" required>
                        </div>
                        <div class="form-group">
                            <label for="thresholdMax">Threshold Max (%):</label>
                            <input type="number" id="thresholdMax" name="thresholdMax" value="2.0" step="0.1" required>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="thresholdStep">Threshold Step (%):</label>
                        <input type="number" id="thresholdStep" name="thresholdStep" value="0.1" step="0.1" required>
                    </div>
                    
                    <button type="submit" class="btn-success">🔧 Start Optimization</button>
                </form>
                
                <div id="optimizationProgress" class="hidden">
                    <div class="progress-bar">
                        <div class="progress-fill" id="optimizationProgressFill"></div>
                    </div>
                    <p id="optimizationProgressText">Preparing optimization...</p>
                </div>
                
                <div id="optimizationResults" class="results hidden">
                    <h3>🔧 Optimization Results</h3>
                    <div id="optimizationResultsContent"></div>
                </div>
            </div>
            
            <!-- Monitor Tab -->
            <div id="monitor" class="tab-content">
                <h2>📈 Live Monitor</h2>
                <div id="monitorContent">
                    <div class="results">
                        <h3>🔍 System Status</h3>
                        <div id="systemStatus"></div>
                    </div>
                    
                    <div class="logs">
                        <h3 style="color: #ecf0f1; margin-bottom: 15px;">📋 Activity Logs</h3>
                        <div id="activityLogs"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let ws;
            let isConnected = false;
            
            // Initialize
            document.addEventListener('DOMContentLoaded', function() {
                initializeWebSocket();
                updateCurrentTime();
                setInterval(updateCurrentTime, 1000);
                setInterval(updateKimchiPremium, 30000); // Update every 30 seconds
                
                // Set default dates
                const today = new Date();
                const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());
                const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
                
                document.getElementById('startDate').value = lastMonth.toISOString().split('T')[0];
                document.getElementById('endDate').value = yesterday.toISOString().split('T')[0];
                document.getElementById('optStartDate').value = lastMonth.toISOString().split('T')[0];
                document.getElementById('optEndDate').value = yesterday.toISOString().split('T')[0];
                
                // Form event listeners
                document.getElementById('backtestForm').addEventListener('submit', runBacktest);
                document.getElementById('tradingForm').addEventListener('submit', startTrading);
                document.getElementById('optimizationForm').addEventListener('submit', runOptimization);
                
                // Initial data fetch
                updateKimchiPremium();
                updateSystemStatus();
            });
            
            function initializeWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() {
                    isConnected = true;
                    updateConnectionStatus('Connected', 'success');
                    addLog('Connected to server', 'success');
                };
                
                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        handleWebSocketMessage(data);
                    } catch (e) {
                        addLog(`Received: ${event.data}`, 'info');
                    }
                };
                
                ws.onclose = function() {
                    isConnected = false;
                    updateConnectionStatus('Disconnected', 'error');
                    addLog('Disconnected from server', 'error');
                    
                    // Reconnect after 3 seconds
                    setTimeout(initializeWebSocket, 3000);
                };
                
                ws.onerror = function(error) {
                    addLog(`WebSocket error: ${error}`, 'error');
                };
            }
            
            function handleWebSocketMessage(data) {
                console.log('Received WebSocket message:', data);
                
                switch(data.type) {
                    case 'backtest_started':
                        showElement('backtestProgress');
                        updateProgress('backtestProgressFill', 'backtestProgressText', 10, 'Starting backtest...');
                        addLog('Backtest started', 'info');
                        break;
                        
                    case 'backtest_progress':
                        updateProgress('backtestProgressFill', 'backtestProgressText', data.progress, data.message);
                        addLog(`Backtest progress: ${data.message}`, 'info');
                        break;
                        
                    case 'backtest_complete':
                        console.log('Backtest complete data:', data.data);
                        hideElement('backtestProgress');
                        displayBacktestResults(data.data);
                        addLog('Backtest completed successfully', 'success');
                        break;
                        
                    case 'backtest_error':
                        hideElement('backtestProgress');
                        addLog(`Backtest error: ${data.error}`, 'error');
                        alert(`Backtest failed: ${data.error}`);
                        break;
                        
                    case 'trading_started':
                        showElement('tradingStatus');
                        updateTradingStatus('Trading started successfully');
                        addLog('Live trading started', 'success');
                        break;
                        
                    case 'trading_status':
                        updateTradingStatus(data.message);
                        addLog(`Trading status: ${data.message}`, 'info');
                        break;
                        
                    case 'trading_stopped':
                        hideElement('tradingStatus');
                        addLog('Trading stopped', 'warning');
                        break;
                        
                    case 'trading_error':
                        addLog(`Trading error: ${data.error}`, 'error');
                        alert(`Trading error: ${data.error}`);
                        break;
                        
                    case 'optimization_started':
                        showElement('optimizationProgress');
                        updateProgress('optimizationProgressFill', 'optimizationProgressText', 5, 'Starting optimization...');
                        addLog('Parameter optimization started', 'info');
                        break;
                        
                    case 'optimization_progress':
                        updateProgress('optimizationProgressFill', 'optimizationProgressText', data.progress, data.message);
                        addLog(`Optimization progress: ${data.message}`, 'info');
                        break;
                        
                    case 'optimization_complete':
                        hideElement('optimizationProgress');
                        displayOptimizationResults(data.data);
                        addLog('Parameter optimization completed', 'success');
                        break;
                        
                    case 'optimization_error':
                        hideElement('optimizationProgress');
                        addLog(`Optimization error: ${data.error}`, 'error');
                        alert(`Optimization failed: ${data.error}`);
                        break;
                        
                    case 'backtest_update':
                        if (data.data[0] === 'trade_alert') {
                            const [, tradeData] = data.data;
                            const [action, amount, price, reason] = tradeData;
                            addLog(`Trade: ${action} $${amount.toFixed(2)} at ${price.toFixed(0)} KRW - ${reason}`, 'success');
                        } else if (data.data[0] === 'debug_info') {
                            addLog(`Debug: ${data.data[1]}`, 'warning');
                        }
                        break;
                        
                    default:
                        addLog(`Unknown message type: ${data.type}`, 'warning');
                }
            }
            
            function showTab(tabName) {
                // Hide all tab contents
                const tabContents = document.querySelectorAll('.tab-content');
                tabContents.forEach(content => content.classList.remove('active'));
                
                // Remove active class from all tabs
                const tabs = document.querySelectorAll('.tab');
                tabs.forEach(tab => tab.classList.remove('active'));
                
                // Show selected tab content
                document.getElementById(tabName).classList.add('active');
                
                // Add active class to selected tab
                event.target.classList.add('active');
            }
            
            function updateCurrentTime() {
                const now = new Date();
                document.getElementById('currentTime').textContent = now.toLocaleString();
            }
            
            function updateConnectionStatus(status, type) {
                const statusDot = document.getElementById('connectionStatus');
                const statusText = document.getElementById('connectionText');
                
                statusText.textContent = status;
                
                if (type === 'success') {
                    statusDot.style.background = '#27ae60';
                } else if (type === 'error') {
                    statusDot.style.background = '#e74c3c';
                } else {
                    statusDot.style.background = '#f39c12';
                }
            }
            
            async function updateKimchiPremium() {
                try {
                    const response = await fetch('/api/kimchi-premium');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        const premium = data.data.kimchi_premium_percentage;
                        const upbitPrice = data.data.upbit_usdt_krw;
                        const binancePrice = data.data.binance_usdt_krw;
                        
                        document.getElementById('kimchiPremium').textContent = 
                            `Kimchi Premium: ${premium.toFixed(2)}% | Upbit: ${upbitPrice.toFixed(0)} | Binance: ${binancePrice.toFixed(0)}`;
                    } else {
                        document.getElementById('kimchiPremium').textContent = 'Kimchi Premium: Error loading';
                    }
                } catch (error) {
                    document.getElementById('kimchiPremium').textContent = 'Kimchi Premium: Connection error';
                }
            }
            
            async function updateSystemStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    const statusHtml = `
                        <div class="result-item">
                            <span class="result-label">Active Connections:</span>
                            <span class="result-value">${data.active_connections}</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Bot Active:</span>
                            <span class="result-value">${data.bot_active ? 'Yes' : 'No'}</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Running Tasks:</span>
                            <span class="result-value">${Object.keys(data.running_tasks).filter(key => data.running_tasks[key]).join(', ') || 'None'}</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Last Update:</span>
                            <span class="result-value">${new Date(data.timestamp).toLocaleString()}</span>
                        </div>
                    `;
                    
                    document.getElementById('systemStatus').innerHTML = statusHtml;
                } catch (error) {
                    document.getElementById('systemStatus').innerHTML = '<p>Error loading system status</p>';
                }
            }
            
            function showElement(elementId) {
                document.getElementById(elementId).classList.remove('hidden');
            }
            
            function hideElement(elementId) {
                document.getElementById(elementId).classList.add('hidden');
            }
            
            function updateProgress(fillId, textId, progress, message) {
                document.getElementById(fillId).style.width = `${progress}%`;
                document.getElementById(textId).textContent = message;
            }
            
            function addLog(message, type = 'info') {
                const logsContainer = document.getElementById('activityLogs');
                const timestamp = new Date().toLocaleTimeString();
                
                const logEntry = document.createElement('div');
                logEntry.className = `log-entry log-${type}`;
                logEntry.innerHTML = `
                    <span class="log-timestamp">[${timestamp}]</span>
                    <span>${message}</span>
                `;
                
                logsContainer.appendChild(logEntry);
                logsContainer.scrollTop = logsContainer.scrollHeight;
                
                // Keep only last 100 log entries
                while (logsContainer.children.length > 100) {
                    logsContainer.removeChild(logsContainer.firstChild);
                }
            }
            
            async function runBacktest(event) {
                event.preventDefault();
                
                const formData = new FormData(event.target);
                const request = {
                    start_date: formData.get('startDate'),
                    end_date: formData.get('endDate'),
                    initial_balance: parseFloat(formData.get('initialBalance')),
                    max_trade_amount: parseFloat(formData.get('maxTradeAmount')),
                    price_threshold: parseFloat(formData.get('priceThreshold')),
                    buy_threshold: parseFloat(formData.get('buyThreshold')),
                    sell_threshold: parseFloat(formData.get('sellThreshold')),
                    stop_loss: parseFloat(formData.get('stopLoss')),
                    take_profit: parseFloat(formData.get('takeProfit')),
                    max_trades_per_day: parseInt(formData.get('maxTradesPerDay')),
                    use_real_data: formData.get('useRealData') === 'on',
                    debug_mode: formData.get('debugMode') === 'on',
                    verbose_debug: formData.get('verboseDebug') === 'on',
                    show_signals: formData.get('showSignals') === 'on'
                };
                
                try {
                    const response = await fetch('/api/backtest', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(request)
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        addLog('Backtest request submitted successfully', 'success');
                    } else {
                        addLog(`Backtest request failed: ${data.detail}`, 'error');
                        alert(`Error: ${data.detail}`);
                    }
                } catch (error) {
                    addLog(`Network error: ${error.message}`, 'error');
                    alert(`Network error: ${error.message}`);
                }
            }
            
            async function startTrading(event) {
                event.preventDefault();
                
                const formData = new FormData(event.target);
                const request = {
                    api_key: formData.get('apiKey') || null,
                    secret_key: formData.get('secretKey') || null,
                    virtual_mode: formData.get('virtualMode') === 'on',
                    initial_balance: parseFloat(formData.get('tradingInitialBalance')),
                    max_trade_amount: parseFloat(formData.get('tradingMaxTradeAmount')),
                    price_threshold: parseFloat(formData.get('tradingPriceThreshold')),
                    stop_loss: parseFloat(formData.get('tradingStopLoss')),
                    take_profit: parseFloat(formData.get('tradingTakeProfit')),
                    max_trades_per_day: parseInt(formData.get('tradingMaxTradesPerDay'))
                };
                
                try {
                    const response = await fetch('/api/trading/start', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(request)
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        addLog('Trading started successfully', 'success');
                    } else {
                        addLog(`Trading start failed: ${data.detail}`, 'error');
                        alert(`Error: ${data.detail}`);
                    }
                } catch (error) {
                    addLog(`Network error: ${error.message}`, 'error');
                    alert(`Network error: ${error.message}`);
                }
            }
            
            async function stopTrading() {
                try {
                    const response = await fetch('/api/trading/stop', {
                        method: 'POST'
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        addLog('Trading stopped successfully', 'success');
                    } else {
                        addLog(`Trading stop failed: ${data.detail}`, 'error');
                        alert(`Error: ${data.detail}`);
                    }
                } catch (error) {
                    addLog(`Network error: ${error.message}`, 'error');
                    alert(`Network error: ${error.message}`);
                }
            }
            
            async function runOptimization(event) {
                event.preventDefault();
                
                const formData = new FormData(event.target);
                const request = {
                    start_date: formData.get('optStartDate'),
                    end_date: formData.get('optEndDate'),
                    initial_balance: parseFloat(formData.get('optInitialBalance')),
                    max_trade_amount: parseFloat(formData.get('optMaxTradeAmount')),
                    threshold_min: parseFloat(formData.get('thresholdMin')),
                    threshold_max: parseFloat(formData.get('thresholdMax')),
                    threshold_step: parseFloat(formData.get('thresholdStep'))
                };
                
                try {
                    const response = await fetch('/api/optimize', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(request)
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        addLog('Optimization started successfully', 'success');
                    } else {
                        addLog(`Optimization start failed: ${data.detail}`, 'error');
                        alert(`Error: ${data.detail}`);
                    }
                } catch (error) {
                    addLog(`Network error: ${error.message}`, 'error');
                    alert(`Network error: ${error.message}`);
                }
            }
            
            function displayBacktestResults(data) {
                // Performance color coding
                const returnColor = data.return_percentage >= 0 ? '#27ae60' : '#e74c3c';
                const winRateColor = data.win_rate >= 50 ? '#27ae60' : '#e74c3c';
                
                let resultsHtml = `
                    <h3>📊 Backtest Performance Summary</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                            <h4 style="color: #2c3e50; margin-bottom: 10px;">💰 Financial Results</h4>
                            <div class="result-item">
                                <span class="result-label">Initial Balance:</span>
                                <span class="result-value">$${data.initial_balance.toLocaleString()}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Final Balance:</span>
                                <span class="result-value">$${data.final_balance.toLocaleString()}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Total Return:</span>
                                <span class="result-value" style="color: ${returnColor}">$${data.total_return.toLocaleString()}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Return Percentage:</span>
                                <span class="result-value" style="color: ${returnColor}; font-weight: bold">${data.return_percentage.toFixed(2)}%</span>
                            </div>
                        </div>
                        
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                            <h4 style="color: #2c3e50; margin-bottom: 10px;">📈 Risk Metrics</h4>
                            <div class="result-item">
                                <span class="result-label">Max Drawdown:</span>
                                <span class="result-value">${data.max_drawdown.toFixed(2)}%</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Sharpe Ratio:</span>
                                <span class="result-value">${data.sharpe_ratio.toFixed(2)}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Profit Factor:</span>
                                <span class="result-value">${data.profit_factor.toFixed(2)}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Risk/Reward:</span>
                                <span class="result-value">${data.max_drawdown > 0 ? (Math.abs(data.return_percentage) / data.max_drawdown).toFixed(2) : 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                        <h4 style="color: #2c3e50; margin-bottom: 10px;">🔄 Trading Activity</h4>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                            <div class="result-item">
                                <span class="result-label">Total Trades:</span>
                                <span class="result-value" style="font-weight: bold">${data.total_trades}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Winning Trades:</span>
                                <span class="result-value" style="color: #27ae60">${data.winning_trades}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Losing Trades:</span>
                                <span class="result-value" style="color: #e74c3c">${data.losing_trades}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Win Rate:</span>
                                <span class="result-value" style="color: ${winRateColor}; font-weight: bold">${data.win_rate.toFixed(2)}%</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Average Win:</span>
                                <span class="result-value" style="color: #27ae60">$${data.average_win.toFixed(2)}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Average Loss:</span>
                                <span class="result-value" style="color: #e74c3c">$${data.average_loss.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                `;
                
                // Add recent trades section if available
                if (data.trades && data.trades.length > 0) {
                    resultsHtml += `
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                            <h4 style="color: #2c3e50; margin-bottom: 10px;">📜 Recent Trades (Last ${data.trades.length})</h4>
                            <div style="max-height: 200px; overflow-y: auto;">
                                <table style="width: 100%; font-size: 14px;">
                                    <thead>
                                        <tr style="background: #ecf0f1;">
                                            <th style="padding: 8px; text-align: left;">Time</th>
                                            <th style="padding: 8px; text-align: center;">Action</th>
                                            <th style="padding: 8px; text-align: right;">Amount</th>
                                            <th style="padding: 8px; text-align: right;">USDT/KRW</th>
                                            <th style="padding: 8px; text-align: right;">USD/KRW</th>
                                            <th style="padding: 8px; text-align: right;">Diff %</th>
                                            <th style="padding: 8px; text-align: right;">P/L</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;
                    
                    data.trades.forEach(trade => {
                        const actionColor = trade.action === 'BUY' ? '#3498db' : '#e67e22';
                        const plColor = trade.profit_loss >= 0 ? '#27ae60' : '#e74c3c';
                        const timestamp = new Date(trade.timestamp).toLocaleString();
                        
                        resultsHtml += `
                            <tr style="border-bottom: 1px solid #ecf0f1;">
                                <td style="padding: 8px; font-size: 12px;">${timestamp}</td>
                                <td style="padding: 8px; text-align: center; color: ${actionColor}; font-weight: bold;">${trade.action}</td>
                                <td style="padding: 8px; text-align: right;">$${trade.amount_usd.toFixed(2)}</td>
                                <td style="padding: 8px; text-align: right;">${trade.usdt_krw_price.toFixed(0)}</td>
                                <td style="padding: 8px; text-align: right;">${trade.usd_krw_rate.toFixed(0)}</td>
                                <td style="padding: 8px; text-align: right;">${trade.difference_percentage.toFixed(2)}%</td>
                                <td style="padding: 8px; text-align: right; color: ${plColor}; font-weight: bold;">$${trade.profit_loss.toFixed(2)}</td>
                            </tr>
                        `;
                    });
                    
                    resultsHtml += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                }
                
                document.getElementById('backtestResultsContent').innerHTML = resultsHtml;
                showElement('backtestResults');
            }
            
            function displayOptimizationResults(data) {
                let resultsHtml = '';
                
                if (data.best_params) {
                    resultsHtml += `
                        <h4>🎯 Best Parameters Found:</h4>
                        <div class="result-item">
                            <span class="result-label">Threshold:</span>
                            <span class="result-value">${data.best_params.threshold.toFixed(2)}%</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Return:</span>
                            <span class="result-value">${data.best_params.return_pct.toFixed(2)}%</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Max Drawdown:</span>
                            <span class="result-value">${data.best_params.max_drawdown.toFixed(2)}%</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Win Rate:</span>
                            <span class="result-value">${data.best_params.win_rate.toFixed(2)}%</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Total Trades:</span>
                            <span class="result-value">${data.best_params.trades}</span>
                        </div>
                        <br>
                    `;
                } else {
                    resultsHtml += '<p>❌ No profitable parameters found in the tested range.</p><br>';
                }
                
                if (data.all_results && data.all_results.length > 0) {
                    resultsHtml += '<h4>📊 Top Results:</h4>';
                    const sortedResults = data.all_results.sort((a, b) => b.return_pct - a.return_pct).slice(0, 5);
                    
                    sortedResults.forEach((result, index) => {
                        resultsHtml += `
                            <div class="result-item">
                                <span class="result-label">${index + 1}. Threshold ${result.threshold.toFixed(2)}%:</span>
                                <span class="result-value">${result.return_pct.toFixed(2)}% return</span>
                            </div>
                        `;
                    });
                }
                
                document.getElementById('optimizationResultsContent').innerHTML = resultsHtml;
                showElement('optimizationResults');
            }
            
            function updateTradingStatus(message) {
                const statusHtml = `
                    <div class="result-item">
                        <span class="result-label">Status:</span>
                        <span class="result-value">${message}</span>
                    </div>
                    <div class="result-item">
                        <span class="result-label">Last Update:</span>
                        <span class="result-value">${new Date().toLocaleString()}</span>
                    </div>
                `;
                
                document.getElementById('tradingStatusContent').innerHTML = statusHtml;
            }
            
            // Update system status every 30 seconds
            setInterval(updateSystemStatus, 30000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import sys
    
    # Configure logging to avoid Unicode issues
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Remove all emoji characters from logger
    class UnicodeFilter(logging.Filter):
        def filter(self, record):
            # Remove emoji characters from log messages
            import re
            if hasattr(record, 'msg'):
                record.msg = re.sub(r'[^\x00-\x7F]+', '', str(record.msg))
            return True
    
    # Add filter to all loggers
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.addFilter(UnicodeFilter())
    
    logger.info("Starting Upbit Trading Bot Web Interface...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 