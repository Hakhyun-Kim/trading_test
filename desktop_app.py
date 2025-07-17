import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import threading
import queue
import json
import os
from upbit_bot.trading_bot import UpbitTradingBot, TradingConfig
from upbit_bot.backtest import EnhancedUpbitBacktest, BacktestConfig
from upbit_bot.kimchi_premium import KimchiPremiumCalculator, KimchiPremiumStrategy
from debug_backtest import DebugUpbitBacktest
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

class UpbitTradingBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Upbit Trading Bot")
        self.root.geometry("1200x800")
        
        # Variables
        self.initial_balance = tk.DoubleVar(value=10000)
        self.max_trade_amount = tk.DoubleVar(value=1000)
        self.price_threshold = tk.DoubleVar(value=0.5)
        self.stop_loss = tk.DoubleVar(value=2.0)
        self.take_profit = tk.DoubleVar(value=1.0)
        self.max_trades_per_day = tk.IntVar(value=10)
        
        self.use_real_data = tk.BooleanVar(value=True)
        self.debug_mode = tk.BooleanVar(value=False)
        self.verbose_debug = tk.BooleanVar(value=False)
        self.show_signals = tk.BooleanVar(value=False)
        
        self.api_key = tk.StringVar()
        self.secret_key = tk.StringVar()
        self.virtual_mode = tk.BooleanVar(value=True)
        
        self.is_running = False
        self.bot = None
        self.queue = queue.Queue()
        
        # Store last backtest result for chart display
        self.last_backtest_result = None
        
        # Setup UI
        self.setup_menu()
        self.setup_ui()
        
        # Start queue processing
        self.process_queue()
        
    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Config", command=self.load_config)
        file_menu.add_command(label="Save Config", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Parameter Optimizer", command=self.open_optimizer)
        tools_menu.add_command(label="Export Results", command=self.export_results)
        
    def setup_ui(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Setup tabs
        self.setup_config_tab()
        self.setup_backtest_tab()
        self.setup_trading_tab()
        self.setup_results_tab()
        
    def setup_config_tab(self):
        # Configuration tab
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Configuration")
        
        # API Keys section
        api_frame = ttk.LabelFrame(config_frame, text="API Configuration", padding="10")
        api_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky="w", pady=2)
        api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=50, show="*")
        api_key_entry.grid(row=0, column=1, pady=2, padx=5)
        
        ttk.Label(api_frame, text="Secret Key:").grid(row=1, column=0, sticky="w", pady=2)
        secret_key_entry = ttk.Entry(api_frame, textvariable=self.secret_key, width=50, show="*")
        secret_key_entry.grid(row=1, column=1, pady=2, padx=5)
        
        ttk.Button(api_frame, text="Test Connection", command=self.test_connection).grid(row=2, column=1, pady=10)
        
        # Trading Parameters section
        params_frame = ttk.LabelFrame(config_frame, text="Trading Parameters", padding="10")
        params_frame.pack(fill="x", padx=10, pady=5)
        
        # Initial balance
        ttk.Label(params_frame, text="Initial Balance (USD):").grid(row=0, column=0, sticky="w", pady=2)
        self.initial_balance = tk.DoubleVar(value=10000.0)
        ttk.Entry(params_frame, textvariable=self.initial_balance, width=20).grid(row=0, column=1, pady=2, padx=5)
        
        # Max trade amount
        ttk.Label(params_frame, text="Max Trade Amount (USD):").grid(row=1, column=0, sticky="w", pady=2)
        self.max_trade_amount = tk.DoubleVar(value=1000.0)
        ttk.Entry(params_frame, textvariable=self.max_trade_amount, width=20).grid(row=1, column=1, pady=2, padx=5)
        
        # Price threshold
        ttk.Label(params_frame, text="Price Threshold (%):").grid(row=2, column=0, sticky="w", pady=2)
        self.price_threshold = tk.DoubleVar(value=0.5)
        ttk.Entry(params_frame, textvariable=self.price_threshold, width=20).grid(row=2, column=1, pady=2, padx=5)
        
        # Stop loss
        ttk.Label(params_frame, text="Stop Loss (%):").grid(row=0, column=2, sticky="w", pady=2, padx=20)
        self.stop_loss = tk.DoubleVar(value=2.0)
        ttk.Entry(params_frame, textvariable=self.stop_loss, width=20).grid(row=0, column=3, pady=2, padx=5)
        
        # Take profit
        ttk.Label(params_frame, text="Take Profit (%):").grid(row=1, column=2, sticky="w", pady=2, padx=20)
        self.take_profit = tk.DoubleVar(value=1.0)
        ttk.Entry(params_frame, textvariable=self.take_profit, width=20).grid(row=1, column=3, pady=2, padx=5)
        
        # Max trades per day
        ttk.Label(params_frame, text="Max Trades/Day:").grid(row=2, column=2, sticky="w", pady=2, padx=20)
        self.max_trades_per_day = tk.IntVar(value=10)
        ttk.Entry(params_frame, textvariable=self.max_trades_per_day, width=20).grid(row=2, column=3, pady=2, padx=5)
        
        # Kimchi Premium Strategy section
        kimchi_frame = ttk.LabelFrame(config_frame, text="Kimchi Premium Strategy", padding="10")
        kimchi_frame.pack(fill="x", padx=10, pady=5)
        
        # Enable kimchi premium strategy
        self.use_kimchi_premium = tk.BooleanVar(value=True)
        ttk.Checkbutton(kimchi_frame, text="Use Kimchi Premium Strategy", variable=self.use_kimchi_premium).grid(row=0, column=0, columnspan=2, sticky="w", pady=2)
        
        # Kimchi premium buy threshold
        ttk.Label(kimchi_frame, text="Buy Threshold (%):").grid(row=1, column=0, sticky="w", pady=2)
        self.kimchi_buy_threshold = tk.DoubleVar(value=-2.0)
        ttk.Entry(kimchi_frame, textvariable=self.kimchi_buy_threshold, width=20).grid(row=1, column=1, pady=2, padx=5)
        ttk.Label(kimchi_frame, text="(Buy when premium below this)").grid(row=1, column=2, sticky="w", pady=2, padx=5)
        
        # Kimchi premium sell threshold
        ttk.Label(kimchi_frame, text="Sell Threshold (%):").grid(row=2, column=0, sticky="w", pady=2)
        self.kimchi_sell_threshold = tk.DoubleVar(value=2.0)
        ttk.Entry(kimchi_frame, textvariable=self.kimchi_sell_threshold, width=20).grid(row=2, column=1, pady=2, padx=5)
        ttk.Label(kimchi_frame, text="(Sell when premium above this)").grid(row=2, column=2, sticky="w", pady=2, padx=5)
        
        # Kimchi premium status
        kimchi_status_frame = ttk.Frame(kimchi_frame)
        kimchi_status_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky="ew")
        
        ttk.Button(kimchi_status_frame, text="Check Current Premium", command=self.check_kimchi_premium).pack(side="left", padx=5)
        self.kimchi_status_label = ttk.Label(kimchi_status_frame, text="Click to check current kimchi premium")
        self.kimchi_status_label.pack(side="left", padx=10)
        
    def setup_backtest_tab(self):
        # Backtest tab
        backtest_frame = ttk.Frame(self.notebook)
        self.notebook.add(backtest_frame, text="Backtest")
        
        # Date range section
        date_frame = ttk.LabelFrame(backtest_frame, text="Date Range", padding="10")
        date_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(date_frame, text="Start Date:").grid(row=0, column=0, sticky="w", pady=2)
        self.start_date = tk.StringVar(value="2024-01-01")
        ttk.Entry(date_frame, textvariable=self.start_date, width=20).grid(row=0, column=1, pady=2, padx=5)
        
        ttk.Label(date_frame, text="End Date:").grid(row=0, column=2, sticky="w", pady=2, padx=20)
        self.end_date = tk.StringVar(value="2024-12-31")
        ttk.Entry(date_frame, textvariable=self.end_date, width=20).grid(row=0, column=3, pady=2, padx=5)
        
        # Options
        options_frame = ttk.LabelFrame(backtest_frame, text="Options", padding="10")
        options_frame.pack(fill="x", padx=10, pady=5)
        
        self.use_real_data = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Use Real Upbit Data", variable=self.use_real_data).pack(anchor="w")
        
        self.export_results_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Export Results", variable=self.export_results_var).pack(anchor="w")
        
        # Debug options
        debug_frame = ttk.Frame(options_frame)
        debug_frame.pack(fill="x", pady=5)
        
        self.debug_mode = tk.BooleanVar(value=True)
        ttk.Checkbutton(debug_frame, text="Show Trade Alerts", variable=self.debug_mode).pack(side="left")
        
        self.verbose_debug = tk.BooleanVar(value=False)
        ttk.Checkbutton(debug_frame, text="Verbose Debug Mode", variable=self.verbose_debug).pack(side="left", padx=20)
        
        self.show_signals = tk.BooleanVar(value=True)
        ttk.Checkbutton(debug_frame, text="Show Trading Signals", variable=self.show_signals).pack(side="left", padx=20)
        
        # Advanced Parameters section
        advanced_frame = ttk.LabelFrame(backtest_frame, text="Advanced Strategy Parameters", padding="10")
        advanced_frame.pack(fill="x", padx=10, pady=5)
        
        # Profit boundaries
        profit_frame = ttk.Frame(advanced_frame)
        profit_frame.pack(fill="x", pady=2)
        
        ttk.Label(profit_frame, text="Min Profit Boundary (%):").grid(row=0, column=0, sticky="w", padx=5)
        self.min_profit_boundary = tk.DoubleVar(value=0.1)
        ttk.Entry(profit_frame, textvariable=self.min_profit_boundary, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(profit_frame, text="Max Profit Boundary (%):").grid(row=0, column=2, sticky="w", padx=5)
        self.max_profit_boundary = tk.DoubleVar(value=3.0)
        ttk.Entry(profit_frame, textvariable=self.max_profit_boundary, width=15).grid(row=0, column=3, padx=5)
        
        # Risk boundaries
        risk_frame = ttk.Frame(advanced_frame)
        risk_frame.pack(fill="x", pady=2)
        
        ttk.Label(risk_frame, text="Max Loss per Trade (%):").grid(row=0, column=0, sticky="w", padx=5)
        self.max_loss_per_trade = tk.DoubleVar(value=1.0)
        ttk.Entry(risk_frame, textvariable=self.max_loss_per_trade, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(risk_frame, text="Max Drawdown (%):").grid(row=0, column=2, sticky="w", padx=5)
        self.max_drawdown_limit = tk.DoubleVar(value=10.0)
        ttk.Entry(risk_frame, textvariable=self.max_drawdown_limit, width=15).grid(row=0, column=3, padx=5)
        
        # Price difference boundaries
        diff_frame = ttk.Frame(advanced_frame)
        diff_frame.pack(fill="x", pady=2)
        
        ttk.Label(diff_frame, text="Buy Price Diff (%):").grid(row=0, column=0, sticky="w", padx=5)
        self.buy_price_diff = tk.DoubleVar(value=-0.5)
        ttk.Entry(diff_frame, textvariable=self.buy_price_diff, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(diff_frame, text="Sell Price Diff (%):").grid(row=0, column=2, sticky="w", padx=5)
        self.sell_price_diff = tk.DoubleVar(value=0.5)
        ttk.Entry(diff_frame, textvariable=self.sell_price_diff, width=15).grid(row=0, column=3, padx=5)
        
        # Trading frequency controls
        freq_frame = ttk.Frame(advanced_frame)
        freq_frame.pack(fill="x", pady=2)
        
        ttk.Label(freq_frame, text="Min Trade Interval (min):").grid(row=0, column=0, sticky="w", padx=5)
        self.min_trade_interval = tk.IntVar(value=30)
        ttk.Entry(freq_frame, textvariable=self.min_trade_interval, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(freq_frame, text="Position Size (%):").grid(row=0, column=2, sticky="w", padx=5)
        self.position_size = tk.DoubleVar(value=20.0)
        ttk.Entry(freq_frame, textvariable=self.position_size, width=15).grid(row=0, column=3, padx=5)
        
        # Optimization section
        optimization_frame = ttk.LabelFrame(backtest_frame, text="Parameter Optimization", padding="10")
        optimization_frame.pack(fill="x", padx=10, pady=5)
        
        opt_controls = ttk.Frame(optimization_frame)
        opt_controls.pack(fill="x", pady=2)
        
        ttk.Button(opt_controls, text="Find Profitable Boundaries", command=self.optimize_boundaries).pack(side="left", padx=5)
        ttk.Button(opt_controls, text="Test Multiple Scenarios", command=self.test_scenarios).pack(side="left", padx=5)
        
        # Scenario results
        self.scenario_results = tk.Text(optimization_frame, height=6, wrap="word")
        opt_scrollbar = ttk.Scrollbar(optimization_frame, orient="vertical", command=self.scenario_results.yview)
        self.scenario_results.configure(yscrollcommand=opt_scrollbar.set)
        
        self.scenario_results.pack(side="left", fill="both", expand=True, pady=5)
        opt_scrollbar.pack(side="right", fill="y", pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(backtest_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(control_frame, text="Run Backtest", command=self.run_backtest).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Stop Backtest", command=self.stop_backtest).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Clear Results", command=self.clear_results).pack(side="left", padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(backtest_frame, mode='determinate', maximum=100)
        self.progress.pack(fill="x", padx=10, pady=5)
        
        # Status label
        self.status_label = ttk.Label(backtest_frame, text="Ready to run backtest")
        self.status_label.pack(pady=2)
        
        # Results display
        results_frame = ttk.LabelFrame(backtest_frame, text="Results", padding="10")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Results text area
        self.results_text = tk.Text(results_frame, height=15, wrap="word")
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def setup_trading_tab(self):
        # Trading tab
        trading_frame = ttk.Frame(self.notebook)
        self.notebook.add(trading_frame, text="Live Trading")
        
        # Trading mode section
        mode_frame = ttk.LabelFrame(trading_frame, text="Trading Mode", padding="10")
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        self.virtual_mode = tk.BooleanVar(value=True)
        ttk.Radiobutton(mode_frame, text="Virtual Trading", variable=self.virtual_mode, value=True).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Live Trading", variable=self.virtual_mode, value=False).pack(anchor="w")
        
        # Control buttons
        control_frame = ttk.Frame(trading_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="Start Trading", command=self.start_trading)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Trading", command=self.stop_trading, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        # Status display
        status_frame = ttk.LabelFrame(trading_frame, text="Status", padding="10")
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.status_text = tk.Text(status_frame, height=20, wrap="word")
        status_scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_text.pack(side="left", fill="both", expand=True)
        status_scrollbar.pack(side="right", fill="y")
        
    def setup_results_tab(self):
        # Results and charts tab
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="Charts & Analysis")
        
        # Chart area
        self.chart_frame = ttk.Frame(results_frame)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Chart controls
        chart_controls = ttk.Frame(results_frame)
        chart_controls.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(chart_controls, text="Equity Curve", command=self.show_equity_curve).pack(side="left", padx=5)
        ttk.Button(chart_controls, text="Trade Distribution", command=self.show_trade_distribution).pack(side="left", padx=5)
        ttk.Button(chart_controls, text="Performance Metrics", command=self.show_performance_metrics).pack(side="left", padx=5)
        
    def test_connection(self):
        """Test API connection"""
        try:
            if not self.api_key.get() or not self.secret_key.get():
                messagebox.showwarning("Warning", "Please enter both API key and secret key")
                return
            
            # Test connection in a separate thread
            def test_api():
                try:
                    bot = UpbitTradingBot(
                        api_key=self.api_key.get(),
                        secret_key=self.secret_key.get(),
                        virtual_mode=False
                    )
                    # Try to get account info
                    balance = bot.get_current_balance()
                    self.queue.put(("connection_success", balance))
                except Exception as e:
                    self.queue.put(("connection_error", str(e)))
            
            threading.Thread(target=test_api, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Connection test failed: {str(e)}")
    
    def check_kimchi_premium(self):
        """Check current kimchi premium"""
        def check_premium():
            try:
                calculator = KimchiPremiumCalculator()
                premium_data = calculator.calculate_kimchi_premium()
                
                if premium_data:
                    self.queue.put(("kimchi_premium_result", premium_data))
                else:
                    self.queue.put(("kimchi_premium_error", "Failed to calculate kimchi premium"))
            except Exception as e:
                self.queue.put(("kimchi_premium_error", str(e)))
        
        threading.Thread(target=check_premium, daemon=True).start()
    
    def optimize_boundaries(self):
        """Find profitable parameter boundaries automatically"""
        if self.is_running:
            messagebox.showwarning("Warning", "Another operation is already running")
            return
        
        self.is_running = True
        self.scenario_results.delete(1.0, tk.END)
        self.scenario_results.insert(tk.END, "🔍 Searching for profitable boundaries...\n")
        
        def optimization_worker():
            try:
                start_dt = datetime.strptime(self.start_date.get(), "%Y-%m-%d")
                end_dt = datetime.strptime(self.end_date.get(), "%Y-%m-%d")
                
                best_params = None
                best_return = float('-inf')
                results = []
                
                # Test different parameter combinations
                price_thresholds = [0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]
                stop_losses = [1.0, 1.5, 2.0, 3.0, 5.0]
                take_profits = [0.5, 1.0, 1.5, 2.0, 3.0]
                
                total_combinations = len(price_thresholds) * len(stop_losses) * len(take_profits)
                current = 0
                
                for threshold in price_thresholds:
                    for stop_loss in stop_losses:
                        for take_profit in take_profits:
                            current += 1
                            progress = (current / total_combinations) * 100
                            
                            self.queue.put(("optimization_progress", (progress, f"Testing combination {current}/{total_combinations}")))
                            
                            config = BacktestConfig(
                                initial_balance_usd=float(self.initial_balance.get()),
                                max_trade_amount=float(self.max_trade_amount.get()),
                                price_threshold=threshold,
                                stop_loss_threshold=stop_loss,
                                take_profit_threshold=take_profit,
                                max_trades_per_day=int(self.max_trades_per_day.get())
                            )
                            
                            backtest = EnhancedUpbitBacktest(config)
                            result = backtest.run_backtest(start_dt, end_dt, use_real_data=self.use_real_data.get())
                            
                            result_data = {
                                'threshold': threshold,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'return_pct': result.return_percentage,
                                'max_drawdown': result.max_drawdown,
                                'trades': result.total_trades,
                                'win_rate': result.win_rate
                            }
                            results.append(result_data)
                            
                            if result.return_percentage > best_return and result.total_trades > 0:
                                best_return = result.return_percentage
                                best_params = result_data
                
                self.queue.put(("optimization_complete", (best_params, results)))
                
            except Exception as e:
                self.queue.put(("optimization_error", str(e)))
        
        threading.Thread(target=optimization_worker, daemon=True).start()
    
    def test_scenarios(self):
        """Test multiple predefined scenarios"""
        if self.is_running:
            messagebox.showwarning("Warning", "Another operation is already running")
            return
        
        self.is_running = True
        self.scenario_results.delete(1.0, tk.END)
        self.scenario_results.insert(tk.END, "🧪 Testing predefined scenarios...\n")
        
        def scenario_worker():
            try:
                start_dt = datetime.strptime(self.start_date.get(), "%Y-%m-%d")
                end_dt = datetime.strptime(self.end_date.get(), "%Y-%m-%d")
                
                # Predefined scenarios
                scenarios = [
                    {"name": "Conservative", "threshold": 1.0, "stop_loss": 2.0, "take_profit": 1.0},
                    {"name": "Moderate", "threshold": 0.5, "stop_loss": 1.5, "take_profit": 1.5},
                    {"name": "Aggressive", "threshold": 0.3, "stop_loss": 1.0, "take_profit": 2.0},
                    {"name": "High Frequency", "threshold": 0.2, "stop_loss": 0.8, "take_profit": 0.8},
                    {"name": "Low Risk", "threshold": 1.5, "stop_loss": 3.0, "take_profit": 0.8},
                    {"name": "Swing Trading", "threshold": 0.8, "stop_loss": 2.5, "take_profit": 2.5}
                ]
                
                results = []
                for i, scenario in enumerate(scenarios):
                    progress = ((i + 1) / len(scenarios)) * 100
                    self.queue.put(("scenario_progress", (progress, f"Testing {scenario['name']} strategy...")))
                    
                    config = BacktestConfig(
                        initial_balance_usd=float(self.initial_balance.get()),
                        max_trade_amount=float(self.max_trade_amount.get()),
                        price_threshold=scenario['threshold'],
                        stop_loss_threshold=scenario['stop_loss'],
                        take_profit_threshold=scenario['take_profit'],
                        max_trades_per_day=int(self.max_trades_per_day.get())
                    )
                    
                    backtest = EnhancedUpbitBacktest(config)
                    result = backtest.run_backtest(start_dt, end_dt, use_real_data=self.use_real_data.get())
                    
                    scenario_result = {
                        'name': scenario['name'],
                        'return_pct': result.return_percentage,
                        'max_drawdown': result.max_drawdown,
                        'trades': result.total_trades,
                        'win_rate': result.win_rate,
                        'params': scenario
                    }
                    results.append(scenario_result)
                
                self.queue.put(("scenarios_complete", results))
                
            except Exception as e:
                self.queue.put(("scenarios_error", str(e)))
        
        threading.Thread(target=scenario_worker, daemon=True).start()
    
    def run_backtest(self):
        """Run backtest in a separate thread"""
        if self.is_running:
            messagebox.showwarning("Warning", "Already running a backtest")
            return
        
        self.is_running = True
        self.progress['value'] = 0
        self.status_label.config(text="Starting backtest...")
        
        def backtest_worker():
            try:
                # Update status
                self.queue.put(("progress_update", (10, "Parsing dates and configuration...")))
                
                # Parse dates
                start_dt = datetime.strptime(self.start_date.get(), "%Y-%m-%d")
                end_dt = datetime.strptime(self.end_date.get(), "%Y-%m-%d")
                
                # Create configuration with advanced parameters
                config = BacktestConfig(
                    initial_balance_usd=float(self.initial_balance.get()),
                    max_trade_amount=float(self.max_trade_amount.get()),
                    price_threshold=float(self.price_threshold.get()),
                    stop_loss_threshold=float(self.stop_loss.get()),
                    take_profit_threshold=float(self.take_profit.get()),
                    max_trades_per_day=int(self.max_trades_per_day.get())
                )
                
                # Apply advanced parameters to strategy
                self.queue.put(("progress_update", (15, "Applying advanced parameters...")))
                
                # Add debug configuration
                debug_config = {
                    'debug_mode': self.debug_mode.get(),
                    'verbose_debug': self.verbose_debug.get(),
                    'show_signals': self.show_signals.get()
                }
                
                self.queue.put(("progress_update", (30, "Fetching historical data...")))
                
                # Create debug-enabled backtest
                backtest = DebugUpbitBacktest(config, debug_config, self.queue)
                
                self.queue.put(("progress_update", (50, "Running backtest simulation...")))
                
                result = backtest.run_backtest(start_dt, end_dt, use_real_data=self.use_real_data.get())
                
                self.queue.put(("progress_update", (90, "Calculating performance metrics...")))
                
                # Small delay to show final progress
                import time
                time.sleep(0.5)
                
                self.queue.put(("progress_update", (100, "Backtest completed!")))
                self.queue.put(("backtest_complete", result))
                
            except Exception as e:
                self.queue.put(("backtest_error", str(e)))
        
        threading.Thread(target=backtest_worker, daemon=True).start()
    
    def stop_backtest(self):
        """Stop running backtest"""
        self.is_running = False
        self.progress['value'] = 0
        self.status_label.config(text="Backtest stopped")
    
    def clear_results(self):
        """Clear results display"""
        self.results_text.delete(1.0, tk.END)
    
    def start_trading(self):
        """Start live trading"""
        if self.is_running:
            messagebox.showwarning("Warning", "Already running")
            return
        
        try:
            # Create trading configuration
            config = TradingConfig(
                max_trade_amount=self.max_trade_amount.get(),
                price_threshold=self.price_threshold.get(),
                stop_loss_threshold=self.stop_loss.get(),
                take_profit_threshold=self.take_profit.get(),
                max_trades_per_day=self.max_trades_per_day.get(),
                max_daily_loss=self.max_trade_amount.get() * 5,  # 5x max trade amount
                emergency_stop_loss=5.0
            )
            
            # Create bot
            if self.virtual_mode.get():
                self.bot = UpbitTradingBot(
                    virtual_mode=True,
                    initial_balance_usd=self.initial_balance.get(),
                    config=config
                )
            else:
                if not self.api_key.get() or not self.secret_key.get():
                    messagebox.showerror("Error", "API keys required for live trading")
                    return
                
                self.bot = UpbitTradingBot(
                    api_key=self.api_key.get(),
                    secret_key=self.secret_key.get(),
                    virtual_mode=False,
                    config=config
                )
            
            # Start trading in separate thread
            def trading_worker():
                try:
                    self.bot.run_bot(check_interval=60)
                except Exception as e:
                    self.queue.put(("trading_error", str(e)))
            
            threading.Thread(target=trading_worker, daemon=True).start()
            
            self.is_running = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            
            self.update_status("Trading started...")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start trading: {str(e)}")
    
    def stop_trading(self):
        """Stop live trading"""
        if self.bot:
            try:
                self.bot.stop_bot()
            except:
                pass
        
        self.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        self.update_status("Trading stopped.")
    
    def update_status(self, message):
        """Update status display"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
    
    def show_equity_curve(self):
        """Show equity curve chart"""
        if self.last_backtest_result:
            # Clear previous chart
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            
            # Create figure with subplots
            fig = plt.figure(figsize=(15, 10))
            
            # 1. Equity Curve (Top Left)
            ax1 = plt.subplot(2, 3, 1)
            if hasattr(self.last_backtest_result, 'balance_history') and self.last_backtest_result.balance_history:
                dates = [trade.timestamp for trade in self.last_backtest_result.trades]
                balances = self.last_backtest_result.balance_history
                ax1.plot(dates, balances, 'b-', linewidth=2)
                ax1.fill_between(dates, self.last_backtest_result.initial_balance, balances, alpha=0.3)
                ax1.axhline(y=self.last_backtest_result.initial_balance, color='r', linestyle='--', alpha=0.5)
                ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
                ax1.set_xlabel('Date')
                ax1.set_ylabel('Balance ($)')
                ax1.grid(True, alpha=0.3)
                ax1.tick_params(axis='x', rotation=45)
            else:
                # Simulate equity curve from trades
                balances = [self.last_backtest_result.initial_balance]
                balance = self.last_backtest_result.initial_balance
                dates = []
                for trade in self.last_backtest_result.trades:
                    if trade.action == "BUY":
                        balance -= trade.amount_usd
                    else:  # SELL
                        balance += trade.amount_usd * (1 + trade.profit_pct/100 if hasattr(trade, 'profit_pct') else 1)
                    balances.append(balance)
                    dates.append(trade.timestamp)
                
                if dates:
                    ax1.plot(dates, balances[1:], 'b-', linewidth=2)
                    ax1.fill_between(dates, self.last_backtest_result.initial_balance, balances[1:], alpha=0.3)
                    ax1.axhline(y=self.last_backtest_result.initial_balance, color='r', linestyle='--', alpha=0.5)
                ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
                ax1.set_xlabel('Date')
                ax1.set_ylabel('Balance ($)')
                ax1.grid(True, alpha=0.3)
            
            # 2. Trade Distribution (Top Center)
            ax2 = plt.subplot(2, 3, 2)
            if self.last_backtest_result.winning_trades > 0 or self.last_backtest_result.losing_trades > 0:
                labels = ['Winning', 'Losing']
                sizes = [self.last_backtest_result.winning_trades, self.last_backtest_result.losing_trades]
                colors = ['#4CAF50', '#F44336']
                explode = (0.1, 0)
                ax2.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                        shadow=True, startangle=90)
                ax2.set_title('Trade Distribution', fontsize=14, fontweight='bold')
            else:
                ax2.text(0.5, 0.5, 'No trades executed', ha='center', va='center', transform=ax2.transAxes)
                ax2.set_title('Trade Distribution', fontsize=14, fontweight='bold')
            
            # 3. Monthly Returns (Top Right)
            ax3 = plt.subplot(2, 3, 3)
            if self.last_backtest_result.trades:
                # Group trades by month and calculate returns
                monthly_returns = {}
                for trade in self.last_backtest_result.trades:
                    month_key = trade.timestamp.strftime('%Y-%m')
                    if month_key not in monthly_returns:
                        monthly_returns[month_key] = 0
                    if hasattr(trade, 'profit_pct'):
                        monthly_returns[month_key] += trade.profit_pct
                
                if monthly_returns:
                    months = list(monthly_returns.keys())
                    returns = list(monthly_returns.values())
                    colors = ['#4CAF50' if r > 0 else '#F44336' for r in returns]
                    ax3.bar(months, returns, color=colors, alpha=0.7)
                    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                    ax3.set_title('Monthly Returns (%)', fontsize=14, fontweight='bold')
                    ax3.set_xlabel('Month')
                    ax3.set_ylabel('Return %')
                    ax3.tick_params(axis='x', rotation=45)
                    ax3.grid(True, alpha=0.3, axis='y')
            
            # 4. Drawdown Chart (Bottom Left)
            ax4 = plt.subplot(2, 3, 4)
            if hasattr(self.last_backtest_result, 'drawdown_history') and self.last_backtest_result.drawdown_history:
                dates = [d[0] for d in self.last_backtest_result.drawdown_history]
                drawdowns = [d[1] for d in self.last_backtest_result.drawdown_history]
                ax4.fill_between(dates, 0, drawdowns, color='red', alpha=0.3)
                ax4.plot(dates, drawdowns, 'r-', linewidth=2)
                ax4.set_title('Drawdown History', fontsize=14, fontweight='bold')
                ax4.set_xlabel('Date')
                ax4.set_ylabel('Drawdown %')
                ax4.grid(True, alpha=0.3)
            else:
                ax4.text(0.5, 0.5, 'Drawdown data not available', ha='center', va='center', transform=ax4.transAxes)
                ax4.set_title('Drawdown History', fontsize=14, fontweight='bold')
            
            # 5. Profit/Loss Distribution (Bottom Center)
            ax5 = plt.subplot(2, 3, 5)
            if self.last_backtest_result.trades:
                profits = []
                for trade in self.last_backtest_result.trades:
                    if hasattr(trade, 'profit_pct'):
                        profits.append(trade.profit_pct)
                    elif hasattr(trade, 'profit'):
                        profits.append(trade.profit)
                
                if profits:
                    ax5.hist(profits, bins=20, color='blue', alpha=0.7, edgecolor='black')
                    ax5.axvline(x=0, color='red', linestyle='--', linewidth=2)
                    ax5.set_title('Profit/Loss Distribution', fontsize=14, fontweight='bold')
                    ax5.set_xlabel('Profit %')
                    ax5.set_ylabel('Frequency')
                    ax5.grid(True, alpha=0.3, axis='y')
            
            # 6. Performance Summary (Bottom Right)
            ax6 = plt.subplot(2, 3, 6)
            ax6.axis('off')
            
            # Create performance summary text
            summary_text = f"""Performance Summary
            
Total Return: {self.last_backtest_result.return_percentage:.2f}%
Sharpe Ratio: {self.last_backtest_result.sharpe_ratio:.2f}
Win Rate: {self.last_backtest_result.win_rate:.2f}%
Profit Factor: {self.last_backtest_result.profit_factor:.2f}
Max Drawdown: {self.last_backtest_result.max_drawdown:.2f}%

Total Trades: {self.last_backtest_result.total_trades}
Avg Win: ${self.last_backtest_result.average_win:.2f}
Avg Loss: ${self.last_backtest_result.average_loss:.2f}
            """
            
            ax6.text(0.1, 0.9, summary_text, transform=ax6.transAxes, fontsize=12,
                    verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))
            
            plt.tight_layout()
            
            # Add to chart frame
            canvas = FigureCanvasTkAgg(fig, self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            # Show success message
            messagebox.showinfo("Backtest Complete", 
                              f"Backtest completed successfully!\n\n"
                              f"Return: {self.last_backtest_result.return_percentage:.2f}%\n"
                              f"Total Trades: {self.last_backtest_result.total_trades}\n"
                              f"Win Rate: {self.last_backtest_result.win_rate:.2f}%")
        else:
            messagebox.showwarning("Warning", "No backtest result to display.")
    
    def show_trade_distribution(self):
        """Show trade distribution chart"""
        # Placeholder for trade distribution
        messagebox.showinfo("Info", "Trade distribution chart - implement with actual data")
    
    def show_performance_metrics(self):
        """Show performance metrics"""
        # Placeholder for performance metrics
        messagebox.showinfo("Info", "Performance metrics - implement with actual data")
    
    def load_config(self):
        """Load configuration from file"""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    config = json.load(f)
                
                # Load values
                self.initial_balance.set(config.get('initial_balance', 10000))
                self.max_trade_amount.set(config.get('max_trade_amount', 1000))
                self.price_threshold.set(config.get('price_threshold', 0.5))
                self.stop_loss.set(config.get('stop_loss', 2.0))
                self.take_profit.set(config.get('take_profit', 1.0))
                self.max_trades_per_day.set(config.get('max_trades_per_day', 10))
                
                messagebox.showinfo("Success", "Configuration loaded successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
    
    def save_config(self):
        """Save configuration to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                config = {
                    'initial_balance': self.initial_balance.get(),
                    'max_trade_amount': self.max_trade_amount.get(),
                    'price_threshold': self.price_threshold.get(),
                    'stop_loss': self.stop_loss.get(),
                    'take_profit': self.take_profit.get(),
                    'max_trades_per_day': self.max_trades_per_day.get()
                }
                
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                
                messagebox.showinfo("Success", "Configuration saved successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
    def open_optimizer(self):
        """Open parameter optimizer window"""
        optimizer_window = tk.Toplevel(self.root)
        optimizer_window.title("Parameter Optimizer")
        optimizer_window.geometry("600x400")
        
        # Add optimizer UI here
        ttk.Label(optimizer_window, text="Parameter Optimizer").pack(pady=20)
        ttk.Label(optimizer_window, text="Feature coming soon...").pack(pady=20)
    
    def export_results(self):
        """Export results to file"""
        # Placeholder for export functionality
        messagebox.showinfo("Info", "Export results - implement with actual data")
    
    def process_queue(self):
        """Process messages from worker threads"""
        try:
            while True:
                message_type, data = self.queue.get_nowait()
                
                if message_type == "connection_success":
                    messagebox.showinfo("Success", f"Connection successful!\nBalance: {data}")
                elif message_type == "connection_error":
                    messagebox.showerror("Error", f"Connection failed: {data}")
                elif message_type == "progress_update":
                    progress_value, status_text = data
                    self.progress['value'] = progress_value
                    self.status_label.config(text=status_text)
                elif message_type == "backtest_complete":
                    self.display_backtest_results(data)
                    self.progress['value'] = 100
                    self.status_label.config(text="Backtest completed successfully!")
                    self.is_running = False
                elif message_type == "backtest_error":
                    messagebox.showerror("Error", f"Backtest failed: {data}")
                    self.progress['value'] = 0
                    self.status_label.config(text="Backtest failed")
                    self.is_running = False
                elif message_type == "trading_error":
                    messagebox.showerror("Error", f"Trading error: {data}")
                    self.stop_trading()
                elif message_type == "kimchi_premium_result":
                    premium = data.get('kimchi_premium_percentage', 0)
                    upbit_price = data.get('upbit_usdt_krw', 0)
                    binance_price = data.get('binance_usdt_krw', 0)
                    self.kimchi_status_label.config(text=f"Premium: {premium:.2f}% | Upbit: {upbit_price:.0f} | Binance: {binance_price:.0f}")
                elif message_type == "kimchi_premium_error":
                    self.kimchi_status_label.config(text=f"Error: {data}")
                    messagebox.showerror("Error", f"Kimchi premium calculation failed: {data}")
                elif message_type == "optimization_progress":
                    progress_value, status_text = data
                    self.progress['value'] = progress_value
                    self.status_label.config(text=status_text)
                elif message_type == "optimization_complete":
                    best_params, all_results = data
                    self.display_optimization_results(best_params, all_results)
                    self.is_running = False
                elif message_type == "optimization_error":
                    messagebox.showerror("Error", f"Optimization failed: {data}")
                    self.is_running = False
                elif message_type == "scenario_progress":
                    progress_value, status_text = data
                    self.progress['value'] = progress_value
                    self.status_label.config(text=status_text)
                elif message_type == "scenarios_complete":
                    self.display_scenario_results(data)
                    self.is_running = False
                elif message_type == "scenarios_error":
                    messagebox.showerror("Error", f"Scenario testing failed: {data}")
                    self.is_running = False
                elif message_type == "trade_alert":
                    action, amount, price, reason = data
                    messagebox.showinfo("Trade Executed!", 
                                      f"🔄 {action} Trade\n"
                                      f"💰 Amount: ${amount:.2f}\n"
                                      f"💱 Price: {price:.0f} KRW\n"
                                      f"📝 Reason: {reason}")
                elif message_type == "signal_alert":
                    signal, price_diff, threshold = data
                    if signal != 'HOLD':
                        messagebox.showinfo("Trading Signal!", 
                                          f"📡 Signal: {signal}\n"
                                          f"📊 Price Difference: {price_diff:.2f}%\n"
                                          f"🎯 Threshold: {threshold:.2f}%")
                elif message_type == "debug_info":
                    messagebox.showinfo("Debug Info", data)
                elif message_type == "market_update":
                    date, usd_krw, usdt_krw, diff = data
                    self.status_label.config(text=f"Processing {date}: Diff {diff:.2f}%")
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_queue)
    
    def display_backtest_results(self, result):
        """Display backtest results with comprehensive charts"""
        self.results_text.delete(1.0, tk.END)
        
        # Store the result for chart display
        self.last_backtest_result = result
        
        # Text results
        results_text = f"""
BACKTEST RESULTS
{'='*60}
Initial Balance: ${result.initial_balance:,.2f}
Final Balance: ${result.final_balance:,.2f}
Total Return: ${result.total_return:,.2f}
Return %: {result.return_percentage:.2f}%
Max Drawdown: {result.max_drawdown:.2f}%
Sharpe Ratio: {result.sharpe_ratio:.2f}
Win Rate: {result.win_rate:.2f}%
Profit Factor: {result.profit_factor:.2f}
Total Trades: {result.total_trades}
Winning Trades: {result.winning_trades}
Losing Trades: {result.losing_trades}
Average Win: ${result.average_win:.2f}
Average Loss: ${result.average_loss:.2f}
{'='*60}

Recent Trades:
"""
        
        self.results_text.insert(tk.END, results_text)
        
        # Add trade history
        for trade in result.trades[-10:]:  # Show last 10 trades
            trade_text = f"[{trade.timestamp}] {trade.action} - ${trade.amount_usd:.2f} - {'SUCCESS' if trade.success else 'FAILED'}\n"
            self.results_text.insert(tk.END, trade_text)
        
        self.results_text.see(tk.END)
        
        # Automatically switch to Charts & Analysis tab and display comprehensive charts
        self.notebook.select(3)  # Switch to Charts & Analysis tab
        self.display_comprehensive_charts(result)
    
    def display_optimization_results(self, best_params, all_results):
        """Display optimization results"""
        self.scenario_results.delete(1.0, tk.END)
        
        if best_params:
            self.scenario_results.insert(tk.END, "🎯 BEST PROFITABLE PARAMETERS FOUND:\n")
            self.scenario_results.insert(tk.END, f"Price Threshold: {best_params['threshold']}%\n")
            self.scenario_results.insert(tk.END, f"Stop Loss: {best_params['stop_loss']}%\n")
            self.scenario_results.insert(tk.END, f"Take Profit: {best_params['take_profit']}%\n")
            self.scenario_results.insert(tk.END, f"Return: {best_params['return_pct']:.2f}%\n")
            self.scenario_results.insert(tk.END, f"Max Drawdown: {best_params['max_drawdown']:.2f}%\n")
            self.scenario_results.insert(tk.END, f"Win Rate: {best_params['win_rate']:.2f}%\n")
            self.scenario_results.insert(tk.END, f"Total Trades: {best_params['trades']}\n\n")
            
            # Auto-apply best parameters
            self.price_threshold.set(best_params['threshold'])
            self.stop_loss.set(best_params['stop_loss'])
            self.take_profit.set(best_params['take_profit'])
            
            self.scenario_results.insert(tk.END, "✅ Best parameters applied to main settings!\n\n")
        else:
            self.scenario_results.insert(tk.END, "❌ No profitable parameters found in the tested range.\n\n")
        
        # Show top 5 results
        sorted_results = sorted(all_results, key=lambda x: x['return_pct'], reverse=True)[:5]
        self.scenario_results.insert(tk.END, "📊 TOP 5 RESULTS:\n")
        for i, result in enumerate(sorted_results, 1):
            self.scenario_results.insert(tk.END, f"{i}. Threshold: {result['threshold']}%, Return: {result['return_pct']:.2f}%\n")
        
        self.scenario_results.see(tk.END)
    
    def display_scenario_results(self, results):
        """Display scenario testing results"""
        self.scenario_results.delete(1.0, tk.END)
        
        self.scenario_results.insert(tk.END, "🧪 SCENARIO TEST RESULTS:\n\n")
        
        # Sort by return percentage
        sorted_results = sorted(results, key=lambda x: x['return_pct'], reverse=True)
        
        for result in sorted_results:
            icon = "🟢" if result['return_pct'] > 0 else "🔴"
            self.scenario_results.insert(tk.END, f"{icon} {result['name']}:\n")
            self.scenario_results.insert(tk.END, f"   Return: {result['return_pct']:.2f}%\n")
            self.scenario_results.insert(tk.END, f"   Drawdown: {result['max_drawdown']:.2f}%\n")
            self.scenario_results.insert(tk.END, f"   Win Rate: {result['win_rate']:.2f}%\n")
            self.scenario_results.insert(tk.END, f"   Trades: {result['trades']}\n")
            self.scenario_results.insert(tk.END, f"   Params: T:{result['params']['threshold']}% SL:{result['params']['stop_loss']}% TP:{result['params']['take_profit']}%\n\n")
        
        # Auto-apply best scenario if profitable
        if sorted_results and sorted_results[0]['return_pct'] > 0:
            best = sorted_results[0]
            self.price_threshold.set(best['params']['threshold'])
            self.stop_loss.set(best['params']['stop_loss'])
            self.take_profit.set(best['params']['take_profit'])
            
            self.scenario_results.insert(tk.END, f"✅ Best scenario ({best['name']}) parameters applied!\n")
        
        self.scenario_results.see(tk.END)
    
    def display_comprehensive_charts(self, result):
        """Display comprehensive charts for backtest results"""
        # Clear previous charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Create figure with subplots
        fig = plt.figure(figsize=(15, 10))
        
        # 1. Equity Curve (Top Left)
        ax1 = plt.subplot(2, 3, 1)
        if hasattr(result, 'balance_history') and result.balance_history:
            dates = []
            for trade in result.trades:
                # Parse timestamp if it's a string
                if isinstance(trade.timestamp, str):
                    dates.append(datetime.fromisoformat(trade.timestamp))
                else:
                    dates.append(trade.timestamp)
            balances = result.balance_history
            ax1.plot(dates, balances, 'b-', linewidth=2)
            ax1.fill_between(dates, result.initial_balance, balances, alpha=0.3)
            ax1.axhline(y=result.initial_balance, color='r', linestyle='--', alpha=0.5)
            ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Balance ($)')
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='x', rotation=45)
        else:
            # Simulate equity curve from trades
            balances = [result.initial_balance]
            balance = result.initial_balance
            dates = []
            for trade in result.trades:
                if trade.action == "BUY":
                    balance -= trade.amount_usd
                else:  # SELL
                    # Use profit_loss if profit_pct is not available
                    profit = getattr(trade, 'profit_pct', 0.0)
                    if profit == 0.0 and hasattr(trade, 'profit_loss'):
                        profit = (trade.profit_loss / trade.amount_usd) * 100
                    balance += trade.amount_usd * (1 + profit/100)
                balances.append(balance)
                # Parse timestamp if it's a string
                if isinstance(trade.timestamp, str):
                    dates.append(datetime.fromisoformat(trade.timestamp))
                else:
                    dates.append(trade.timestamp)
            
            if dates:
                ax1.plot(dates, balances[1:], 'b-', linewidth=2)
                ax1.fill_between(dates, result.initial_balance, balances[1:], alpha=0.3)
                ax1.axhline(y=result.initial_balance, color='r', linestyle='--', alpha=0.5)
            ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Balance ($)')
            ax1.grid(True, alpha=0.3)
        
        # 2. Trade Distribution (Top Center)
        ax2 = plt.subplot(2, 3, 2)
        if result.winning_trades > 0 or result.losing_trades > 0:
            labels = ['Winning', 'Losing']
            sizes = [result.winning_trades, result.losing_trades]
            colors = ['#4CAF50', '#F44336']
            explode = (0.1, 0)
            ax2.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                    shadow=True, startangle=90)
            ax2.set_title('Trade Distribution', fontsize=14, fontweight='bold')
        else:
            ax2.text(0.5, 0.5, 'No trades executed', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('Trade Distribution', fontsize=14, fontweight='bold')
        
        # 3. Monthly Returns (Top Right)
        ax3 = plt.subplot(2, 3, 3)
        if result.trades:
            # Group trades by month and calculate returns
            monthly_returns = {}
            for trade in result.trades:
                # Parse timestamp if it's a string
                if isinstance(trade.timestamp, str):
                    trade_date = datetime.fromisoformat(trade.timestamp)
                else:
                    trade_date = trade.timestamp
                month_key = trade_date.strftime('%Y-%m')
                if month_key not in monthly_returns:
                    monthly_returns[month_key] = 0
                # Get profit percentage
                profit = 0.0
                if hasattr(trade, 'profit_pct') and trade.profit_pct != 0:
                    profit = trade.profit_pct
                elif hasattr(trade, 'profit_loss') and trade.amount_usd > 0:
                    profit = (trade.profit_loss / trade.amount_usd) * 100
                monthly_returns[month_key] += profit
            
            if monthly_returns:
                months = list(monthly_returns.keys())
                returns = list(monthly_returns.values())
                colors = ['#4CAF50' if r > 0 else '#F44336' for r in returns]
                ax3.bar(months, returns, color=colors, alpha=0.7)
                ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                ax3.set_title('Monthly Returns (%)', fontsize=14, fontweight='bold')
                ax3.set_xlabel('Month')
                ax3.set_ylabel('Return %')
                ax3.tick_params(axis='x', rotation=45)
                ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Drawdown Chart (Bottom Left)
        ax4 = plt.subplot(2, 3, 4)
        if hasattr(result, 'drawdown_history') and result.drawdown_history:
            dates = [d[0] for d in result.drawdown_history]
            drawdowns = [d[1] for d in result.drawdown_history]
            ax4.fill_between(dates, 0, drawdowns, color='red', alpha=0.3)
            ax4.plot(dates, drawdowns, 'r-', linewidth=2)
            ax4.set_title('Drawdown History', fontsize=14, fontweight='bold')
            ax4.set_xlabel('Date')
            ax4.set_ylabel('Drawdown %')
            ax4.grid(True, alpha=0.3)
        else:
            ax4.text(0.5, 0.5, 'Drawdown data not available', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('Drawdown History', fontsize=14, fontweight='bold')
        
        # 5. Profit/Loss Distribution (Bottom Center)
        ax5 = plt.subplot(2, 3, 5)
        if result.trades:
            profits = []
            for trade in result.trades:
                if hasattr(trade, 'profit_pct') and trade.profit_pct != 0:
                    profits.append(trade.profit_pct)
                elif hasattr(trade, 'profit_loss'):
                    # Convert profit_loss to percentage
                    if trade.amount_usd > 0:
                        profit_pct = (trade.profit_loss / trade.amount_usd) * 100
                        profits.append(profit_pct)
            
            if profits:
                ax5.hist(profits, bins=20, color='blue', alpha=0.7, edgecolor='black')
                ax5.axvline(x=0, color='red', linestyle='--', linewidth=2)
                ax5.set_title('Profit/Loss Distribution', fontsize=14, fontweight='bold')
                ax5.set_xlabel('Profit %')
                ax5.set_ylabel('Frequency')
                ax5.grid(True, alpha=0.3, axis='y')
        
        # 6. Performance Summary (Bottom Right)
        ax6 = plt.subplot(2, 3, 6)
        ax6.axis('off')
        
        # Create performance summary text
        summary_text = f"""Performance Summary
        
Total Return: {result.return_percentage:.2f}%
Sharpe Ratio: {result.sharpe_ratio:.2f}
Win Rate: {result.win_rate:.2f}%
Profit Factor: {result.profit_factor:.2f}
Max Drawdown: {result.max_drawdown:.2f}%

Total Trades: {result.total_trades}
Avg Win: ${result.average_win:.2f}
Avg Loss: ${result.average_loss:.2f}
        """
        
        ax6.text(0.1, 0.9, summary_text, transform=ax6.transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))
        
        plt.tight_layout()
        
        # Add to chart frame
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Show success message
        messagebox.showinfo("Backtest Complete", 
                          f"Backtest completed successfully!\n\n"
                          f"Return: {result.return_percentage:.2f}%\n"
                          f"Total Trades: {result.total_trades}\n"
                          f"Win Rate: {result.win_rate:.2f}%")
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = UpbitTradingBotGUI()
    app.run() 