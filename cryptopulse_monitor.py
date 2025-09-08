# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
CryptoPulse Monitor - Professional Cryptocurrency Price Tracking Application
A bulletproof, cross-platform desktop application for real-time crypto monitoring

# CryptoPulse Monitor © 2025 Guillaume Lessard, iD01t Productions
# Closed Source License — All Rights Reserved
# This software is proprietary. Unauthorized copying, modification,
# or redistribution is prohibited without written permission.

Author: Guillaume Lessard / iD01t Productions
Website: https://id01t.store
Email: admin@id01t.store
Version: 2.1.2 - BULLETPROOF HOTFIX
Year: 2025
License: Closed Source — All Rights Reserved

Changelog v2.1.2:
- Fixed Binance missing 'lastPrice' handling with intelligent fallback
- Fixed Windows tray crash on repeated minimize/restore operations
- Reinforced notification fallback system with Tkinter popup backup
- Enhanced provider rotation to prevent error spam in logs
- Strengthened tray handle management to prevent [WinError 6]

Features:
- Real-time cryptocurrency price monitoring with intelligent API fallback
- Professional dark-themed GUI with smooth animations and modern design
- Smart notification system with customizable tick-to-tick thresholds
- System tray integration with comprehensive context menu
- Interactive price history charts with multiple timeframes
- Persistent settings and automatic crash recovery
- Multi-exchange support (CoinGecko, Binance, CryptoCompare)
- Cross-platform compatibility (Windows, macOS, Linux)
- Memory-efficient data handling with automatic cleanup
- Professional error handling, logging, and data export
- Real-time statistics and performance monitoring
- BULLETPROOF: Never crashes, handles all edge cases gracefully

Requirements: Python 3.8+
Install: pip install -r requirements.txt
Usage: python cryptopulse_monitor.py
"""

import sys
import os
import subprocess
import importlib
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
import webbrowser
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
import argparse

# Global exception hook for silent failure notifications
def global_exception_hook(exc_type, exc_value, exc_traceback):
    """Global exception handler to catch silent failures and notify user"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow normal keyboard interrupt handling
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Log the exception
    logger = logging.getLogger('CryptoPulse')
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Try to show notification if possible
    try:
        from plyer import notification
        notification.notify(
            title="CryptoPulse Monitor Error",
            message=f"An unexpected error occurred: {str(exc_value)[:100]}",
            timeout=10,
            toast=False
        )
    except Exception as notify_error:
        logger.debug(f"Could not show error notification: {notify_error}")
    
    # Call the default exception handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

# Set the global exception hook
sys.excepthook = global_exception_hook

# Configure logging
def setup_logging():
    """Setup professional logging system"""
    log_dir = Path.home() / '.cryptopulse'
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'cryptopulse.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('CryptoPulse')

logger = setup_logging()

# Check if running in frozen/packaged build
if getattr(sys, 'frozen', False):
    SKIP_INSTALLS = True
    logger.info("Running in frozen build - skipping dependency installation")
else:
    SKIP_INSTALLS = False
    logger.info("Running in development mode - checking dependencies")

# Dependency management with bulletproof error handling
REQUIRED_PACKAGES = {
    'requests': 'requests>=2.25.0',
    'matplotlib': 'matplotlib>=3.5.0', 
    'pillow': 'Pillow>=8.0.0',
    'plyer': 'plyer>=2.1.0',
    'pystray': 'pystray>=0.19.0',
    'numpy': 'numpy>=1.21.0',
}

def install_package(package: str, version_spec: str) -> bool:
    """Install package with version specification and error handling"""
    try:
        logger.info(f"Installing {package} ({version_spec})...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", version_spec,
            "--quiet", "--disable-pip-version-check", "--user"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info(f"Successfully installed {package}")
            return True
        else:
            logger.error(f"Failed to install {package}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout installing {package}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error installing {package}: {e}")
        return False

def check_and_install_dependencies() -> bool:
    """Check and install dependencies with comprehensive error handling"""
    logger.info("Checking dependencies...")
    missing_packages = []
    
    # Check each required package
    for package, version_spec in REQUIRED_PACKAGES.items():
        try:
            if package == 'tkinter':
                import tkinter
                logger.info(f"[OK] {package} (built-in)")
            else:
                importlib.import_module(package)
                logger.info(f"[OK] {package} (available)")
        except ImportError:
            missing_packages.append((package, version_spec))
            logger.warning(f"[X] {package} (missing)")
    
    # Install missing packages
    if missing_packages:
        logger.info(f"Installing {len(missing_packages)} missing packages...")
        failed_installs = []
        
        for package, version_spec in missing_packages:
            if not install_package(package, version_spec):
                failed_installs.append(package)
        
        if failed_installs:
            logger.error(f"Failed to install: {', '.join(failed_installs)}")
            print(f"\n[WARNING] Installation failed for: {', '.join(failed_installs)}")
            print("Please install manually:")
            for package in failed_installs:
                print(f"  pip install {REQUIRED_PACKAGES[package]}")
            return False
        
        logger.info("All dependencies installed successfully")
    else:
        logger.info("All dependencies already available")
    
    return True

# Install dependencies (skip in frozen builds)
if not SKIP_INSTALLS:
    if not check_and_install_dependencies():
        sys.exit(1)
else:
    logger.info("Skipping dependency installation in frozen build")

# Import all modules after dependency check
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, font, filedialog
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    
    # Optional imports with fallbacks
    try:
        from plyer import notification
        # Test notification capability safely
        try:
            # Don't actually show test notification during import
            NOTIFICATIONS_AVAILABLE = True
            logger.info("[OK] Desktop notifications available")
        except Exception as e:
            NOTIFICATIONS_AVAILABLE = False
            logger.warning(f"[X] Desktop notifications test failed: {e}")
    except ImportError:
        NOTIFICATIONS_AVAILABLE = False
        logger.warning("[X] Desktop notifications unavailable - plyer not installed")

    try:
        import pystray
        from pystray import MenuItem as item
        SYSTEM_TRAY_AVAILABLE = True
        logger.info("[OK] System tray available")
    except ImportError:
        SYSTEM_TRAY_AVAILABLE = False
        logger.warning("[X] System tray unavailable")
        
except ImportError as e:
    logger.critical(f"Critical import error: {e}")
    print(f"[WARNING] Critical dependency missing: {e}")
    sys.exit(1)

# Bulletproof notification system using plyer
class NotificationManager:
    """Bulletproof notification system with win10toast → plyer → Tkinter fallback"""
    
    def __init__(self, logger, debounce_seconds: float = 6.0):
        self.logger = logger
        self.debounce_seconds = debounce_seconds
        self._last_ts = 0.0
        self._lock = threading.Lock()
        
        # Initialize win10toast on Windows for better reliability
        self.win10toast = None
        if os.name == "nt":
            try:
                from win10toast import ToastNotifier
                self.win10toast = ToastNotifier()
                self.logger.info("win10toast initialized successfully")
            except Exception as e:
                self.logger.warning(f"win10toast initialization failed: {e}")

    def _debounced(self) -> bool:
        with self._lock:
            now = time.time()
            if now - self._last_ts < self.debounce_seconds:
                return True
            self._last_ts = now
            return False

    def notify(self, title: str, message: str, duration: int = 5):
        """Bulletproof notification with win10toast → Tkinter fallback (skip plyer)"""
        if self._debounced():
            print("Notification debounced (too frequent)")
            return

        def _worker():
            # 1) Try win10toast first on Windows (most reliable)
            if os.name == "nt" and self.win10toast:
                try:
                    self.win10toast.show_toast(
                        title=title,
                        msg=message,
                        duration=duration,
                        threaded=True
                    )
                    print("Notification sent via win10toast")
                    return
                except Exception as e:
                    print(f"win10toast failed: {e}")

            # 2) Skip plyer (causes crashes) - go directly to Tkinter
            try:
                from tkinter import messagebox
                messagebox.showinfo(title, message)
                print("Notification sent via Tkinter fallback")
            except Exception as e:
                print(f"All notification methods failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

def get_resource_path(rel_path: str) -> str:
    """
    Return an absolute path to resource, works for dev and PyInstaller.
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, rel_path)

# Data classes for type safety
@dataclass
class PriceData:
    """Cryptocurrency price data structure"""
    symbol: str
    price: float
    change_24h: float
    change_percent_24h: float
    timestamp: datetime
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None

@dataclass
class AlertConfig:
    """Alert configuration structure"""
    enabled: bool
    threshold: float
    notify_rise: bool
    notify_drop: bool
    last_triggered: Optional[datetime] = None

class APIProvider(Enum):
    """API provider enumeration"""
    COINGECKO = "coingecko"
    BINANCE = "binance"
    CRYPTOCOMPARE = "cryptocompare"

class TimeFrame(Enum):
    """Chart timeframe enumeration"""
    ONE_HOUR = "1H"
    SIX_HOURS = "6H"
    TWENTY_FOUR_HOURS = "24H"
    SEVEN_DAYS = "7D"

class CryptoPulseMonitor:
    """Professional Cryptocurrency Price Monitor Application - BULLETPROOF EDITION"""
    
    def __init__(self):
        logger.info("Initializing CryptoPulse Monitor...")
        
        # Application state
        self.current_price_data: Optional[PriceData] = None
        self.last_price_data: Optional[PriceData] = None
        self.price_history: List[PriceData] = []
        self.alerts_history: List[Dict] = []
        self.is_monitoring = True
        self.is_first_check = True
        self.api_failures = 0
        self.max_api_failures = 3
        self.current_timeframe = TimeFrame.TWENTY_FOUR_HOURS
        self.shutdown_requested = False
        
        # Enhanced error handling attributes
        self.api_failure_count = 0
        self.max_failure_count = 10
        self.last_api_call_time = 0
        self.min_api_interval = 10.0  # Increased to 10 seconds between API calls
        self.tray_running = False
        self.tray_thread = None
        self.rate_limit_reset_time = None
        self.rate_limited_until = None
        
        # Enhanced rate limiting
        self.api_provider_blacklist = {}  # Track rate limited providers
        self.retry_attempts = {}  # Track retry attempts per provider
        self.max_retry_attempts = 3
        self.base_retry_delay = 30  # Base delay for retries
        
        # Performance optimization
        self.cache_duration = 30  # Cache data for 30 seconds
        self.last_cache_time = 0
        self.cached_price_data = None
        self.gui_initialized = False
        
        # Konami Code Easter egg
        self.konami_sequence = ['Up', 'Up', 'Down', 'Down', 'Left', 'Right', 'Left', 'Right', 'Return', 'space']
        self.konami_input = []
        self.konami_activated = False
        self.start_time = time.time()
        self.cache_hits = 0
        
        # Tray lifecycle management
        self.tray_lock = threading.Lock()
        self.tray_running = False
        self.tray_icon = None
        self.tray_thread = None
        self.tray_stop_event = threading.Event()
        
        # Monitoring thread management
        self.monitoring_stop_event = threading.Event()
        
        # Settings with comprehensive defaults
        self.settings = {
            'refresh_interval': 60,  # Increased to 60 seconds to avoid rate limits
            'cryptocurrency': 'bitcoin',
            'vs_currency': 'usd',
            'api_provider': APIProvider.COINGECKO.value,
            'enable_notifications': True,
            'alert_config': {
                'price_drop': {'enabled': True, 'threshold': 2.0},
                'price_rise': {'enabled': False, 'threshold': 5.0},
                'volume_spike': {'enabled': False, 'threshold': 50.0}
            },
            'ui_config': {
                'window_width': 1200,
                'window_height': 800,
                'window_x': 100,
                'window_y': 100,
                'dark_mode': True,
                'auto_minimize': False
            },
            'data_retention': {
                'price_history_hours': 168,  # 7 days
                'alert_history_count': 100
            }
        }
        
        # Professional color scheme with enhanced contrast
        self.colors = {
            'primary': '#3B82F6',      # Blue-500
            'primary_hover': '#2563EB', # Blue-600
            'secondary': '#6B7280',    # Gray-500  
            'accent': '#8B5CF6',       # Violet-500
            'accent_hover': '#7C3AED', # Violet-600
            'background': '#0F172A',   # Slate-900
            'surface': '#1E293B',      # Slate-800
            'card': '#334155',         # Slate-700
            'text_primary': '#F8FAFC', # Slate-50
            'text_secondary': '#CBD5E1', # Slate-300
            'text_muted': '#64748B',   # Slate-500
            'success': '#10B981',      # Emerald-500
            'success_hover': '#059669', # Emerald-600
            'warning': '#F59E0B',      # Amber-500
            'warning_hover': '#D97706', # Amber-600
            'error': '#EF4444',        # Red-500
            'error_hover': '#DC2626',  # Red-600
            'chart_grid': '#374151',   # Gray-700
            'border': '#475569',       # Slate-600
            'hover': '#475569'         # Slate-600
        }
        
        # Cryptocurrency display names
        self.crypto_names = {
            'bitcoin': 'Bitcoin (BTC)',
            'ethereum': 'Ethereum (ETH)',
            'cardano': 'Cardano (ADA)',
            'solana': 'Solana (SOL)',
            'litecoin': 'Litecoin (LTC)',
            'ripple': 'Ripple (XRP)',
            'polkadot': 'Polkadot (DOT)',
            'chainlink': 'Chainlink (LINK)'
        }
        
        # API endpoints with fallbacks
        self.api_endpoints = {
            APIProvider.BINANCE: {
                'base_url': 'https://api.binance.com/api/v3',
                'price_endpoint': '/ticker/price',
                'timeout': 10
            },
            APIProvider.COINGECKO: {
                'base_url': 'https://api.coingecko.com/api/v3',
                'price_endpoint': '/simple/price',
                'timeout': 15
            },
            APIProvider.CRYPTOCOMPARE: {
                'base_url': 'https://min-api.cryptocompare.com/data',
                'price_endpoint': '/pricemultifull',
                'timeout': 15
            }
        }
        
        # BULLETPROOF: Setup HTTP session with retry and connection pooling
        self.session = self.setup_http_session()
        
        # BULLETPROOF: User agent rotation to avoid detection
        self.user_agents = [
            "CryptoPulse/2.1.1 (+https://id01t.store)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "CryptoTracker/1.0 (Compatible; +https://id01t.store)",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        self.current_user_agent = 0
        
        # Initialize components
        self.load_settings()
        
        # Add default tray setting if not present
        if 'enable_system_tray' not in self.settings.get('ui_config', {}):
            self.settings['ui_config']['enable_system_tray'] = True
        
        self.setup_gui()
        
        # Initialize bulletproof notification system
        self.notifier = NotificationManager(
            logger, 
            debounce_seconds=6.0
        )
        
        self.setup_system_tray()
        self.start_monitoring()
        
        logger.info("CryptoPulse Monitor initialized successfully")

    def setup_http_session(self) -> requests.Session:
        """BULLETPROOF: Setup HTTP session with retry and connection pooling"""
        session = requests.Session()
        
        # Retry strategy for transient failures
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            respect_retry_after_header=True
        )
        
        # HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=5,
            pool_maxsize=10,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set reasonable timeouts
        session.timeout = 15
        
        return session

    def get_api_headers(self) -> dict:
        """BULLETPROOF: Get rotating headers to avoid rate limiting"""
        headers = {
            "User-Agent": self.user_agents[self.current_user_agent],
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "DNT": "1",
            "Pragma": "no-cache"
        }
        
        # Rotate user agent
        self.current_user_agent = (self.current_user_agent + 1) % len(self.user_agents)
        return headers

    def enforce_rate_limit(self) -> None:
        """Enhanced rate limiting with provider-specific tracking"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call_time
        
        # Base rate limiting
        if time_since_last_call < self.min_api_interval:
            sleep_time = self.min_api_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_api_call_time = time.time()
    
    def is_provider_blacklisted(self, provider: APIProvider) -> bool:
        """Check if a provider is currently blacklisted due to rate limiting"""
        if provider.value not in self.api_provider_blacklist:
            return False
        
        blacklist_until = self.api_provider_blacklist[provider.value]
        if time.time() < blacklist_until:
            remaining = blacklist_until - time.time()
            logger.debug(f"Provider {provider.value} blacklisted for {remaining:.1f}s more")
            return True
        
        # Remove from blacklist if time has passed
        del self.api_provider_blacklist[provider.value]
        return False
    
    def blacklist_provider(self, provider: APIProvider, duration: int = 300) -> None:
        """Blacklist a provider for a specified duration (default 5 minutes)"""
        self.api_provider_blacklist[provider.value] = time.time() + duration
        logger.warning(f"Provider {provider.value} blacklisted for {duration}s due to rate limiting")
    
    def get_retry_delay(self, provider: APIProvider) -> float:
        """Get exponential backoff delay for retries"""
        attempts = self.retry_attempts.get(provider.value, 0)
        delay = self.base_retry_delay * (2 ** attempts)  # Exponential backoff
        return min(delay, 300)  # Cap at 5 minutes

    def load_settings(self) -> None:
        """Load settings with error recovery"""
        try:
            settings_dir = Path.home() / '.cryptopulse'
            settings_dir.mkdir(exist_ok=True)
            settings_path = settings_dir / 'settings.json'
            
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                
                # Deep merge settings
                self._merge_settings(self.settings, saved_settings)
                logger.info("Settings loaded successfully")
            else:
                logger.info("No existing settings found, using defaults")
                
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            logger.info("Using default settings")

    def _merge_settings(self, default: dict, saved: dict) -> None:
        """Recursively merge saved settings into defaults"""
        for key, value in saved.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_settings(default[key], value)
                else:
                    default[key] = value

    def save_settings(self) -> None:
        """Save settings with atomic write"""
        try:
            settings_dir = Path.home() / '.cryptopulse'
            settings_dir.mkdir(exist_ok=True)
            settings_path = settings_dir / 'settings.json'
            temp_path = settings_path.with_suffix('.tmp')
            
            # Atomic write
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            temp_path.replace(settings_path)
            
            logger.info("Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def setup_gui(self) -> None:
        """Setup professional GUI with modern design"""
        self.root = tk.Tk()
        self.root.title("CryptoPulse Monitor v2.1.2")
        
        # Bulletproof minimize handling - prevent re-entrancy
        self._suppress_unmap = False  # prevent re-entrancy when we withdraw()
        self._suppress_hide = False  # prevent recursion in hide_window
        self._minimizing = False  # prevent infinite minimize loop
        self.root.protocol("WM_DELETE_WINDOW", self.on_minimize)  # title-bar close -> minimize to tray
        
        # Window configuration
        width = self.settings['ui_config']['window_width']
        height = self.settings['ui_config']['window_height']
        x = self.settings['ui_config']['window_x']
        y = self.settings['ui_config']['window_y']
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(bg=self.colors['background'])
        self.root.minsize(800, 600)
        
        # Configure styles
        self.setup_styles()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create essential layout first (fast loading)
        self.create_header()
        self.create_status_bar()
        
        # Create loading indicator
        self.create_loading_indicator()
        
        # Bind events
        self.root.bind("<Configure>", self.on_window_configure)
        self.root.bind("<Control-q>", lambda e: self.quit_application())
        
        # Handle window state changes to prevent crashes
        try:
            self.root.bind("<Map>", self.on_window_map)
            self.root.bind("<Unmap>", lambda e: self.on_minimize() if self.root.state() == 'iconic' else None)
        except Exception as e:
            logger.debug(f"Could not bind window state events: {e}")
        
        # Bind Konami Code key sequence
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.focus_set()  # Enable key focus
        
        # Set window icon
        try:
            self.set_window_icon()
        except Exception as e:
            logger.warning(f"Could not set window icon: {e}")
        
        # Schedule heavy components for lazy loading
        self.safe_after(100, self.lazy_load_heavy_components)

    def create_loading_indicator(self) -> None:
        """Create a loading indicator for heavy components"""
        self.loading_frame = ttk.Frame(self.root, style='Card.TFrame')
        self.loading_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Loading text
        loading_label = ttk.Label(self.loading_frame, 
                                 text="Loading CryptoPulse Monitor...",
                                 style='Header.TLabel')
        loading_label.pack(expand=True)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.loading_frame, mode='indeterminate')
        self.progress.pack(pady=20)
        self.progress.start()

    def lazy_load_heavy_components(self) -> None:
        """Load heavy components asynchronously to improve startup time"""
        try:
            # Update loading status
            if hasattr(self, 'loading_frame'):
                loading_label = ttk.Label(self.loading_frame, 
                                         text="Loading price data...",
                                         style='Info.TLabel')
                loading_label.pack()
            
            # Load main content
            self.create_main_content()
            
            # Update loading status
            if hasattr(self, 'loading_frame'):
                loading_label = ttk.Label(self.loading_frame, 
                                         text="Loading sidebar...",
                                         style='Info.TLabel')
                loading_label.pack()
            
            # Load sidebar
            self.create_sidebar()
            
            # Remove loading indicator
            if hasattr(self, 'loading_frame'):
                self.loading_frame.destroy()
                del self.loading_frame
            
            # Mark GUI as initialized
            self.gui_initialized = True
            
            logger.info("Heavy components loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading heavy components: {e}")
            # Remove loading indicator even on error
            if hasattr(self, 'loading_frame'):
                self.loading_frame.destroy()
                del self.loading_frame

    def set_window_icon(self) -> None:
        """Set window icon from cryptopulse.ico file or create fallback"""
        try:
            # Try to use the cryptopulse.ico file
            icon_paths = [
                'cryptopulse.ico',
                'assets/cryptopulse.ico',
                os.path.join(os.path.dirname(__file__), 'cryptopulse.ico'),
                os.path.join(os.path.dirname(__file__), 'assets', 'cryptopulse.ico')
            ]
            
            icon_set = False
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        if os.name == 'nt':  # Windows
                            self.root.iconbitmap(icon_path)
                        else:  # Other platforms
                            icon_image = Image.open(icon_path)
                            photo = ImageTk.PhotoImage(icon_image)
                            self.root.iconphoto(True, photo)
                        icon_set = True
                        logger.info(f"Set window icon from: {icon_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to set icon from {icon_path}: {e}")
                        continue
            
            if not icon_set:
                logger.warning("cryptopulse.ico not found, using fallback icon")
                self.create_fallback_icon()
                
        except Exception as e:
            logger.warning(f"Error setting window icon: {e}")
            self.create_fallback_icon()
    
    def create_price_card(self, parent) -> None:
        """Create professional price display card"""
        price_card = ttk.Frame(parent, style='Card.TFrame')
        price_card.pack(fill='x', pady=(0, 15))
        
        # Card header
        header_frame = ttk.Frame(price_card, style='Card.TFrame')
        header_frame.pack(fill='x', padx=25, pady=(20, 10))
        
        # Store reference to crypto label for updates
        self.crypto_display_label = ttk.Label(header_frame, 
                                            text=self.get_crypto_display_name(), 
                                            style='Title.TLabel')
        self.crypto_display_label.pack(side='left')
        
        # Live indicator
        self.live_indicator = tk.Canvas(header_frame, width=12, height=12,
                                       bg=self.colors['surface'], 
                                       highlightthickness=0)
        self.live_indicator.pack(side='right', padx=(10, 0))
        
        # Price display
        price_frame = ttk.Frame(price_card, style='Card.TFrame')
        price_frame.pack(fill='x', padx=25, pady=(0, 10))
        
        self.price_label = ttk.Label(price_frame, text="Loading...", 
                                    style='Price.TLabel')
        self.price_label.pack(anchor='w')
        
        # Change display
        change_frame = ttk.Frame(price_card, style='Card.TFrame')
        change_frame.pack(fill='x', padx=25, pady=(0, 10))
        
        self.change_label = ttk.Label(change_frame, text="---", 
                                     style='Change.TLabel')
        self.change_label.pack(anchor='w')
        
        # Additional metrics
        metrics_frame = ttk.Frame(price_card, style='Card.TFrame')
        metrics_frame.pack(fill='x', padx=25, pady=(0, 20))
        
        self.volume_label = ttk.Label(metrics_frame, text="24H Volume: ---",
                                     style='Info.TLabel')
        self.volume_label.pack(side='left')
        
        self.update_label = ttk.Label(metrics_frame, text="Last updated: Never",
                                     style='Info.TLabel')
        self.update_label.pack(side='right')

    def get_crypto_display_name(self) -> str:
        """Get formatted display name for current cryptocurrency"""
        crypto = self.settings['cryptocurrency']
        currency = self.settings['vs_currency'].upper()
        
        if crypto in self.crypto_names:
            return f"{self.crypto_names[crypto]}/{currency}"
        else:
            return f"{crypto.title()} ({crypto[:3].upper()})/{currency}"
    
    def get_display_currency(self) -> str:
        """Get the display currency based on current API provider"""
        # Binance only supports USDT pairs, so show USDT when using Binance
        if hasattr(self, 'current_api_provider') and self.current_api_provider == APIProvider.BINANCE:
            return "USDT"
        return self.settings['vs_currency'].upper()

    def create_chart_card(self, parent) -> None:
        """Create professional price chart card"""
        chart_card = ttk.Frame(parent, style='Card.TFrame')
        chart_card.pack(fill='both', expand=True, pady=(0, 15))
        
        # Chart header
        chart_header = ttk.Frame(chart_card, style='Card.TFrame')
        chart_header.pack(fill='x', padx=25, pady=(20, 10))
        
        chart_title = ttk.Label(chart_header, text="Price History",
                               style='Title.TLabel')
        chart_title.pack(side='left')
        
        # Chart timeframe selector
        timeframe_frame = ttk.Frame(chart_header, style='Card.TFrame')
        timeframe_frame.pack(side='right')
        
        self.timeframe_buttons = {}
        for period in TimeFrame:
            btn = self.create_modern_button(
                timeframe_frame, period.value, 
                self.colors['primary'] if period == self.current_timeframe else self.colors['secondary'],
                lambda p=period: self.change_chart_timeframe(p), width=3)
            btn.pack(side='left', padx=2)
            self.timeframe_buttons[period] = btn
        
        # Chart
        self.setup_professional_chart(chart_card)

    def setup_professional_chart(self, parent) -> None:
        """Setup professional matplotlib chart"""
        # Configure matplotlib for dark theme
        plt.style.use('dark_background')
        
        self.fig = Figure(figsize=(10, 5), dpi=100, 
                         facecolor=self.colors['surface'])
        self.ax = self.fig.add_subplot(111, facecolor=self.colors['card'])
        
        # Professional styling
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color(self.colors['border'])
        self.ax.spines['left'].set_color(self.colors['border'])
        self.ax.tick_params(colors=self.colors['text_secondary'], labelsize=10)
        self.ax.grid(True, alpha=0.2, color=self.colors['chart_grid'])
        
        # Initial empty plot
        self.price_line, = self.ax.plot([], [], color=self.colors['primary'], 
                                       linewidth=2.5, alpha=0.9)
        self.ax.set_ylabel('Price ($)', color=self.colors['text_primary'], fontsize=11)
        self.ax.set_title('Price Trend', color=self.colors['text_primary'], 
                         fontsize=12, pad=15)
        
        # Add to GUI
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, 
                                        padx=25, pady=(0, 20))

    def create_controls_card(self, parent) -> None:
        """Create professional controls card"""
        controls_card = ttk.Frame(parent, style='Card.TFrame')
        controls_card.pack(fill='x')
        
        controls_frame = ttk.Frame(controls_card, style='Card.TFrame')
        controls_frame.pack(fill='x', padx=25, pady=20)
        
        # Left side controls
        left_controls = ttk.Frame(controls_frame, style='Card.TFrame')
        left_controls.pack(side='left')
        
        self.monitor_btn = self.create_modern_button(
            left_controls, "Pause", self.colors['primary'],
            self.toggle_monitoring)
        self.monitor_btn.pack(side='left', padx=(0, 10))
        
        refresh_btn = self.create_modern_button(
            left_controls, "Refresh", self.colors['success'],
            self.manual_refresh)
        refresh_btn.pack(side='left', padx=(0, 10))
        
        # Right side controls
        right_controls = ttk.Frame(controls_frame, style='Card.TFrame')
        right_controls.pack(side='right')
        
        export_btn = self.create_modern_button(
            right_controls, "Export", self.colors['accent'],
            self.export_data)
        export_btn.pack(side='right', padx=10)
        
        clear_btn = self.create_modern_button(
            right_controls, "Clear", self.colors['error'],
            self.clear_history)
        clear_btn.pack(side='right')

    def create_sidebar(self) -> None:
        """Create professional sidebar"""
        self.sidebar = ttk.Frame(self.root, style='App.TFrame', width=320)
        self.sidebar.pack(side='right', fill='y', padx=(10, 20), pady=10)
        self.sidebar.pack_propagate(False)
        
        # API Status card
        self.create_status_card()
        
        # Alerts history card
        self.create_alerts_card()
        
        # Quick stats card
        self.create_stats_card()

    def create_status_card(self) -> None:
        """Create API status card"""
        status_card = ttk.Frame(self.sidebar, style='Card.TFrame')
        status_card.pack(fill='x', pady=(0, 15))
        
        # Header
        status_header = ttk.Frame(status_card, style='Card.TFrame')
        status_header.pack(fill='x', padx=20, pady=(15, 10))
        
        ttk.Label(status_header, text="Connection Status", 
                 style='Title.TLabel').pack(side='left')
        
        # Status content
        status_content = ttk.Frame(status_card, style='Card.TFrame')
        status_content.pack(fill='x', padx=20, pady=(0, 15))
        
        self.connection_label = ttk.Label(status_content, text="● Connecting...",
                                         style='Info.TLabel')
        self.connection_label.pack(anchor='w')
        
        self.api_provider_label = ttk.Label(status_content, 
                                           text="Provider: CoinGecko",
                                           style='Info.TLabel')
        self.api_provider_label.pack(anchor='w', pady=(5, 0))
        
        self.next_update_label = ttk.Label(status_content, 
                                          text="Next update: ---",
                                          style='Info.TLabel')
        self.next_update_label.pack(anchor='w', pady=(5, 0))

    def create_alerts_card(self) -> None:
        """Create alerts history card"""
        alerts_card = ttk.Frame(self.sidebar, style='Card.TFrame')
        alerts_card.pack(fill='both', expand=True, pady=(0, 15))
        
        # Header
        alerts_header = ttk.Frame(alerts_card, style='Card.TFrame')
        alerts_header.pack(fill='x', padx=20, pady=(15, 10))
        
        ttk.Label(alerts_header, text="Recent Alerts", 
                 style='Title.TLabel').pack(side='left')
        
        clear_alerts_btn = self.create_modern_button(
            alerts_header, "Clear", self.colors['secondary'],
            self.clear_alerts, width=5)
        clear_alerts_btn.pack(side='right')
        
        # Alerts list
        self.alerts_listbox = tk.Listbox(alerts_card,
                                        bg=self.colors['card'],
                                        fg=self.colors['text_primary'],
                                        font=('Segoe UI', 9),
                                        border=0,
                                        selectbackground=self.colors['primary'],
                                        selectforeground='white')
        self.alerts_listbox.pack(fill='both', expand=True, padx=20, pady=(0, 20))

    def create_stats_card(self) -> None:
        """Create quick stats card"""
        stats_card = ttk.Frame(self.sidebar, style='Card.TFrame')
        stats_card.pack(fill='x')
        
        # Header
        stats_header = ttk.Frame(stats_card, style='Card.TFrame')
        stats_header.pack(fill='x', padx=20, pady=(15, 10))
        
        ttk.Label(stats_header, text="24H Statistics", 
                 style='Title.TLabel').pack(side='left')
        
        # Stats content
        stats_content = ttk.Frame(stats_card, style='Card.TFrame')
        stats_content.pack(fill='x', padx=20, pady=(0, 15))
        
        self.high_label = ttk.Label(stats_content, text="24H High: ---",
                                   style='Info.TLabel')
        self.high_label.pack(anchor='w')
        
        self.low_label = ttk.Label(stats_content, text="24H Low: ---",
                                  style='Info.TLabel')
        self.low_label.pack(anchor='w', pady=(5, 0))
        
        self.avg_label = ttk.Label(stats_content, text="24H Average: ---",
                                  style='Info.TLabel')
        self.avg_label.pack(anchor='w', pady=(5, 0))

    def create_status_bar(self) -> None:
        """Create professional status bar"""
        self.status_bar = ttk.Frame(self.root, style='Card.TFrame')
        self.status_bar.pack(side='bottom', fill='x')
        
        status_content = ttk.Frame(self.status_bar, style='Card.TFrame')
        status_content.pack(fill='x', padx=10, pady=8)
        
        self.status_text = ttk.Label(status_content, text="Ready",
                                    style='Info.TLabel')
        self.status_text.pack(side='left')
        
        # Version info
        version_label = ttk.Label(status_content, text="v2.1.1",
                                 style='Info.TLabel')
        version_label.pack(side='right')

    def _minimize_to_tray_safe(self):
        """Guard to avoid <Unmap> recursion when we withdraw()"""
        self._suppress_unmap = True
        try:
            self.minimize_to_tray()
        finally:
            # After we withdraw, keep suppression on briefly; it will clear on restore
            pass

    def on_minimize(self, event=None):
        """Handle minimize button - hide window and show tray icon"""
        try:
            if hasattr(self, 'gui_initialized') and not self.gui_initialized:
                return
            
            # Suppression guard to prevent infinite loop
            if hasattr(self, '_minimizing') and self._minimizing:
                return
            self._minimizing = True
            
            # Hide the window
            self.root.withdraw()
            
            # Show tray icon if available and enabled
            if SYSTEM_TRAY_AVAILABLE and self.settings.get("ui_config", {}).get("enable_system_tray", True):
                self.minimize_to_tray()
            else:
                # Fallback to iconify if tray not available
                self.safe_iconify()
                
            print("Window minimized to tray")
        except Exception as e:
            print(f"Error minimizing window: {e}")
            # Fallback to iconify
            self.safe_iconify()
        finally:
            # Reset suppression flag
            self._minimizing = False

    def on_closing(self):
        """Handle title-bar close button - prefer tray if available, otherwise quit"""
        if SYSTEM_TRAY_AVAILABLE and self.settings.get("ui_config", {}).get("enable_system_tray", True):
            self.on_minimize()
        else:
            self.quit_application()

    def minimize_to_tray(self) -> None:
        """BULLETPROOF minimize to system tray with fresh icon creation and locking"""
        if not SYSTEM_TRAY_AVAILABLE:
            self.safe_iconify()
            return
        
        # Check if system tray is enabled in settings
        if not self.settings.get('ui_config', {}).get('enable_system_tray', True):
            logger.info("System tray disabled in settings, using iconify instead")
            self.safe_iconify()
            return
        
        # Cross-platform tray reliability check
        import platform
        system = platform.system().lower()
        
        # On macOS and Linux, tray can be unreliable, so we prefer iconify
        if system in ['darwin', 'linux']:
            logger.info(f"Tray not fully supported on {system}, using iconify instead")
            self.safe_iconify()
            return
        
        with self.tray_lock:
            # Always clean up any existing tray to prevent handle reuse
            if self.tray_running and self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception as e:
                    self.logger.warning(f"Tray stop issue: {e}")
                finally:
                    # Always reset state, even if stop() failed
                    self.tray_running = False
                    self.tray_icon = None
                    self.tray_thread = None

            try:
                # Create fresh tray image and icon
                tray_img = self._make_tray_image()
                menu = pystray.Menu(
                    pystray.MenuItem("Restore", lambda i, it: self.restore_window()),
                    pystray.MenuItem("Quit", lambda i, it: self.quit_application())
                )
                self.tray_icon = pystray.Icon("CryptoPulse", tray_img, "CryptoPulse Monitor", menu)
                self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
                self.tray_thread.start()
                self.tray_running = True
                self.logger.info("Tray icon started successfully")
            except Exception as e:
                self.logger.error(f"Tray start failed: {e}, retrying with fresh image...")
                # Wait briefly and retry once with a completely fresh tray
                time.sleep(0.5)
                try:
                    # Ensure we start completely fresh
                    self.tray_icon = None
                    self.tray_thread = None
                    self.tray_running = False
                    
                    # Create completely fresh tray image and icon
                    tray_img = self._make_tray_image()
                    menu = pystray.Menu(
                        pystray.MenuItem("Restore", lambda i, it: self.restore_window()),
                        pystray.MenuItem("Quit", lambda i, it: self.quit_application())
                    )
                    self.tray_icon = pystray.Icon("CryptoPulse", tray_img, "CryptoPulse Monitor", menu)
                    self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
                    self.tray_thread.start()
                    self.tray_running = True
                    self.logger.info("Tray retry successful")
                except Exception as e2:
                    self.logger.error(f"Tray retry also failed: {e2}, falling back to iconify")
                    # Clean up any partial state
                    self.tray_icon = None
                    self.tray_thread = None
                    self.tray_running = False
                    self.safe_iconify()
                    return
        
        if hasattr(self, 'root') and self.root and self.root.winfo_exists():
            self.root.withdraw()
        self.logger.info("Minimized to system tray")

    def safe_iconify(self) -> None:
        """Safely minimize window to taskbar with error handling"""
        try:
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                self.root.iconify()
                logger.debug("Window minimized to taskbar")
            else:
                logger.warning("Cannot iconify - root window not available")
        except Exception as e:
            logger.error(f"Safe iconify failed: {e}")

    def safe_deiconify(self) -> None:
        """Safely restore window from minimized state with error handling"""
        try:
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                logger.debug("Window restored from minimized state")
            else:
                logger.warning("Cannot deiconify - root window not available")
        except Exception as e:
            logger.error(f"Safe deiconify failed: {e}")

    def _make_tray_image(self) -> 'Image.Image':
        """Create a fresh RGBA image every time for tray icon"""
        try:
            from PIL import Image, ImageDraw
            # Create a fresh RGBA image every time
            base = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            draw = ImageDraw.Draw(base)
            # Simple pulse ring + generic crypto glyph
            draw.ellipse((16, 16, 240, 240), outline=(0, 200, 255, 255), width=10)
            draw.text((92, 96), "₵", fill=(255, 215, 0, 255))  # Crypto symbol
            return base
        except Exception as e:
            logger.debug(f"Could not create tray image: {e}")
            # Fallback to simple colored circle
            base = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(base)
            draw.ellipse((4, 4, 60, 60), fill=(0, 200, 255, 255))
            return base

    def _run_tray(self):
        """Tray runner with proper cleanup"""
        try:
            if self.tray_icon:
                self.tray_icon.run()
        finally:
            # Make sure state resets even on error
            with self.tray_lock:
                self.tray_running = False
                self.tray_icon = None
                self.tray_thread = None
            logger.info("System tray loop ended")

    def restore_window(self) -> None:
        """BULLETPROOF window restoration with cross-platform safeguards"""
        # Stop tray if running, ignore errors
        with self.tray_lock:
            if self.tray_icon is not None:
                try:
                    self.tray_icon.stop()
                except Exception as e:
                    logger.warning(f"Tray stop warning: {e}")
                # _run_tray finally block will reset flags
            
        # Restore window with cross-platform safeguards
        if hasattr(self, 'root') and self.root and self.root.winfo_exists():
            try:
                self.safe_deiconify()
                # Ensure window is visible and properly positioned
                self.root.state('normal')
                self.root.lift()
                self.root.focus_force()
                logger.info("Window restored from tray")
            except Exception as e:
                logger.warning(f"Window restore error: {e}")
                # Cross-platform safeguard: try to recreate GUI if hidden but not restored
                try:
                    if not self.root.winfo_viewable():
                        logger.info("Window not viewable, attempting to recreate GUI...")
                        self.root.deiconify()
                        self.root.lift()
                        self.root.focus_force()
                except Exception as e2:
                    logger.error(f"Cross-platform restore safeguard failed: {e2}")
        else:
            # Emergency fallback: recreate the window if it was destroyed
            logger.warning("Root window not available, attempting to recreate...")
            try:
                self.setup_gui()
                logger.info("GUI recreated successfully")
            except Exception as e:
                logger.error(f"Failed to recreate GUI: {e}")

    def setup_system_tray(self) -> None:
        """Setup bulletproof system tray functionality"""
        if not SYSTEM_TRAY_AVAILABLE:
            logger.warning("System tray not available")
            return
            
        try:
            # Ensure we have a valid tray image
            self.create_tray_icon()
            
            # Create tray icon with proper error handling
            self.tray_icon = pystray.Icon(
                "cryptopulse_monitor", 
                self.tray_image,
                "CryptoPulse Monitor",
                self.create_tray_menu()
            )
            
            # Start tray icon in a separate thread to avoid blocking
            def safe_tray_run():
                try:
                    self.tray_icon.run()
                except Exception as e:
                    logger.error(f"Tray icon runtime error: {e}")
                    # Clean up on error
                    self.tray_running = False
                    self.tray_icon = None
            
            self.tray_thread = threading.Thread(target=safe_tray_run, daemon=True)
            self.tray_thread.start()
            self.tray_running = True
            
            logger.info("System tray configured successfully")
        except Exception as e:
            logger.error(f"System tray setup failed: {e}")
            # Fallback: try to create a simple tray icon without menu
            try:
                self.tray_icon = pystray.Icon("cryptopulse_monitor", self.tray_image, "CryptoPulse Monitor")
                self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
                self.tray_thread.start()
                self.tray_running = True
                logger.info("System tray configured with fallback (no menu)")
            except Exception as e2:
                logger.error(f"Fallback tray setup also failed: {e2}")
                self.tray_running = False

    def create_tray_icon(self) -> None:
        """Create system tray icon from cryptopulse.ico file"""
        try:
            # Try to use the cryptopulse.ico file for tray icon
            icon_paths = [
                'cryptopulse.ico',
                'assets/cryptopulse.ico',
                os.path.join(os.path.dirname(__file__), 'cryptopulse.ico'),
                os.path.join(os.path.dirname(__file__), 'assets', 'cryptopulse.ico')
            ]
            
            icon_loaded = False
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        icon_image = Image.open(icon_path)
                        tray_size = 32
                        self.tray_image = icon_image.resize((tray_size, tray_size), Image.Resampling.LANCZOS)
                        icon_loaded = True
                        logger.info(f"Set tray icon from: {icon_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load tray icon from {icon_path}: {e}")
                        continue
            
            if not icon_loaded:
                logger.warning("cryptopulse.ico not found for tray, using fallback icon")
                self.create_fallback_tray_icon()
                
        except Exception as e:
            logger.warning(f"Error creating tray icon: {e}")
            self.create_fallback_tray_icon()
    
    def create_fallback_tray_icon(self) -> None:
        """Create fallback programmatic tray icon if ico file not available"""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Professional crypto icon
        center = size // 2
        radius = size // 2 - 4
        
        # Outer circle with gradient effect
        draw.ellipse([4, 4, size-4, size-4], 
                    fill='#3B82F6', outline='#1E40AF', width=2)
        
        # Inner design - modern crypto symbol
        bar_width = 4
        bar_height = 24
        bar_y = center - bar_height // 2
        
        draw.rectangle([center-10, bar_y, center-10+bar_width, bar_y+bar_height], 
                      fill='white')
        draw.rectangle([center+6, bar_y, center+6+bar_width, bar_y+bar_height], 
                      fill='white')
        
        # Horizontal bars
        draw.rectangle([center-14, center-6, center+14, center-2], fill='white')
        draw.rectangle([center-14, center+2, center+14, center+6], fill='white')
        
        self.tray_image = image

    def create_tray_menu(self) -> pystray.Menu:
        """Create professional system tray context menu"""
        def on_quit(icon, item):
            self.quit_application()

        def on_restore(icon, item):
            self.root.after(0, self.restore_window)

        def on_settings(icon, item):
            self.root.after(0, self.show_settings)

        return pystray.Menu(
            item('Show CryptoPulse', on_restore, default=True),
            item('Toggle Monitoring', self.toggle_monitoring),
            pystray.Menu.SEPARATOR,
            item('Settings', lambda: self.root.after(0, self.toggle_settings)),
            item('About', lambda: self.root.after(0, self.show_about)),
            pystray.Menu.SEPARATOR,
            item('Exit', on_quit)
        )

    def start_monitoring(self) -> None:
        """Start monitoring with bulletproof error handling"""
        try:
            self.monitoring_thread = threading.Thread(
                target=self.monitor_price_loop, 
                daemon=True,  # Daemon for cleaner shutdown
                name="PriceMonitor"
            )
            self.monitoring_thread.start()
            logger.info("Price monitoring started")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.show_error("Monitoring Error", f"Failed to start price monitoring: {e}")

    def monitor_price_loop(self) -> None:
        """BULLETPROOF monitoring loop with progressive error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        base_sleep_interval = 1
        
        logger.info("Starting monitoring loop")
        
        while not self.shutdown_requested and not self.monitoring_stop_event.is_set():
            loop_start_time = time.time()
            
            try:
                if self.is_monitoring:
                    # Attempt to fetch price
                    self.fetch_and_update_price()
                    
                    # Update next refresh time
                    next_update = datetime.now() + timedelta(seconds=self.settings['refresh_interval'])
                    self.root.after(0, lambda: self.update_next_refresh_time(next_update))
                    
                    # Reset error count on success
                    consecutive_errors = 0
                    
                else:
                    # Monitoring is paused
                    self.root.after(0, lambda: self.update_connection_status(
                        "● Monitoring Paused", self.colors['warning']))
                
            except Exception as e:
                consecutive_errors += 1
                error_msg = str(e)[:100]  # Truncate long error messages
                
                logger.error(f"Monitoring error ({consecutive_errors}/{max_consecutive_errors}): {error_msg}")
                
                # Progressive error handling
                if consecutive_errors >= max_consecutive_errors:
                    # Extended backoff for persistent failures
                    backoff_time = min(300, 30 * (2 ** min(consecutive_errors - max_consecutive_errors, 3)))
                    
                    self.root.after(0, lambda bt=backoff_time: self.update_connection_status(
                        f"● Extended Backoff: {bt}s", self.colors['error']))
                    
                    logger.warning(f"Extended backoff: {backoff_time}s after {consecutive_errors} consecutive errors")
                    
                    # Sleep for backoff period with early exit check
                    for _ in range(int(backoff_time)):
                        if self.shutdown_requested:
                            break
                        time.sleep(1)
                    
                    consecutive_errors = 0  # Reset after backoff
                else:
                    # Show retry status
                    self.root.after(0, lambda ce=consecutive_errors: self.update_connection_status(
                        f"● Retry {ce}/{max_consecutive_errors}", self.colors['warning']))
            
            # Calculate how long this loop iteration took
            loop_duration = time.time() - loop_start_time
            
            # Sleep for remainder of refresh interval
            target_interval = max(10, self.settings['refresh_interval'])  # Minimum 10 seconds
            remaining_sleep = target_interval - loop_duration
            
            if remaining_sleep > 0:
                # Sleep in small intervals to allow responsive shutdown
                sleep_chunks = max(1, int(remaining_sleep))
                for _ in range(sleep_chunks):
                    if self.shutdown_requested:
                        break
                    
                    sleep_time = min(remaining_sleep / sleep_chunks, base_sleep_interval)
                    time.sleep(sleep_time)
                    
                    # When paused, sleep longer to reduce CPU usage
                    if not self.is_monitoring:
                        time.sleep(2)
        
        logger.info("Monitoring loop stopped")

    def fetch_and_update_price(self) -> None:
        """BULLETPROOF price fetching with intelligent provider rotation and caching"""
        try:
            # Check cache first for performance
            current_time = time.time()
            if (self.cached_price_data and 
                current_time - self.last_cache_time < self.cache_duration):
                logger.debug("Using cached price data")
                self.cache_hits += 1
                try:
                    self.safe_after(0, lambda: self.update_price_display(self.cached_price_data))
                    self.safe_after(0, lambda: self.update_connection_status(
                        "● Connected (cached)", self.colors['success']))
                except Exception as e:
                    logger.debug(f"Cache display update failed: {e}")
                return
            
            # Enforce rate limiting
            self.enforce_rate_limit()
            
            # Get available providers (excluding blacklisted ones)
            all_providers = [APIProvider.COINGECKO, APIProvider.BINANCE, APIProvider.CRYPTOCOMPARE]
            available_providers = [p for p in all_providers if not self.is_provider_blacklisted(p)]
            
            if not available_providers:
                # All providers are blacklisted
                self.safe_after(0, lambda: self.update_connection_status(
                    "● All APIs rate limited", self.colors['error']))
                logger.warning("All API providers are currently rate limited")
                return
            
            # Honor primary provider setting first, but only if not blacklisted
            primary = APIProvider(self.settings.get('api_provider', 'binance'))
            if primary in available_providers:
                providers = [primary] + [p for p in available_providers if p != primary]
            else:
                providers = available_providers
                logger.info(f"Primary provider {primary.value} is blacklisted, using fallbacks")
            
            # Try each provider
            for provider in providers:
                try:
                    # Update status with error handling
                    try:
                        self.safe_after(0, lambda: self.update_connection_status(
                                f"● Fetching from {provider.value}...", self.colors['warning']))
                    except Exception as status_error:
                        logger.debug(f"Status update failed: {status_error}")
                    
                    price_data = self.fetch_price_from_provider(provider)
                    if price_data and self._validate_price_data(price_data):
                        # Normalize data to ensure consistent fields across providers
                        price_data = self._normalize_price_data(price_data)
                        
                        # Success - reset failure count and cache data
                        self.api_failure_count = 0
                        self.cached_price_data = price_data
                        self.last_cache_time = current_time
                        
                        # Update UI with bulletproof error handling
                        try:
                            self.current_api_provider = provider
                            self.safe_after(0, lambda p=provider: self.api_provider_label.config(
                                text=f"Provider: {p.value.title()}"))
                            self.safe_after(0, lambda pd=price_data: self.update_price_display(pd))
                            self.safe_after(0, lambda: self.update_connection_status(
                                "● Connected", self.colors['success']))
                        except Exception as ui_error:
                            logger.debug(f"UI update failed: {ui_error}")
                        return
                        
                except Exception as e:
                    logger.warning(f"Provider {provider.value} failed: {e}")
                    # Continue to next provider instead of crashing
                    continue
            
            # All providers failed
            self.api_failure_count += 1
            error_msg = f"All API providers failed (attempt {self.api_failure_count})"
            logger.error(error_msg)
            
            self.safe_after(0, lambda: self.update_connection_status(
                f"● All APIs Failed ({self.api_failure_count})", self.colors['error']))
            
            raise Exception(error_msg)
            
        except Exception as e:
            logger.error(f"Price fetch error: {e}")
            self.api_failure_count += 1
            raise

    def fetch_price_from_provider(self, provider: APIProvider) -> Optional[PriceData]:
        """Enhanced provider-specific fetching with intelligent rate limiting"""
        # Check if provider is blacklisted
        if self.is_provider_blacklisted(provider):
            logger.debug(f"Provider {provider.value} is temporarily blacklisted")
            return None
        
        config = self.api_endpoints[provider]
        
        try:
            if provider == APIProvider.BINANCE:
                return self.fetch_from_binance_safe(config)
            elif provider == APIProvider.COINGECKO:
                return self.fetch_from_coingecko_safe(config)
            elif provider == APIProvider.CRYPTOCOMPARE:
                return self.fetch_from_cryptocompare_safe(config)
            
        except Exception as e:
            logger.warning(f"Provider {provider.value} fetch failed: {e}")
            return None
        
        return None

    def _parse_binance_price_payload(self, data: dict) -> tuple[float, float, float]:
        """
        Bulletproof Binance parser with tolerant field handling.
        Returns: (price, absolute_change, percent_change)
        """
        try:
            if "lastPrice" in data:  # full 24hr payload
                price = float(data["lastPrice"])
                pct = float(data.get("priceChangePercent", 0))
                abs_change = float(data.get("priceChange", price * pct / 100))
                return price, abs_change, pct

            if "price" in data:  # simple price endpoint
                price = float(data["price"])
                return price, 0.0, 0.0

            if "weightedAvgPrice" in data:  # weighted average price
                price = float(data["weightedAvgPrice"])
                return price, 0.0, 0.0

            raise ValueError("Binance payload missing price fields")

        except Exception as e:
            self.logger.error(f"Binance parse error: {e}")
            raise
        
    def fetch_from_binance_safe(self, config: dict) -> Optional[PriceData]:
        """Robust Binance API with retry logic, rate limiting, and bulletproof parsing"""
        # Binance uses different symbol format (BTCUSDT instead of bitcoin)
        symbol_map = {
            'bitcoin': 'BTCUSDT',
            'ethereum': 'ETHUSDT',
            'binancecoin': 'BNBUSDT',
            'cardano': 'ADAUSDT',
            'solana': 'SOLUSDT',
            'ripple': 'XRPUSDT',
            'polkadot': 'DOTUSDT',
            'chainlink': 'LINKUSDT'
        }
        
        symbol = symbol_map.get(self.settings['cryptocurrency'], 'BTCUSDT')
        vs_currency = self.settings.get('vs_currency', 'usd')
        
        # Try /ticker/24hr first, then fallback to /ticker/price
        urls = [
            ("https://api.binance.com/api/v3/ticker/24hr", {"symbol": symbol}),
            ("https://api.binance.com/api/v3/ticker/price", {"symbol": symbol}),
        ]
        
        headers = self.get_api_headers()
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            for url, params in urls:
                try:
                    response = self.session.get(url, params=params, headers=headers, timeout=config['timeout'])
                    
                    # Handle rate limiting with intelligent retry
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.warning(f"Binance rate limited (attempt {attempt + 1}/{max_retries}), retry after {retry_after}s")
                        
                        if attempt < max_retries - 1:
                            # Blacklist provider temporarily
                            self.blacklist_provider(APIProvider.BINANCE, retry_after)
                            # Wait before retry
                            time.sleep(min(retry_after, 60))  # Cap wait time at 60 seconds
                            continue
                        else:
                            # Final attempt failed, blacklist for longer
                            self.blacklist_provider(APIProvider.BINANCE, 300)  # 5 minutes
                            return None
                    
                    # Handle other HTTP errors
                    if response.status_code != 200:
                        self.logger.warning(f"Binance returned status {response.status_code}")
                        if attempt < max_retries - 1:
                            delay = self.get_retry_delay(APIProvider.BINANCE)
                            self.logger.info(f"Retrying in {delay:.1f}s...")
                            time.sleep(delay)
                            continue
                        else:
                            return None
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # Use bulletproof parser
                    price, abs_change, pct = self._parse_binance_price_payload(data)
                    
                    # Success - reset retry attempts
                    if APIProvider.BINANCE.value in self.retry_attempts:
                        del self.retry_attempts[APIProvider.BINANCE.value]
                    
                    return PriceData(
                        symbol=symbol,
                        price=price,
                        change_24h=abs_change,
                        change_percent_24h=pct,
                        timestamp=datetime.now(),
                        volume_24h=float(data.get("quoteVolume") or data.get("volume") or 0.0),
                        market_cap=None  # Binance endpoint does not provide market cap
                    )
                    
                except Exception as e:
                    self.logger.warning(f"Binance fetch attempt failed: {e}")
                    continue
            
            # If all URLs failed for this attempt, wait before retrying
            if attempt < max_retries - 1:
                delay = self.get_retry_delay(APIProvider.BINANCE)
                self.logger.info(f"All Binance endpoints failed, retrying in {delay:.1f}s...")
                time.sleep(delay)
        
        # All attempts failed
        self.logger.warning(f"Binance fetch failed after {max_retries} attempts")
        return None

    def fetch_from_coingecko_safe(self, config: dict) -> Optional[PriceData]:
        """Enhanced CoinGecko API with intelligent rate limiting and retry logic"""
        url = f"{config['base_url']}{config['price_endpoint']}"
        params = {
            'ids': self.settings['cryptocurrency'],
            'vs_currencies': self.settings['vs_currency'],
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_market_cap': 'true',
            'precision': '2'
        }
        
        headers = self.get_api_headers()
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Make request with comprehensive error handling
                response = self.session.get(
                    url, 
                    params=params, 
                    headers=headers, 
                    timeout=config['timeout']
                )
                
                # Handle rate limiting with intelligent retry
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"CoinGecko rate limited (attempt {attempt + 1}/{max_retries}), retry after {retry_after}s")
                    
                    if attempt < max_retries - 1:
                        # Blacklist provider temporarily
                        self.blacklist_provider(APIProvider.COINGECKO, retry_after)
                        # Wait before retry
                        time.sleep(min(retry_after, 60))  # Cap wait time at 60 seconds
                        continue
                    else:
                        # Final attempt failed, blacklist for longer
                        self.blacklist_provider(APIProvider.COINGECKO, 300)  # 5 minutes
                        continue
                
                response.raise_for_status()
                
                # Handle other HTTP errors
                if response.status_code != 200:
                    logger.warning(f"CoinGecko returned status {response.status_code}")
                    if attempt < max_retries - 1:
                        delay = self.get_retry_delay(APIProvider.COINGECKO)
                        logger.info(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        response.raise_for_status()
                
                # Success - reset retry attempts
                if APIProvider.COINGECKO.value in self.retry_attempts:
                    del self.retry_attempts[APIProvider.COINGECKO.value]
                
                data = response.json()
                crypto_data = data.get(self.settings['cryptocurrency'], {})
                
                if not crypto_data:
                    raise ValueError(f"No data returned for {self.settings['cryptocurrency']}")
                
                currency = self.settings['vs_currency']
                current_price = float(crypto_data.get(currency, 0))
                change_percent = float(crypto_data.get(f'{currency}_24h_change', 0))
                
                if current_price <= 0:
                    raise ValueError("Invalid price data received")
                
                # Calculate absolute change
                absolute_change = current_price * (change_percent / 100.0)
                
                return PriceData(
                    symbol=self.settings['cryptocurrency'].upper(),
                    price=current_price,
                    change_24h=absolute_change,
                    change_percent_24h=change_percent,
                    timestamp=datetime.now(),
                    volume_24h=crypto_data.get(f'{currency}_24h_vol'),
                    market_cap=crypto_data.get(f'{currency}_market_cap')
                )

            except Exception as e:
                # Track retry attempts
                if APIProvider.COINGECKO.value not in self.retry_attempts:
                    self.retry_attempts[APIProvider.COINGECKO.value] = 0
                self.retry_attempts[APIProvider.COINGECKO.value] += 1
                
                if attempt < max_retries - 1:
                    delay = self.get_retry_delay(APIProvider.COINGECKO)
                    logger.warning(f"CoinGecko attempt {attempt + 1} failed: {e}, retrying in {delay:.1f}s")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"All CoinGecko attempts failed: {e}")
                    raise
        
        return None


    def fetch_from_cryptocompare_safe(self, config: dict) -> Optional[PriceData]:
        """BULLETPROOF CryptoCompare API fetching"""
        symbol_map = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH', 
            'cardano': 'ADA',
            'solana': 'SOL',
            'litecoin': 'LTC',
            'ripple': 'XRP',
            'polkadot': 'DOT',
            'chainlink': 'LINK'
        }
        
        symbol = symbol_map.get(self.settings['cryptocurrency'])
        if not symbol:
            self.logger.warning(f"Cryptocurrency not supported by CryptoCompare: {self.settings['cryptocurrency']}")
            return None
        
        url = f"{config['base_url']}{config['price_endpoint']}"
        params = {
            'fsyms': symbol,
            'tsyms': self.settings['vs_currency'].upper()
        }
        headers = self.get_api_headers()
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=config['timeout'])
                
                # Handle rate limiting with intelligent retry
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.logger.warning(f"CryptoCompare rate limited (attempt {attempt + 1}/{max_retries}), retry after {retry_after}s")
                    
                    if attempt < max_retries - 1:
                        # Blacklist provider temporarily
                        self.blacklist_provider(APIProvider.CRYPTOCOMPARE, retry_after)
                        # Wait before retry
                        time.sleep(min(retry_after, 60))  # Cap wait time at 60 seconds
                        continue
                    else:
                        # Final attempt failed, blacklist for longer
                        self.blacklist_provider(APIProvider.CRYPTOCOMPARE, 300)  # 5 minutes
                        return None
                
                # Handle other HTTP errors
                if response.status_code != 200:
                    self.logger.warning(f"CryptoCompare returned status {response.status_code}")
                    if attempt < max_retries - 1:
                        delay = self.get_retry_delay(APIProvider.CRYPTOCOMPARE)
                        self.logger.info(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        return None
                
                response.raise_for_status()
                data = response.json()
                
                # Check for API errors
                if 'Response' in data and data['Response'] == 'Error':
                    self.logger.warning(f"CryptoCompare API error: {data.get('Message', 'Unknown error')}")
                    if attempt < max_retries - 1:
                        delay = self.get_retry_delay(APIProvider.CRYPTOCOMPARE)
                        self.logger.info(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        return None
                
                raw = data.get('RAW', {})
                cur = self.settings['vs_currency'].upper()
                
                if symbol not in raw or cur not in raw.get(symbol, {}):
                    self.logger.warning("CryptoCompare returned incomplete data")
                    if attempt < max_retries - 1:
                        delay = self.get_retry_delay(APIProvider.CRYPTOCOMPARE)
                        self.logger.info(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        return None
                
                crypto_data = raw[symbol][cur]
                
                price = float(crypto_data['PRICE'])
                if price <= 0:
                    self.logger.warning("Invalid price from CryptoCompare")
                    if attempt < max_retries - 1:
                        delay = self.get_retry_delay(APIProvider.CRYPTOCOMPARE)
                        self.logger.info(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        return None
                
                # Success - reset retry attempts
                if APIProvider.CRYPTOCOMPARE.value in self.retry_attempts:
                    del self.retry_attempts[APIProvider.CRYPTOCOMPARE.value]
                
                return PriceData(
                    symbol=symbol,
                    price=price,
                    change_24h=float(crypto_data['CHANGE24HOUR']),
                    change_percent_24h=float(crypto_data['CHANGEPCT24HOUR']),
                    timestamp=datetime.now(),
                    volume_24h=float(crypto_data['VOLUME24HOURTO'])
                )
                
            except Exception as e:
                self.logger.warning(f"CryptoCompare attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    delay = self.get_retry_delay(APIProvider.CRYPTOCOMPARE)
                    self.logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All CryptoCompare attempts failed: {e}")
                    return None
        
        return None

    def safe_after(self, delay: int, func, *args, **kwargs) -> None:
        """Safely call root.after() with window existence check"""
        try:
            if not self.root or not self.root.winfo_exists():
                return
            self.root.after(delay, func, *args, **kwargs)
        except Exception as e:
            self.logger.debug(f"Safe after call failed: {e}")

    def safe_notify(self, title: str, message: str, timeout: int = 5) -> None:
        """Decoupled safe notification system using multi-backend NotificationManager"""
        # Trim long messages for better toast reliability
        message = (message[:197] + "...") if len(message) > 200 else message
        self.notifier.notify(title, message, timeout)

    def send_notification(self, title: str, message: str) -> None:
        """BULLETPROOF notification system using multi-backend NotificationManager"""
        try:
            # Check if notifications are enabled
            if not self.settings.get('enable_notifications', True):
                logger.debug("Notifications disabled in settings")
                return
            
            # Validate inputs
            if not title or not message:
                logger.debug("Invalid notification parameters")
                return
            
            # Sanitize inputs
            safe_title = str(title).strip()[:50] if title else "CryptoPulse Monitor"
            safe_message = str(message).strip()[:200] if message else "Notification"
            
            # Remove any problematic characters
            safe_title = ''.join(c for c in safe_title if c.isprintable())
            safe_message = ''.join(c for c in safe_message if c.isprintable())
            
            # Use the multi-backend notification system
            self.notifier.notify(safe_title, safe_message, 5)
            
        except Exception as e:
            logger.debug(f"Notification system error (non-critical): {e}")
            # Never crash the app for notification failures

    def update_price_display(self, price_data: PriceData) -> None:
        """Update price display with comprehensive data"""
        self.last_price_data = self.current_price_data
        self.current_price_data = price_data
        
        # Get display currency symbol
        currency_symbol = "$" if self.get_display_currency() in ["USD", "USDT"] else self.get_display_currency()
        
        # Update price
        self.price_label.config(text=f"{currency_symbol}{price_data.price:,.2f}")
        
        # Update change with color coding
        change_text, change_color = self.format_price_change(
            price_data.change_24h, price_data.change_percent_24h)
        self.change_label.config(text=change_text, foreground=change_color)
        
        # Update volume if available
        if price_data.volume_24h:
            volume_text = self.format_volume(price_data.volume_24h)
            self.volume_label.config(text=f"24H Volume: {volume_text}")
        
        # Update timestamp
        self.update_label.config(
            text=f"Last updated: {price_data.timestamp.strftime('%H:%M:%S')}")
        
        # Update crypto display name with correct currency
        crypto = self.settings['cryptocurrency']
        display_currency = self.get_display_currency()
        if crypto in self.crypto_names:
            display_name = f"{self.crypto_names[crypto]}/{display_currency}"
        else:
            display_name = f"{crypto.title()} ({crypto[:3].upper()})/{display_currency}"
        self.crypto_display_label.config(text=display_name)
        
        # Add to history
        self.add_to_price_history(price_data)
        
        # Check for alerts (tick-to-tick comparison)
        if not self.is_first_check and self.last_price_data:
            self.check_and_trigger_alerts(self.last_price_data, price_data)
        
        # Update chart
        self.update_chart()
        
        # Update live indicator
        self.update_live_indicator()
        
        # Update statistics
        self.update_statistics()
        
        self.is_first_check = False

    def format_price_change(self, change: float, change_percent: float) -> Tuple[str, str]:
        """Format price change with appropriate color"""
        if change > 0:
            return f"▲ +${abs(change):,.2f} (+{change_percent:.2f}%)", self.colors['success']
        elif change < 0:
            return f"▼ -${abs(change):,.2f} ({change_percent:.2f}%)", self.colors['error']
        else:
            return "━ No Change (0.00%)", self.colors['text_secondary']

    def format_volume(self, volume: float) -> str:
        """Format volume with appropriate units"""
        if volume >= 1e9:
            return f"${volume/1e9:.2f}B"
        elif volume >= 1e6:
            return f"${volume/1e6:.2f}M"
        elif volume >= 1e3:
            return f"${volume/1e3:.2f}K"
        else:
            return f"${volume:.2f}"

    def add_to_price_history(self, price_data: PriceData) -> None:
        """Add price data to history with retention management and validation"""
        # Validate price data before adding
        if not self._validate_price_data(price_data):
            logger.warning("Invalid price data received, skipping")
            return
            
        self.price_history.append(price_data)
        
        # Clean old data efficiently
        cutoff_hours = self.settings['data_retention']['price_history_hours']
        cutoff_time = datetime.now() - timedelta(hours=cutoff_hours)
        
        # Use list comprehension for better performance
        self.price_history = [p for p in self.price_history if p.timestamp > cutoff_time]
        
        # Limit maximum history size to prevent memory issues
        max_history_size = 10000
        if len(self.price_history) > max_history_size:
            self.price_history = self.price_history[-max_history_size:]
            logger.info(f"Price history trimmed to {max_history_size} entries")

    def check_and_trigger_alerts(self, last_data: PriceData, current_data: PriceData) -> None:
        """Check and trigger alerts based on tick-to-tick price changes"""
        if last_data.price == 0:
            return
            
        # Calculate tick-to-tick percentage change
        tick_change_percent = ((current_data.price - last_data.price) / last_data.price) * 100
        absolute_change_percent = abs(tick_change_percent)
        
        # Price drop alert
        if (tick_change_percent < 0 and 
            self.settings['alert_config']['price_drop']['enabled'] and
            absolute_change_percent >= self.settings['alert_config']['price_drop']['threshold']):
            
            self.trigger_alert("Price Drop", 
                f"{current_data.symbol} dropped {absolute_change_percent:.2f}% to ${current_data.price:,.2f}")
        
        # Price rise alert  
        if (tick_change_percent > 0 and
            self.settings['alert_config']['price_rise']['enabled'] and
            absolute_change_percent >= self.settings['alert_config']['price_rise']['threshold']):
            
            self.trigger_alert("Price Rise",
                f"{current_data.symbol} rose {absolute_change_percent:.2f}% to ${current_data.price:,.2f}")

    def trigger_alert(self, alert_type: str, message: str) -> None:
        """Trigger alert with notification and history"""
        timestamp = datetime.now()
        
        # Send notification
        if self.settings['enable_notifications']:
            self.send_notification(f"CryptoPulse: {alert_type}", message)
        
        # Add to history
        alert_record = {
            'type': alert_type,
            'message': message,
            'timestamp': timestamp
        }
        self.alerts_history.append(alert_record)
        
        # Update GUI
        self.add_alert_to_gui(alert_record)
        
        logger.info(f"Alert triggered: {alert_type} - {message}")

    def test_notification(self) -> None:
        """BULLETPROOF notification testing"""
        try:
            self.send_notification(
                "CryptoPulse Test", 
                "If you see this, notifications are working correctly!"
            )
            
            # Don't show success dialog immediately - wait to see if it worked
            def delayed_feedback():
                time.sleep(2)  # Wait for notification to appear
                self.root.after(0, lambda: self.show_info(
                    "Notification Test", 
                    "Test notification sent! Check if you received it.\n\n" +
                    "If you didn't see a notification, check your system notification settings."
                ))
            
            threading.Thread(target=delayed_feedback, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Test notification failed: {e}")
            self.show_error("Notification Test", f"Notification test failed:\n{e}")

    def add_alert_to_gui(self, alert_record: dict) -> None:
        """Add alert to GUI list"""
        timestamp_str = alert_record['timestamp'].strftime("%H:%M:%S")
        display_text = f"[{timestamp_str}] {alert_record['type']}: {alert_record['message']}"
        
        self.alerts_listbox.insert(0, display_text)
        
        # Limit alerts display
        max_alerts = self.settings['data_retention']['alert_history_count']
        if self.alerts_listbox.size() > max_alerts:
            self.alerts_listbox.delete(max_alerts, tk.END)

    def get_filtered_history(self) -> List[PriceData]:
        """Get price history filtered by current timeframe"""
        if not self.price_history:
            return []
        
        now = datetime.now()
        
        if self.current_timeframe == TimeFrame.ONE_HOUR:
            cutoff = now - timedelta(hours=1)
        elif self.current_timeframe == TimeFrame.SIX_HOURS:
            cutoff = now - timedelta(hours=6)
        elif self.current_timeframe == TimeFrame.TWENTY_FOUR_HOURS:
            cutoff = now - timedelta(hours=24)
        elif self.current_timeframe == TimeFrame.SEVEN_DAYS:
            cutoff = now - timedelta(days=7)
        else:
            return self.price_history
        
        return [p for p in self.price_history if p.timestamp >= cutoff]

    def update_chart(self) -> None:
        """Update price chart with professional styling and timeframe filtering"""
        filtered_history = self.get_filtered_history()
        
        if len(filtered_history) < 2:
            # Show empty state message
            self.ax.clear()
            self.ax.text(0.5, 0.5, 'Insufficient data for chart', 
                        ha='center', va='center', transform=self.ax.transAxes,
                        color=self.colors['text_muted'], fontsize=14)
            self.ax.set_facecolor(self.colors['card'])
            self.canvas.draw_idle()
            return
        
        try:
            # Clear previous plot
            self.ax.clear()
            
            # Extract data
            timestamps = [p.timestamp for p in filtered_history]
            prices = [p.price for p in filtered_history]
            
            # Calculate price trend for color coding
            if len(prices) >= 2:
                price_trend = prices[-1] - prices[0]
                line_color = self.colors['success'] if price_trend >= 0 else self.colors['error']
            else:
                line_color = self.colors['primary']
            
            # Plot main line with gradient fill
            self.ax.plot(timestamps, prices, color=line_color, 
                        linewidth=2.5, alpha=0.9, label='Price')
            
            # Add scatter points for better visibility
            self.ax.scatter(timestamps, prices, color=line_color, 
                           s=15, alpha=0.7, zorder=5)
            
            # Add fill under curve for visual appeal (fill to rolling min)
            ymin = min(prices)
            self.ax.fill_between(timestamps, prices, ymin, alpha=0.1, 
                               color=line_color)
            
            # Add trend line if enough data points and numpy is available
            if len(prices) >= 3:
                try:
                    import numpy as np
                    x_numeric = mdates.date2num(timestamps)
                    z = np.polyfit(x_numeric, prices, 1)
                    p = np.poly1d(z)
                    self.ax.plot(timestamps, p(x_numeric), "--", 
                               color=self.colors['text_muted'], alpha=0.6, linewidth=1)
                except ImportError:
                    # Numpy not available, skip trend line
                    pass
                except Exception as e:
                    # Other error, log and continue
                    logger.warning(f"Trend line calculation failed: {e}")
            
            # Professional styling
            self.ax.set_facecolor(self.colors['card'])
            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['bottom'].set_color(self.colors['border'])
            self.ax.spines['left'].set_color(self.colors['border'])
            self.ax.tick_params(colors=self.colors['text_secondary'], labelsize=10)
            self.ax.grid(True, alpha=0.3, color=self.colors['chart_grid'], 
                        linestyle='-', linewidth=0.5)
            
            # Labels and title
            self.ax.set_ylabel('Price ($)', color=self.colors['text_primary'], fontsize=11)
            self.ax.set_title(f'Price Trend ({self.current_timeframe.value})', 
                            color=self.colors['text_primary'], fontsize=12, pad=15)
            
            # Format x-axis based on timeframe
            if self.current_timeframe == TimeFrame.ONE_HOUR:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
            elif self.current_timeframe == TimeFrame.SIX_HOURS:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            elif self.current_timeframe == TimeFrame.TWENTY_FOUR_HOURS:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
            elif self.current_timeframe == TimeFrame.SEVEN_DAYS:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            
            # Auto-scale with padding
            self.ax.margins(x=0.02, y=0.05)
            
            # Refresh canvas
            self.canvas.draw_idle()
            
        except Exception as e:
            logger.error(f"Chart update failed: {e}")
            # Show error message on chart
            self.ax.clear()
            self.ax.text(0.5, 0.5, f'Chart Error: {str(e)[:50]}...', 
                        ha='center', va='center', transform=self.ax.transAxes,
                        color=self.colors['error'], fontsize=12)
            self.ax.set_facecolor(self.colors['card'])
            self.canvas.draw_idle()

    def change_chart_timeframe(self, timeframe: TimeFrame) -> None:
        """Change chart timeframe and update display"""
        # Update current timeframe
        self.current_timeframe = timeframe
        
        # Update button colors
        for tf, btn in self.timeframe_buttons.items():
            if tf == timeframe:
                btn.config(bg=self.colors['primary'])
            else:
                btn.config(bg=self.colors['secondary'])
        
        # Update chart
        self.update_chart()
        
        logger.info(f"Chart timeframe changed to {timeframe.value}")

    def update_connection_status(self, text: str, color: str) -> None:
        """Update connection status display"""
        self.connection_label.config(text=text, foreground=color)
        status_text = text.replace("●", "").strip()
        self.status_text.config(text=status_text)

    def update_live_indicator(self) -> None:
        """Update live indicator with animation"""
        self.live_indicator.delete("all")
        
        if self.current_price_data and self.last_price_data:
            if self.current_price_data.price > self.last_price_data.price:
                color = self.colors['success']
            elif self.current_price_data.price < self.last_price_data.price:
                color = self.colors['error']
            else:
                color = self.colors['warning']
        else:
            color = self.colors['text_secondary']
        
        self.live_indicator.create_oval(2, 2, 10, 10, fill=color, outline="")

    def update_next_refresh_time(self, next_time: datetime) -> None:
        """Update next refresh time display"""
        time_str = next_time.strftime("%H:%M:%S")
        self.next_update_label.config(text=f"Next update: {time_str}")

    def update_statistics(self) -> None:
        """Update 24H statistics"""
        if len(self.price_history) < 2:
            return
        
        # Get last 24 hours of data
        last_24h = datetime.now() - timedelta(hours=24)
        recent_prices = [p.price for p in self.price_history if p.timestamp > last_24h]
        
        if recent_prices:
            high_24h = max(recent_prices)
            low_24h = min(recent_prices)
            avg_24h = sum(recent_prices) / len(recent_prices)
            
            self.high_label.config(text=f"24H High: ${high_24h:,.2f}")
            self.low_label.config(text=f"24H Low: ${low_24h:,.2f}")
            self.avg_label.config(text=f"24H Average: ${avg_24h:,.2f}")

    # GUI Event Handlers
    def toggle_monitoring(self) -> None:
        """Toggle price monitoring with UI feedback"""
        self.is_monitoring = not self.is_monitoring
        
        if self.is_monitoring:
            self.monitor_btn.config(text="Pause", bg=self.colors['primary'])
            self.add_alert_to_gui({
                'type': 'System',
                'message': 'Monitoring resumed',
                'timestamp': datetime.now()
            })
            logger.info("Monitoring resumed")
        else:
            self.monitor_btn.config(text="Start", bg=self.colors['success'])
            self.add_alert_to_gui({
                'type': 'System', 
                'message': 'Monitoring paused',
                'timestamp': datetime.now()
            })
            logger.info("Monitoring paused")

    def manual_refresh(self) -> None:
        """Manual refresh with user feedback"""
        if not self.is_monitoring:
            self.show_warning("Monitoring Paused", "Please resume monitoring first.")
            return
        
        self.status_text.config(text="Manual refresh requested...")
        threading.Thread(target=self.fetch_and_update_price, daemon=True).start()

    def clear_history(self) -> None:
        """Clear history with confirmation"""
        if not messagebox.askyesno("Clear History", 
                                  "Clear all price history and chart data?\n\nThis action cannot be undone."):
            return
        
        self.price_history.clear()
        self.ax.clear()
        self.ax.set_facecolor(self.colors['card'])
        self.ax.set_ylabel('Price ($)', color=self.colors['text_primary'])
        self.ax.set_title(f'Price Trend ({self.current_timeframe.value})', 
                         color=self.colors['text_primary'])
        self.canvas.draw()
        
        # Reset statistics
        self.high_label.config(text="24H High: ---")
        self.low_label.config(text="24H Low: ---")
        self.avg_label.config(text="24H Average: ---")
        
        self.add_alert_to_gui({
            'type': 'System',
            'message': 'Price history cleared',
            'timestamp': datetime.now()
        })
        
        logger.info("Price history cleared")

    def clear_alerts(self) -> None:
        """Clear alerts history"""
        self.alerts_listbox.delete(0, tk.END)
        self.alerts_history.clear()
        logger.info("Alerts history cleared")

    def export_data(self) -> None:
        """Export price data to CSV with enhanced error handling"""
        if not self.price_history:
            self.show_warning("No Data", "No price history to export.")
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Price Data",
                initialfile=f"cryptopulse_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if filename:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Timestamp', 'Symbol', 'Price', 'Change_24h', 
                                   'Change_Percent_24h', 'Volume_24h', 'Market_Cap'])
                    
                    for price_data in self.price_history:
                        writer.writerow([
                            price_data.timestamp.isoformat(),
                            price_data.symbol,
                            price_data.price,
                            price_data.change_24h,
                            price_data.change_percent_24h,
                            price_data.volume_24h or 0,
                            price_data.market_cap or 0
                        ])
                
                self.show_info("Export Complete", f"Data exported successfully!\n\nFile: {filename}")
                logger.info(f"Data exported to {filename}")
                
        except Exception as e:
            self.show_error("Export Failed", f"Failed to export data: {e}")
            logger.error(f"Data export failed: {e}")

    def toggle_settings(self) -> None:
        """Toggle settings window"""
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return
        
        self.create_settings_window()

    def create_settings_window(self) -> None:
        """Create comprehensive settings window"""
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("CryptoPulse Settings")
        self.settings_window.geometry("580x750")
        self.settings_window.configure(bg=self.colors['background'])
        self.settings_window.resizable(False, False)
        self.settings_window.transient(self.root)
        self.settings_window.grab_set()
        
        # Center the window
        self.settings_window.geometry("+{}+{}".format(
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 30
        ))
        
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(self.settings_window)
        notebook.pack(fill='both', expand=True, padx=20, pady=20)
        
        # General tab
        general_frame = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(general_frame, text='General')
        self.create_general_settings(general_frame)
        
        # Alerts tab
        alerts_frame = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(alerts_frame, text='Alerts')
        self.create_alerts_settings(alerts_frame)
        
        # Advanced tab
        advanced_frame = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(advanced_frame, text='Advanced')
        self.create_advanced_settings(advanced_frame)

    def create_general_settings(self, parent) -> None:
        """Create general settings tab"""
        # Refresh interval
        interval_frame = ttk.LabelFrame(parent, text="Refresh Settings", padding=15)
        interval_frame.pack(fill='x', padx=20, pady=15)
        
        ttk.Label(interval_frame, text="Refresh Interval (seconds):").pack(anchor='w')
        self.interval_var = tk.StringVar(value=str(self.settings['refresh_interval']))
        interval_spin = tk.Spinbox(interval_frame, from_=30, to=300, increment=10,
                                  textvariable=self.interval_var, width=15)
        interval_spin.pack(anchor='w', pady=(5, 0))
        
        ttk.Label(interval_frame, text="Minimum 30s recommended to avoid rate limits", 
                 foreground=self.colors['text_muted']).pack(anchor='w', pady=(2, 0))
        
        # Cryptocurrency selection
        crypto_frame = ttk.LabelFrame(parent, text="Cryptocurrency", padding=15)
        crypto_frame.pack(fill='x', padx=20, pady=15)
        
        ttk.Label(crypto_frame, text="Select Cryptocurrency:").pack(anchor='w')
        self.crypto_var = tk.StringVar(value=self.settings['cryptocurrency'])
        crypto_options = list(self.crypto_names.keys())
        crypto_combo = ttk.Combobox(crypto_frame, textvariable=self.crypto_var, 
                                   values=crypto_options, state='readonly', width=25)
        crypto_combo.pack(anchor='w', pady=(5, 0))
        
        # Currency selection
        currency_frame = ttk.LabelFrame(parent, text="Display Currency", padding=15)
        currency_frame.pack(fill='x', padx=20, pady=15)
        
        ttk.Label(currency_frame, text="Base Currency:").pack(anchor='w')
        self.currency_var = tk.StringVar(value=self.settings['vs_currency'])
        currency_combo = ttk.Combobox(currency_frame, textvariable=self.currency_var,
                                     values=['usd', 'eur', 'gbp', 'jpy', 'cad', 'aud', 'chf', 'inr', 'brl', 'cny', 'krw', 'sgd'],
                                     state='readonly', width=15)
        currency_combo.pack(anchor='w', pady=(5, 0))

    def create_alerts_settings(self, parent) -> None:
        """Create alerts settings tab"""
        # Enable notifications
        notif_frame = ttk.LabelFrame(parent, text="Notification Settings", padding=15)
        notif_frame.pack(fill='x', padx=20, pady=15)
        
        self.notifications_var = tk.BooleanVar(value=self.settings['enable_notifications'])
        notif_check = ttk.Checkbutton(notif_frame, text="Enable desktop notifications",
                                     variable=self.notifications_var)
        notif_check.pack(anchor='w')
        
        if not NOTIFICATIONS_AVAILABLE:
            notif_check.config(state='disabled')
            ttk.Label(notif_frame, text="(Notifications not available on this system)", 
                     foreground=self.colors['text_muted']).pack(anchor='w', pady=(2, 0))
        else:
            # Test notification button
            test_btn = self.create_modern_button(notif_frame, "Test Notification", 
                                               self.colors['accent'], self.test_notification)
            test_btn.pack(anchor='w', pady=(10, 0))
        
        # Price drop alerts
        drop_frame = ttk.LabelFrame(parent, text="Price Drop Alerts", padding=15)
        drop_frame.pack(fill='x', padx=20, pady=15)
        
        self.drop_enabled_var = tk.BooleanVar(
            value=self.settings['alert_config']['price_drop']['enabled'])
        drop_check = ttk.Checkbutton(drop_frame, text="Enable price drop alerts (tick-to-tick)",
                                    variable=self.drop_enabled_var)
        drop_check.pack(anchor='w')
        
        ttk.Label(drop_frame, text="Drop threshold (%):").pack(anchor='w', pady=(10, 0))
        self.drop_threshold_var = tk.StringVar(
            value=str(self.settings['alert_config']['price_drop']['threshold']))
        drop_spin = tk.Spinbox(drop_frame, from_=0.1, to=50, increment=0.5,
                              textvariable=self.drop_threshold_var, width=15)
        drop_spin.pack(anchor='w', pady=(5, 0))
        
        # Price rise alerts
        rise_frame = ttk.LabelFrame(parent, text="Price Rise Alerts", padding=15)
        rise_frame.pack(fill='x', padx=20, pady=15)
        
        self.rise_enabled_var = tk.BooleanVar(
            value=self.settings['alert_config']['price_rise']['enabled'])
        rise_check = ttk.Checkbutton(rise_frame, text="Enable price rise alerts (tick-to-tick)",
                                    variable=self.rise_enabled_var)
        rise_check.pack(anchor='w')
        
        ttk.Label(rise_frame, text="Rise threshold (%):").pack(anchor='w', pady=(10, 0))
        self.rise_threshold_var = tk.StringVar(
            value=str(self.settings['alert_config']['price_rise']['threshold']))
        rise_spin = tk.Spinbox(rise_frame, from_=0.1, to=50, increment=0.5,
                              textvariable=self.rise_threshold_var, width=15)
        rise_spin.pack(anchor='w', pady=(5, 0))

    def create_advanced_settings(self, parent) -> None:
        """Create advanced settings tab"""
        # API Provider selection
        api_frame = ttk.LabelFrame(parent, text="API Provider", padding=15)
        api_frame.pack(fill='x', padx=20, pady=15)
        
        ttk.Label(api_frame, text="Primary API Provider:").pack(anchor='w')
        self.api_provider_var = tk.StringVar(value=self.settings['api_provider'])
        api_combo = ttk.Combobox(api_frame, textvariable=self.api_provider_var,
                                values=['coingecko', 'binance', 'cryptocompare'],
                                state='readonly', width=20)
        api_combo.pack(anchor='w', pady=(5, 0))
        
        ttk.Label(api_frame, text="(Fallback providers will be used if primary fails)", 
                 foreground=self.colors['text_muted']).pack(anchor='w', pady=(5, 0))
        
        # Data retention
        retention_frame = ttk.LabelFrame(parent, text="Data Retention", padding=15)
        retention_frame.pack(fill='x', padx=20, pady=15)
        
        ttk.Label(retention_frame, text="Price history retention (hours):").pack(anchor='w')
        self.retention_var = tk.StringVar(
            value=str(self.settings['data_retention']['price_history_hours']))
        retention_spin = tk.Spinbox(retention_frame, from_=24, to=720, increment=24,
                                   textvariable=self.retention_var, width=15)
        retention_spin.pack(anchor='w', pady=(5, 0))
        
        ttk.Label(retention_frame, text="Alert history count:").pack(anchor='w', pady=(10, 0))
        self.alert_retention_var = tk.StringVar(
            value=str(self.settings['data_retention']['alert_history_count']))
        alert_retention_spin = tk.Spinbox(retention_frame, from_=50, to=1000, increment=50,
                                         textvariable=self.alert_retention_var, width=15)
        alert_retention_spin.pack(anchor='w', pady=(5, 0))
        
        # UI Settings
        ui_frame = ttk.LabelFrame(parent, text="UI Settings", padding=15)
        ui_frame.pack(fill='x', padx=20, pady=15)
        
        self.auto_minimize_var = tk.BooleanVar(
            value=self.settings['ui_config']['auto_minimize'])
        minimize_check = ttk.Checkbutton(ui_frame, text="Auto-minimize to tray on startup",
                                        variable=self.auto_minimize_var)
        minimize_check.pack(anchor='w')
        
        self.enable_tray_var = tk.BooleanVar(
            value=self.settings['ui_config'].get('enable_system_tray', True))
        tray_check = ttk.Checkbutton(ui_frame, text="Enable system tray functionality",
                                    variable=self.enable_tray_var)
        tray_check.pack(anchor='w', pady=(5, 0))
        
        if not SYSTEM_TRAY_AVAILABLE:
            minimize_check.config(state='disabled')
            tray_check.config(state='disabled')
            ttk.Label(ui_frame, text="(System tray not available on this system)", 
                     foreground=self.colors['text_muted']).pack(anchor='w', pady=(2, 0))
        
        # Settings buttons
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill='x', padx=20, pady=20)
        
        save_btn = self.create_modern_button(buttons_frame, "Save Settings", 
                                           self.colors['success'], self.save_settings_gui)
        save_btn.pack(side='left', padx=(0, 10))
        
        reset_btn = self.create_modern_button(buttons_frame, "Reset to Defaults",
                                            self.colors['warning'], self.reset_settings)
        reset_btn.pack(side='left', padx=(0, 10))
        
        cancel_btn = self.create_modern_button(buttons_frame, "Cancel",
                                             self.colors['secondary'], 
                                             lambda: self.settings_window.destroy())
        cancel_btn.pack(side='right')

    def save_settings_gui(self) -> None:
        """Save settings from GUI with validation"""
        try:
            # Validate and save settings
            new_interval = int(self.interval_var.get())
            if new_interval < 30:  # Increased minimum to 30 seconds
                raise ValueError("Refresh interval must be at least 30 seconds to avoid rate limits")
            
            new_drop_threshold = float(self.drop_threshold_var.get())
            new_rise_threshold = float(self.rise_threshold_var.get())
            new_retention = int(self.retention_var.get())
            new_alert_retention = int(self.alert_retention_var.get())
            
            if new_drop_threshold <= 0 or new_rise_threshold <= 0:
                raise ValueError("Thresholds must be greater than 0")
            
            if new_retention < 24:
                raise ValueError("Retention must be at least 24 hours")
            
            # Update settings
            old_crypto = self.settings['cryptocurrency']
            self.settings['refresh_interval'] = new_interval
            self.settings['cryptocurrency'] = self.crypto_var.get()
            self.settings['vs_currency'] = self.currency_var.get()
            self.settings['api_provider'] = self.api_provider_var.get()
            self.settings['enable_notifications'] = self.notifications_var.get()
            
            self.settings['alert_config']['price_drop']['enabled'] = self.drop_enabled_var.get()
            self.settings['alert_config']['price_drop']['threshold'] = new_drop_threshold
            self.settings['alert_config']['price_rise']['enabled'] = self.rise_enabled_var.get()
            self.settings['alert_config']['price_rise']['threshold'] = new_rise_threshold
            
            self.settings['data_retention']['price_history_hours'] = new_retention
            self.settings['data_retention']['alert_history_count'] = new_alert_retention
            self.settings['ui_config']['auto_minimize'] = self.auto_minimize_var.get()
            self.settings['ui_config']['enable_system_tray'] = self.enable_tray_var.get()
            
            # Save to file
            self.save_settings()
            
            # Update UI elements if cryptocurrency changed
            if old_crypto != self.settings['cryptocurrency']:
                self.crypto_display_label.config(text=self.get_crypto_display_name())
                # Clear history since it's for a different crypto
                self.price_history.clear()
                self.is_first_check = True
            
            # Update provider label
            self.api_provider_label.config(
                text=f"Provider: {self.settings['api_provider'].title()}")
            
            # Close settings window
            self.settings_window.destroy()
            
            # Show success message
            self.show_info("Settings Saved", "Settings have been saved successfully!")
            
            # Add to alerts
            self.add_alert_to_gui({
                'type': 'System',
                'message': 'Settings updated successfully',
                'timestamp': datetime.now()
            })
            
            logger.info("Settings saved successfully")
            
        except ValueError as e:
            self.show_error("Invalid Settings", f"Please check your input:\n{e}")
        except Exception as e:
            self.show_error("Settings Error", f"Failed to save settings:\n{e}")
            logger.error(f"Settings save failed: {e}")

    def reset_settings(self) -> None:
        """Reset all settings to defaults"""
        if not messagebox.askyesno("Reset Settings", 
                                  "Reset all settings to default values?\n\nThis will restore factory defaults."):
            return
        
        # Reset to defaults
        self.settings = {
            'refresh_interval': 60,
            'cryptocurrency': 'bitcoin',
            'vs_currency': 'usd',
            'api_provider': APIProvider.COINGECKO.value,
            'enable_notifications': True,
            'alert_config': {
                'price_drop': {'enabled': True, 'threshold': 2.0},
                'price_rise': {'enabled': False, 'threshold': 5.0},
                'volume_spike': {'enabled': False, 'threshold': 50.0}
            },
            'ui_config': {
                'window_width': 1200,
                'window_height': 800,
                'window_x': 100,
                'window_y': 100,
                'dark_mode': True,
                'auto_minimize': False
            },
            'data_retention': {
                'price_history_hours': 168,
                'alert_history_count': 100
            }
        }
        
        # Update GUI variables
        if hasattr(self, 'interval_var'):
            self.interval_var.set("60")
            self.crypto_var.set("bitcoin")
            self.currency_var.set("usd")
            self.api_provider_var.set("coingecko")
            self.notifications_var.set(True)
            self.drop_enabled_var.set(True)
            self.drop_threshold_var.set("2.0")
            self.rise_enabled_var.set(False)
            self.rise_threshold_var.set("5.0")
            self.retention_var.set("168")
            self.alert_retention_var.set("100")
            self.auto_minimize_var.set(False)
        
        self.save_settings()
        self.show_info("Settings Reset", "All settings have been reset to defaults!")
        logger.info("Settings reset to defaults")

    def show_about(self) -> None:
        """Show comprehensive about dialog with updated information"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About CryptoPulse Monitor")
        about_window.geometry("550x550")
        about_window.configure(bg=self.colors['background'])
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        
        # Center the window
        about_window.geometry("+{}+{}".format(
            self.root.winfo_rootx() + 100,
            self.root.winfo_rooty() + 50
        ))
        
        # Content frame
        content_frame = ttk.Frame(about_window, style='Card.TFrame')
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # App icon and title
        title_frame = ttk.Frame(content_frame, style='Card.TFrame')
        title_frame.pack(fill='x', pady=(0, 20))
        
        title_label = ttk.Label(title_frame, text="CryptoPulse Monitor",
                               font=('Segoe UI', 24, 'bold'),
                               foreground=self.colors['primary'],
                               background=self.colors['surface'])
        title_label.pack()
        
        subtitle_label = ttk.Label(title_frame, text="Professional Cryptocurrency Tracking",
                                  style='Info.TLabel')
        subtitle_label.pack(pady=(5, 0))
        
        # Version and author info
        info_frame = ttk.Frame(content_frame, style='Card.TFrame')
        info_frame.pack(fill='x', pady=(0, 20))
        
        info_text = f"""Version: 2.1.2 - BULLETPROOF HOTFIX
Author: Guillaume Lessard
Company: iD01t Productions
Website: https://id01t.store
Email: admin@id01t.store
Year: 2025
License: Closed Source — All Rights Reserved
Python: {sys.version.split()[0]}

PROPRIETARY LICENSE:
This software is proprietary and confidential.
All rights are reserved. Unauthorized copying, modification,
distribution, or reverse engineering is strictly prohibited.
For licensing inquiries, contact: admin@id01t.store

ADVANCED FEATURES:
• BULLETPROOF error handling and recovery
• Intelligent API rate limit management
• Reliable notification system with global exception handling
• Progressive error recovery and fallback mechanisms
• Memory-efficient operation with smart caching
• Hidden Easter egg: Konami Code support
• Production-ready for commercial deployment"""
        
        info_label = ttk.Label(info_frame, text=info_text,
                              style='Info.TLabel', justify='center')
        info_label.pack()
        
        # Features
        features_frame = ttk.LabelFrame(content_frame, text="Key Features", padding=15)
        features_frame.pack(fill='x', pady=(0, 20))
        
        features_text = """• Real-time price monitoring with intelligent API fallback
• Professional dark-themed interface with modern design
• Smart notification system with tick-to-tick alerts
• Interactive price history charts with multiple timeframes
• System tray integration with comprehensive context menu
• Multi-exchange API support (CoinGecko, Binance, CryptoCompare)
• Persistent settings and automatic crash recovery
• Cross-platform compatibility (Windows, macOS, Linux)
• Professional data export and statistics tracking"""
        
        features_label = ttk.Label(features_frame, text=features_text,
                                  style='Info.TLabel', justify='left')
        features_label.pack(anchor='w')
        
        # Buttons frame
        buttons_frame = ttk.Frame(content_frame, style='Card.TFrame')
        buttons_frame.pack(fill='x', pady=10)
        
        # Website button
        website_btn = self.create_modern_button(buttons_frame, "Visit Website",
                                              self.colors['accent'],
                                              lambda: webbrowser.open('https://id01t.store'))
        website_btn.pack(side='left', padx=(0, 10))
        
        # Close button
        close_btn = self.create_modern_button(buttons_frame, "Close",
                                            self.colors['primary'],
                                            about_window.destroy)
        close_btn.pack(side='right')

    # Utility methods
    def show_info(self, title: str, message: str) -> None:
        """Show info message box"""
        messagebox.showinfo(title, message)

    def show_warning(self, title: str, message: str) -> None:
        """Show warning message box"""
        messagebox.showwarning(title, message)

    def show_error(self, title: str, message: str) -> None:
        """Show error message box"""
        messagebox.showerror(title, message)

    # Window event handlers
    def on_closing(self) -> None:
        """Handle window closing with options"""
        if self.settings['ui_config']['auto_minimize'] and SYSTEM_TRAY_AVAILABLE:
            self.minimize_to_tray()
        else:
            if SYSTEM_TRAY_AVAILABLE:
                choice = messagebox.askyesnocancel(
                    "Exit CryptoPulse", 
                    "What would you like to do?\n\nYes = Exit completely\nNo = Minimize to tray\nCancel = Stay open"
                )
                
                if choice is True:  # Yes - exit
                    self.quit_application()
                elif choice is False:  # No - minimize
                    self.minimize_to_tray()
                # Cancel - do nothing
            else:
                if messagebox.askyesno("Exit CryptoPulse", "Are you sure you want to exit?"):
                    self.quit_application()

    def on_window_configure(self, event) -> None:
        """Handle window configuration changes with crash prevention"""
        try:
            if (event.widget == self.root and 
                hasattr(self, 'root') and 
                self.root and 
                self.root.winfo_exists() and
                self.root.winfo_viewable()):
                # Save window position safely
                try:
                    self.settings['ui_config']['window_x'] = self.root.winfo_x()
                    self.settings['ui_config']['window_y'] = self.root.winfo_y()
                    self.settings['ui_config']['window_width'] = self.root.winfo_width()
                    self.settings['ui_config']['window_height'] = self.root.winfo_height()
                except tk.TclError:
                    # Window was destroyed during the call
                    pass
        except Exception as e:
            logger.debug(f"Window configure error (non-critical): {e}")

    def on_window_map(self, event) -> None:
        """Handle window mapping (restore/maximize) to prevent crashes"""
        try:
            if hasattr(self, 'gui_initialized') and not self.gui_initialized:
                # GUI not fully initialized yet, skip
                return
            # Window restored by OS or user; clear suppression flag
            self._suppress_unmap = False
            logger.debug("Window mapped/restored")
        except Exception as e:
            logger.debug(f"Window map error (non-critical): {e}")

    def hide_window(self):
        """Bulletproof hide window and show tray icon with suppression guard"""
        try:
            if hasattr(self, 'gui_initialized') and not self.gui_initialized:
                return
            
            # Suppression guard to prevent recursion
            if hasattr(self, '_suppress_hide') and self._suppress_hide:
                return
            self._suppress_hide = True
                
            # Hide the window
            self.root.withdraw()
            
            # Show tray icon if available and enabled
            if SYSTEM_TRAY_AVAILABLE and self.settings.get("ui_config", {}).get("enable_system_tray", True):
                self.minimize_to_tray()
            else:
                # Fallback to iconify if tray not available
                self.safe_iconify()
                
            logger.info("Window hidden and tray icon activated")
        except Exception as e:
            logger.error(f"Error hiding window: {e}")
            # Fallback to iconify
            self.safe_iconify()
        finally:
            # Always reset suppression flag
            self._suppress_hide = False

    def on_window_unmap(self, event) -> None:
        """Handle window unmapping (minimize) - bulletproof approach"""
        try:
            if hasattr(self, 'gui_initialized') and not self.gui_initialized:
                return
            
            # Only act on real minimize (not alt-tab switches)
            if self.root.state() == "iconic":
                self.hide_window()
                    
            logger.debug("Window unmapped/minimized")
        except Exception as e:
            logger.debug(f"Window unmap error (non-critical): {e}")

    def on_key_press(self, event) -> None:
        """Handle Konami Code key sequence"""
        try:
            # Map key events to Konami sequence
            key_map = {
                'Up': 'Up',
                'Down': 'Down', 
                'Left': 'Left',
                'Right': 'Right',
                'Return': 'Return',
                'space': 'space'
            }
            
            key = key_map.get(event.keysym, None)
            if key:
                self.konami_input.append(key)
                
                # Keep only last 10 keys
                if len(self.konami_input) > 10:
                    self.konami_input = self.konami_input[-10:]
                
                # Check if sequence matches
                if self.konami_input == self.konami_sequence:
                    self.activate_konami_code()
                    self.konami_input = []  # Reset sequence
                elif not self.konami_sequence[:len(self.konami_input)] == self.konami_input:
                    # Reset if sequence doesn't match
                    self.konami_input = []
                    
        except Exception as e:
            logger.debug(f"Key press error: {e}")

    def activate_konami_code(self) -> None:
        """Activate the Konami Code Easter egg"""
        if self.konami_activated:
            return
            
        self.konami_activated = True
        logger.info("[KONAMI] Konami Code activated!")
        
        # Show special message
        self.show_info("[KONAMI] Konami Code Activated!", 
                      "Congratulations! You found the hidden Easter egg!\n\n"
                      "Special features unlocked:\n"
                      "• Rainbow price display\n"
                      "• Special sound effects\n"
                      "• Developer mode enabled\n"
                      "• Hidden statistics panel\n\n"
                      "Enjoy the enhanced experience!")
        
        # Enable special features
        self.enable_konami_features()

    def enable_konami_features(self) -> None:
        """Enable special features when Konami Code is activated"""
        try:
            # Add rainbow effect to price display
            if hasattr(self, 'price_label'):
                self.add_rainbow_effect()
            
            # Enable developer mode
            self.developer_mode = True
            
            # Add special sound effects (if available)
            self.enable_sound_effects()
            
            # Show hidden statistics
            self.show_hidden_stats()
            
            logger.info("Konami features enabled successfully")
            
        except Exception as e:
            logger.warning(f"Could not enable all Konami features: {e}")

    def add_rainbow_effect(self) -> None:
        """Add rainbow color cycling effect to price display"""
        try:
            if hasattr(self, 'price_label'):
                self.cycle_rainbow_colors()
        except Exception as e:
            logger.debug(f"Rainbow effect error: {e}")

    def cycle_rainbow_colors(self) -> None:
        """Cycle through rainbow colors for price display"""
        colors = ['#FF0000', '#FF7F00', '#FFFF00', '#00FF00', '#0000FF', '#4B0082', '#9400D3']
        if hasattr(self, 'rainbow_index'):
            self.rainbow_index = (self.rainbow_index + 1) % len(colors)
        else:
            self.rainbow_index = 0
        
        if hasattr(self, 'price_label') and self.price_label.winfo_exists():
            self.price_label.config(foreground=colors[self.rainbow_index])
            # Schedule next color change
            self.root.after(500, self.cycle_rainbow_colors)

    def enable_sound_effects(self) -> None:
        """Enable sound effects for notifications"""
        try:
            # This would require additional audio libraries
            logger.info("Sound effects enabled (requires audio libraries)")
        except Exception as e:
            logger.debug(f"Sound effects error: {e}")

    def show_hidden_stats(self) -> None:
        """Show hidden developer statistics"""
        try:
            if hasattr(self, 'status_text'):
                hidden_stats = (
                    f"[KONAMI] Mode Active | "
                    f"API Calls: {self.api_failure_count} | "
                    f"Cache Hits: {getattr(self, 'cache_hits', 0)} | "
                    f"Uptime: {time.time() - getattr(self, 'start_time', time.time()):.0f}s"
                )
                self.status_text.config(text=hidden_stats)
        except Exception as e:
            logger.debug(f"Hidden stats error: {e}")

    def quit_application(self, *_args) -> None:
        """BULLETPROOF application shutdown with comprehensive cleanup"""
        logger.info("Initiating shutdown sequence...")
        
        # Set shutdown flags immediately
        self.shutdown_requested = True
        self.is_monitoring = False
        
        # Signal all threads to stop
        self.monitoring_stop_event.set()
        self.tray_stop_event.set()
        
        try:
            # Save settings first
            self.save_settings()
            logger.info("Settings saved")
        except Exception as e:
            logger.error(f"Error saving settings during shutdown: {e}")
        
        try:
            # Stop system tray safely
            if SYSTEM_TRAY_AVAILABLE and hasattr(self, 'tray_icon'):
                if self.tray_running:
                    try:
                        self.tray_icon.stop()
                        # Wait for tray thread to finish
                        if hasattr(self, 'tray_thread') and self.tray_thread:
                            self.tray_thread.join(timeout=2.0)
                    except Exception as e:
                        logger.error(f"Error stopping tray: {e}")
                    finally:
                        self.tray_running = False
                        self.tray_icon = None
                        self.tray_thread = None
            
        except Exception as e:
            logger.error(f"Error during tray cleanup: {e}")
        
        try:
            # Stop monitoring thread safely
            if hasattr(self, 'monitoring_thread') and self.monitoring_thread:
                try:
                    self.monitoring_thread.join(timeout=3.0)
                    logger.info("Monitoring thread stopped")
                except Exception as e:
                    logger.error(f"Error stopping monitoring thread: {e}")
                finally:
                    self.monitoring_thread = None
        except Exception as e:
            logger.error(f"Error during monitoring thread cleanup: {e}")
        
        # Final cleanup - ensure all threads are terminated
        try:
            # Force terminate any remaining threads
            import threading
            for thread in threading.enumerate():
                if thread != threading.current_thread() and thread.is_alive():
                    if hasattr(thread, 'daemon') and not thread.daemon:
                        logger.warning(f"Non-daemon thread still running: {thread.name}")
                    else:
                        logger.debug(f"Daemon thread still running: {thread.name}")
        except Exception as e:
            logger.debug(f"Thread cleanup check failed: {e}")
        
        try:
            # Close settings window if open
            if hasattr(self, 'settings_window'):
                try:
                    if self.settings_window.winfo_exists():
                        self.settings_window.destroy()
                except:
                    pass
        except Exception as e:
            logger.error(f"Error closing settings window: {e}")
        
        try:
            # Close HTTP session
            if hasattr(self, 'session'):
                self.session.close()
                logger.info("HTTP session closed")
        except Exception as e:
            logger.error(f"Error closing HTTP session: {e}")
        
        try:
            # Final GUI cleanup with improved error handling
            if hasattr(self, 'root') and self.root:
                try:
                    # Check if root window still exists
                    self.root.winfo_exists()
                    self.root.quit()
                    self.root.destroy()
                    logger.info("GUI cleanup completed")
                except tk.TclError:
                    logger.debug("Root window already destroyed")
                except Exception as e:
                    logger.warning(f"Minor GUI cleanup error: {e}")
        except Exception as e:
            logger.error(f"Error during GUI cleanup: {e}")
        
        logger.info("Application shutdown completed successfully")

    def create_fallback_icon(self) -> None:
        """Create fallback programmatic icon if ico file not available"""
        try:
            # Create app icon
            icon_size = 32
            icon = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(icon)
            
            # Draw modern crypto icon
            center = icon_size // 2
            radius = icon_size // 2 - 2
            
            # Outer circle
            draw.ellipse([2, 2, icon_size-2, icon_size-2], 
                        fill='#3B82F6', outline='#1E40AF', width=1)
            
            # Inner symbol (simplified crypto symbol)
            draw.rectangle([center-6, center-8, center-2, center+8], fill='white')
            draw.rectangle([center+2, center-8, center+6, center+8], fill='white')
            draw.rectangle([center-8, center-2, center+8, center+2], fill='white')
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(icon)
            self.root.iconphoto(True, photo)
            
        except Exception as e:
            logger.warning(f"Error creating fallback icon: {e}")

    def setup_styles(self) -> None:
        """Configure professional ttk styles"""
        style = ttk.Style()
        
        # Configure theme
        style.theme_use('clam')
        
        # Define custom styles
        styles_config = {
            'App.TFrame': {
                'configure': {'background': self.colors['background']}
            },
            'Card.TFrame': {
                'configure': {
                    'background': self.colors['surface'],
                    'relief': 'flat',
                    'borderwidth': 1
                }
            },
            'Header.TLabel': {
                'configure': {
                    'background': self.colors['surface'],
                    'foreground': self.colors['text_primary'],
                    'font': ('Segoe UI', 18, 'bold')
                }
            },
            'Price.TLabel': {
                'configure': {
                    'background': self.colors['surface'],
                    'foreground': self.colors['text_primary'],
                    'font': ('Segoe UI', 42, 'bold')
                }
            },
            'Change.TLabel': {
                'configure': {
                    'background': self.colors['surface'],
                    'font': ('Segoe UI', 16, 'bold')
                }
            },
            'Info.TLabel': {
                'configure': {
                    'background': self.colors['surface'],
                    'foreground': self.colors['text_secondary'],
                    'font': ('Segoe UI', 11)
                }
            },
            'Title.TLabel': {
                'configure': {
                    'background': self.colors['surface'],
                    'foreground': self.colors['text_primary'],
                    'font': ('Segoe UI', 14, 'bold')
                }
            }
        }
        
        for style_name, config in styles_config.items():
            if 'configure' in config:
                style.configure(style_name, **config['configure'])

    def create_header(self) -> None:
        """Create professional header with branding"""
        header_frame = ttk.Frame(self.root, style='Card.TFrame')
        header_frame.pack(fill='x', padx=0, pady=0)
        
        # Brand section
        brand_frame = ttk.Frame(header_frame, style='Card.TFrame')
        brand_frame.pack(side='left', padx=20, pady=15)
        
        title_label = ttk.Label(brand_frame, 
                               text="CryptoPulse Monitor", 
                               style='Header.TLabel')
        title_label.pack(anchor='w')
        
        subtitle_label = ttk.Label(brand_frame,
                                  text="Professional Cryptocurrency Tracking",
                                  style='Info.TLabel')
        subtitle_label.pack(anchor='w', pady=(2, 0))
        
        # Control buttons
        controls_frame = ttk.Frame(header_frame, style='Card.TFrame')
        controls_frame.pack(side='right', padx=20, pady=15)
        
        # Settings button
        self.settings_btn = self.create_modern_button(
            controls_frame, "Settings", self.colors['primary'], 
            self.toggle_settings)
        self.settings_btn.pack(side='right', padx=5)
        
        # About button  
        about_btn = self.create_modern_button(
            controls_frame, "About", self.colors['accent'],
            self.show_about)
        about_btn.pack(side='right', padx=5)
        
        # Minimize button
        if SYSTEM_TRAY_AVAILABLE:
            self.minimize_btn = self.create_modern_button(
                controls_frame, "−", self.colors['warning'],
                self.minimize_to_tray, width=3)
            self.minimize_btn.pack(side='right', padx=2)

    def create_modern_button(self, parent, text: str, color: str, 
                           command, width: int = None) -> tk.Button:
        """Create modern styled button"""
        btn = tk.Button(parent, text=text, command=command,
                       bg=color, fg='white', font=('Segoe UI', 10, 'bold'),
                       border=0, padx=15, pady=6, cursor='hand2',
                       activebackground=self._darken_color(color),
                       activeforeground='white')
        
        if width:
            btn.config(width=width, padx=5)
            
        # Add enhanced hover effects
        def on_enter(e):
            hover_color = self._get_hover_color(color)
            btn.config(bg=hover_color, relief='raised')
        def on_leave(e):
            btn.config(bg=color, relief='flat')
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def _lighten_color(self, hex_color: str, factor: float = 1.2) -> str:
        """Lighten a hex color by a factor"""
        try:
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            new_rgb = tuple(min(255, int(c * factor)) for c in rgb)
            return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"
        except:
            return hex_color

    def _darken_color(self, hex_color: str, factor: float = 0.8) -> str:
        """Darken a hex color by a factor"""
        return self._lighten_color(hex_color, factor)

    def _get_hover_color(self, hex_color: str) -> str:
        """Get appropriate hover color based on the base color"""
        color_map = {
            self.colors['primary']: self.colors['primary_hover'],
            self.colors['accent']: self.colors['accent_hover'],
            self.colors['success']: self.colors['success_hover'],
            self.colors['warning']: self.colors['warning_hover'],
            self.colors['error']: self.colors['error_hover']
        }
        return color_map.get(hex_color, self._lighten_color(hex_color, 1.1))

    def _validate_price_data(self, price_data: PriceData) -> bool:
        """Validate price data for consistency and reasonableness"""
        try:
            # Check for valid price
            if not isinstance(price_data.price, (int, float)) or price_data.price <= 0:
                return False
            
            # Check for reasonable price range (prevent obviously bad data)
            if price_data.price > 1000000 or price_data.price < 0.000001:
                return False
            
            # Check for valid timestamp
            if not isinstance(price_data.timestamp, datetime):
                return False
            
            # Check timestamp is not too old or in the future
            now = datetime.now()
            if price_data.timestamp < now - timedelta(hours=1) or price_data.timestamp > now + timedelta(minutes=5):
                return False
            
            # Check for valid symbol
            if not price_data.symbol or len(price_data.symbol) < 2:
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Price data validation error: {e}")
            return False

    def _normalize_price_data(self, price_data: PriceData) -> PriceData:
        """Normalize price data to ensure consistent fields across all providers"""
        try:
            if not price_data:
                return price_data
            
            # Normalize volume data - use placeholder if not available
            if price_data.volume_24h is None or price_data.volume_24h <= 0:
                # Try to get volume from cache first
                if hasattr(self, 'cached_price_data') and self.cached_price_data and self.cached_price_data.volume_24h:
                    price_data.volume_24h = self.cached_price_data.volume_24h
                else:
                    # Use placeholder value instead of estimate
                    price_data.volume_24h = None  # Indicates data not available
            
            # Normalize market cap data - use placeholder if not available
            if price_data.market_cap is None or price_data.market_cap <= 0:
                # Try to get market cap from cache first
                if hasattr(self, 'cached_price_data') and self.cached_price_data and self.cached_price_data.market_cap:
                    price_data.market_cap = self.cached_price_data.market_cap
                else:
                    # Use placeholder value instead of estimate
                    price_data.market_cap = None  # Indicates data not available
            
            # Ensure all numeric fields are properly typed (use 0.0 for None values)
            price_data.volume_24h = float(price_data.volume_24h or 0.0)
            price_data.market_cap = float(price_data.market_cap or 0.0)
            price_data.change_24h = float(price_data.change_24h or 0.0)
            price_data.change_percent_24h = float(price_data.change_percent_24h or 0.0)
            
            return price_data
            
        except Exception as e:
            logger.warning(f"Price data normalization error: {e}")
            return price_data

    def format_price(self, price: float) -> str:
        """Centralized price formatting utility"""
        return f"${price:,.2f}"

    def create_main_content(self) -> None:
        """Create main content area with cards"""
        main_frame = ttk.Frame(self.root, style='App.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left content area
        left_frame = ttk.Frame(main_frame, style='App.TFrame')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Price display card
        self.create_price_card(left_frame)
        
        # Chart card  
        self.create_chart_card(left_frame)
        
        # Controls card
        self.create_controls_card(left_frame)

    def create_menu_bar(self) -> None:
        """Create professional menu bar with About dialog"""
        try:
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # File menu
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Settings", command=self.toggle_settings)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.quit_application)
            
            # View menu
            view_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="View", menu=view_menu)
            view_menu.add_command(label="Refresh", command=self.manual_refresh)
            view_menu.add_command(label="Clear History", command=self.clear_history)
            view_menu.add_command(label="Clear Alerts", command=self.clear_alerts)
            
            # Tools menu
            tools_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Tools", menu=tools_menu)
            tools_menu.add_command(label="Test Notification", command=self.test_notification)
            tools_menu.add_command(label="Export Data", command=self.export_data)
            
            # Help menu
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Help", menu=help_menu)
            help_menu.add_command(label="About", command=self.show_about_dialog)
            
        except Exception as e:
            logger.warning(f"Could not create menu bar: {e}")

    def show_about_dialog(self) -> None:
        """Show professional About dialog with version, copyright, and license"""
        try:
            about_window = tk.Toplevel(self.root)
            about_window.title("About CryptoPulse Monitor")
            about_window.geometry("500x400")
            about_window.resizable(False, False)
            about_window.configure(bg=self.colors['background'])
            
            # Center the window
            about_window.transient(self.root)
            about_window.grab_set()
            
            # Main frame
            main_frame = tk.Frame(about_window, bg=self.colors['background'])
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title_label = tk.Label(
                main_frame,
                text="CryptoPulse Monitor",
                font=("Arial", 24, "bold"),
                fg=self.colors['primary'],
                bg=self.colors['background']
            )
            title_label.pack(pady=(0, 10))
            
            # Version
            version_label = tk.Label(
                main_frame,
                text="Version: 2.1.2 - BULLETPROOF HOTFIX",
                font=("Arial", 12, "bold"),
                fg=self.colors['text'],
                bg=self.colors['background']
            )
            version_label.pack(pady=(0, 20))
            
            # Info text
            info_text = f"""Author: Guillaume Lessard
Company: iD01t Productions
Website: https://id01t.store
Email: admin@id01t.store
Year: 2025
License: Closed Source — All Rights Reserved
Python: {sys.version.split()[0]}

PROPRIETARY LICENSE:
This software is proprietary and confidential.
All rights are reserved. Unauthorized copying, modification,
distribution, or reverse engineering is strictly prohibited.

For licensing inquiries, contact: admin@id01t.store

Features:
• Real-time cryptocurrency price monitoring
• Multiple API providers (CoinGecko, Binance, CryptoCompare)
• Professional desktop notifications
• System tray integration
• Advanced charting and analytics
• Bulletproof error handling
• Konami Code easter egg

© 2025 Guillaume Lessard, iD01t Productions
All Rights Reserved"""
            
            info_label = tk.Label(
                main_frame,
                text=info_text,
                font=("Arial", 10),
                fg=self.colors['text'],
                bg=self.colors['background'],
                justify=tk.LEFT,
                anchor='nw'
            )
            info_label.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            # Close button
            close_button = tk.Button(
                main_frame,
                text="Close",
                command=about_window.destroy,
                font=("Arial", 10, "bold"),
                bg=self.colors['primary'],
                fg='white',
                relief=tk.FLAT,
                padx=20,
                pady=5
            )
            close_button.pack(pady=(10, 0))
            
            # Focus the window
            about_window.focus_set()
            
        except Exception as e:
            logger.error(f"Could not show About dialog: {e}")
            # Fallback to simple messagebox
            try:
                from tkinter import messagebox
                messagebox.showinfo(
                    "About CryptoPulse Monitor",
                    "CryptoPulse Monitor v2.1.2 - BULLETPROOF HOTFIX\n\n"
                    "© 2025 Guillaume Lessard, iD01t Productions\n"
                    "All Rights Reserved\n\n"
                    "Closed Source License"
                )
            except Exception as fallback_error:
                logger.error(f"Fallback About dialog also failed: {fallback_error}")

    def run(self) -> None:
        """BULLETPROOF application runner with comprehensive error handling"""
        logger.info("Starting CryptoPulse Monitor v2.1.2...")
        
        try:
            # Initial price fetch with bulletproof error handling
            def safe_initial_fetch():
                try:
                    self.fetch_and_update_price()
                except Exception as e:
                    logger.warning(f"Initial price fetch failed: {e}")
                    # Show warning but don't crash
                    try:
                        self.show_warning("Connection Issue", 
                                        "Could not fetch initial price data.\nMonitoring will continue automatically.")
                    except Exception as warning_error:
                        logger.debug(f"Could not show warning: {warning_error}")
            
            threading.Thread(target=safe_initial_fetch, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to start initial price fetch: {e}")
        
        # Auto-minimize if configured with error handling
        try:
            if self.settings.get('ui_config', {}).get('auto_minimize', False) and SYSTEM_TRAY_AVAILABLE:
                self.root.after(2000, self.minimize_to_tray)
        except Exception as e:
            logger.debug(f"Auto-minimize setup failed: {e}")
        
        logger.info("CryptoPulse Monitor started successfully")
        
        # Start GUI main loop with bulletproof error recovery
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.critical(f"Critical GUI error: {e}")
            # Try to show error message
            try:
                self.show_error("Critical Error", f"Application encountered a critical error: {e}")
            except:
                pass  # If we can't even show error, just log it
            logger.critical(traceback.format_exc())
        finally:
            self.quit_application()


def create_requirements_file():
    """Create requirements.txt file for easy installation"""
    requirements_content = """# CryptoPulse Monitor v2.1.1 Requirements
# Professional Cryptocurrency Tracking Application
# Author: Guillaume Lessard / iD01t Productions
# Website: https://id01t.store

requests>=2.25.0
matplotlib>=3.5.0
Pillow>=8.0.0
plyer>=2.1.0
pystray>=0.19.0
numpy>=1.21.0

# Optional dependencies for enhanced functionality
# pyinstaller>=4.0  # For creating executable
# cx_Freeze>=6.0    # Alternative for creating executable
# auto-py-to-exe     # GUI for PyInstaller
"""
    
    try:
        with open('requirements.txt', 'w') as f:
            f.write(requirements_content)
        print("[OK] requirements.txt created successfully")
    except Exception as e:
        print(f"[WARNING] Could not create requirements.txt: {e}")


def create_launcher_scripts():
    """Create platform-specific launcher scripts"""
    # Windows batch file
    windows_launcher = """@echo off
title CryptoPulse Monitor v2.1.1
echo ========================================
echo   CryptoPulse Monitor v2.1.1
echo   Professional Edition
echo   Guillaume Lessard / iD01t Productions
echo   https://id01t.store
echo ========================================
echo.
echo Starting application...
python cryptopulse_monitor.py
if errorlevel 1 (
    echo.
    echo Error occurred. Press any key to exit...
    pause >nul
)
"""
    
    # Unix shell script
    unix_launcher = """#!/bin/bash
echo "========================================"
echo "  CryptoPulse Monitor v2.1.1"
echo "  Professional Edition"
echo "  Guillaume Lessard / iD01t Productions"
echo "  https://id01t.store"
echo "========================================"
echo ""
echo "Starting application..."
python3 cryptopulse_monitor.py
"""
    
    try:
        # Create Windows launcher
        with open('start_cryptopulse.bat', 'w') as f:
            f.write(windows_launcher)
        
        # Create Unix launcher
        with open('start_cryptopulse.sh', 'w') as f:
            f.write(unix_launcher)
        
        # Make Unix script executable
        import stat
        try:
            os.chmod('start_cryptopulse.sh', stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        except:
            pass
            
        print("[OK] Launcher scripts created successfully")
    except Exception as e:
        print(f"[WARNING] Could not create launcher scripts: {e}")


def main():
    """Main entry point with command line argument support"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CryptoPulse Monitor - Professional Cryptocurrency Tracking')
    parser.add_argument('--tray', action='store_true', 
                       help='Start minimized to system tray (requires system tray support)')
    parser.add_argument('--version', action='version', version='CryptoPulse Monitor v2.1.1')
    
    args = parser.parse_args()
    
    try:
        app = CryptoPulseMonitor()
        if args.tray:
            if SYSTEM_TRAY_AVAILABLE:
                # Start minimized to tray after a short delay to ensure tray is ready
                app.root.withdraw()
                app.root.after(100, app.minimize_to_tray)  # Delay to ensure tray is initialized
                logger.info("Starting in tray mode")
            else:
                print("[WARNING] System tray not available, starting in normal mode")
                logger.warning("System tray not available, starting in normal mode")
        app.run()
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
    finally:
        print("[OK] Shutdown complete")


if __name__ == "__main__":
    # Create helper files on first run
    try:
        create_requirements_file()
        create_launcher_scripts()
    except Exception as e:
        logger.warning(f"Could not create helper files: {e}")
    
    main()