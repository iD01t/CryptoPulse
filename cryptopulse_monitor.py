#!/usr/bin/env python3
"""
CryptoPulse Monitor - Professional Cryptocurrency Price Tracking Application
A bulletproof, cross-platform desktop application for real-time crypto monitoring

Author: Guillaume Lessard / iD01t Productions
Website: https://id01t.store
Email: admin@id01t.store
Version: 2.1.0
Year: 2025
License: MIT

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
import platform

# Configure logging first
def setup_logging():
    """Setup professional logging system"""
    try:
        log_dir = Path.home() / '.cryptopulse'
        log_dir.mkdir(exist_ok=True)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler with rotation protection
        log_file = log_dir / 'cryptopulse.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # Configure logger
        logger = logging.getLogger('CryptoPulse')
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    except Exception as e:
        # Fallback logging
        print(f"Warning: Could not setup logging: {e}")
        return logging.getLogger('CryptoPulse')

logger = setup_logging()

# Dependency management with bulletproof error handling
REQUIRED_PACKAGES = {
    'requests': 'requests>=2.25.0',
    'matplotlib': 'matplotlib>=3.5.0', 
    'pillow': 'Pillow>=8.0.0',
    'plyer': 'plyer>=2.1.0',
    'pystray': 'pystray>=0.19.0',
}

def check_package_installed(package_name: str) -> bool:
    """Check if a package is installed"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

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
    
    # Check tkinter separately as it's built-in
    try:
        import tkinter
        logger.info("tkinter (built-in) - available")
    except ImportError:
        logger.error("tkinter not available - this is a critical issue")
        print("ERROR: tkinter is not available. Please install Python with tkinter support.")
        return False
    
    # Check each required package
    for package, version_spec in REQUIRED_PACKAGES.items():
        if not check_package_installed(package):
            missing_packages.append((package, version_spec))
            logger.warning(f"{package} - missing")
        else:
            logger.info(f"{package} - available")
    
    # Install missing packages
    if missing_packages:
        logger.info(f"Installing {len(missing_packages)} missing packages...")
        failed_installs = []
        
        for package, version_spec in missing_packages:
            if not install_package(package, version_spec):
                failed_installs.append(package)
        
        if failed_installs:
            logger.error(f"Failed to install: {', '.join(failed_installs)}")
            print(f"\nFailed to install: {', '.join(failed_installs)}")
            print("Please install manually using:")
            for package in failed_installs:
                print(f"  pip install {REQUIRED_PACKAGES[package]}")
            return False
        
        logger.info("All dependencies installed successfully")
    else:
        logger.info("All dependencies already available")
    
    return True

# Install dependencies if needed
if not check_and_install_dependencies():
    input("Press Enter to exit...")
    sys.exit(1)

# Import all modules after dependency check
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, font, filedialog
    import requests
    import matplotlib
    matplotlib.use('TkAgg')  # Set backend before importing pyplot
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    from PIL import Image, ImageTk, ImageDraw
    
    # Optional imports with graceful fallbacks
    NOTIFICATIONS_AVAILABLE = False
    SYSTEM_TRAY_AVAILABLE = False
    
    try:
        from plyer import notification
        NOTIFICATIONS_AVAILABLE = True
        logger.info("Desktop notifications - available")
    except ImportError:
        logger.warning("Desktop notifications - unavailable")

    try:
        import pystray
        from pystray import MenuItem as item
        SYSTEM_TRAY_AVAILABLE = True
        logger.info("System tray - available")
    except ImportError:
        logger.warning("System tray - unavailable")
        
except ImportError as e:
    logger.critical(f"Critical import error: {e}")
    print(f"Critical dependency missing: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

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

class Tooltip:
    """Simple tooltip class for tkinter widgets"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                      background="#ffffe0", relief='solid', borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=4, ipady=2)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

class NotificationManager:
    """A robust, multi-backend notification manager with fallbacks and diagnostics."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.last_notification_time = 0
        self.settings = app_instance.settings # Shortcut to app settings

        # Backend availability
        self.backends = {'plyer': False, 'win10toast': False, 'tk': True}
        self._win10toast_toaster = None
        self._detect_backends()

        # Notification statistics
        self.stats = {
            'total_attempts': 0, 'success': 0, 'failed': 0, 'debounced': 0, 'forced': 0,
            'by_backend': {'plyer': 0, 'win10toast': 0, 'tk': 0}
        }
        feature/robust-notifications-v2.1.2
        
    def _detect_backends(self):
        """Detect and log available notification backends."""
        logger.info("Notification Backend Diagnostics:")


        feature/robust-notifications-v2.1.2
        
    def _detect_backends(self):
        """Detect and log available notification backends."""
        logger.info("Notification Backend Diagnostics:"

    def _detect_backends(self):
        """Detect and log available notification backends."""
        logger.info("Notification Backend Diagnostics:")
        
        main
        main
        # 1. Plyer
        global NOTIFICATIONS_AVAILABLE
        if NOTIFICATIONS_AVAILABLE:
            self.backends['plyer'] = True
            logger.info(" - Plyer: Available")
        else:
            logger.warning(" - Plyer: Unavailable (plyer library failed to import)")

        # 2. win10toast (Windows only)
        if platform.system() == "Windows":
            try:
                from win10toast import ToastNotifier
                self._win10toast_toaster = ToastNotifier()
                self.backends['win10toast'] = True
                logger.info(" - win10toast: Available")
            except ImportError:
                logger.warning(" - win10toast: Unavailable. For better Windows notifications, run: pip install win10toast")
            except Exception as e:
                logger.error(f" - win10toast: Failed to initialize. Error: {e}")

        # 3. Tkinter (always available as a fallback)
        logger.info(" - Tkinter: Available (as a fallback)")

    def send_notification(self, title: str, message: str, timeout: int = 8) -> bool:
        """DEPRECATED: Legacy method for internal compatibility. Use notify() instead."""
        self.notify(title, message, duration=timeout)
        # Old method returned bool, let's keep that for compatibility, though it's less meaningful now
        return True

    def notify(self, title: str, message: str, duration: int = 5, *, force: bool = False, debounce_bypass: bool = False, backend_hint: str | None = None) -> None:
        """
        Send a notification using the best available backend with fallbacks.

        Args:
            title (str): The notification title.
            message (str): The notification body.
            duration (int): Display duration in seconds.
            force (bool): Bypasses OS heuristics if possible (e.g., for win10toast).
            debounce_bypass (bool): Ignores local cooldown.
            backend_hint (str | None): Tries a specific backend first ("plyer", "win10toast", "tk").
        """
        self.stats['total_attempts'] += 1
        if force:
            self.stats['forced'] += 1

        # 1. Handle debounce unless bypassed
        if not debounce_bypass:
            cooldown = self.settings.get('min_notification_interval', 6)
            now = time.time()
            if now - self.last_notification_time < cooldown:
                logger.debug(f"Notification '{title}' debounced. Cooldown active.")
                self.stats['debounced'] += 1
                return

        # 2. Clean inputs
        clean_title = str(title).strip()[:100]
        clean_message = str(message).strip()[:500]

        # 3. Determine backend order
        backend_order = []
        # Use hint if provided and available
        if backend_hint and self.backends.get(backend_hint):
            backend_order.append(backend_hint)

        # Add remaining backends in default priority
        default_order = ['plyer', 'win10toast', 'tk']
        for b in default_order:
            if b not in backend_order:
                backend_order.append(b)

        # 4. Loop through backends and attempt to send
        notification_sent = False
        for backend in backend_order:
            # Skip unavailable backends
            if not self.backends.get(backend):
                continue
            
            # Skip if platform doesn't match
            if backend == 'win10toast' and platform.system() != "Windows":
                continue

            # Handle debug setting to force Tkinter
            use_tk_only = self.settings.get('debug', {}).get('use_tkinter_fallback_only', False)
            if use_tk_only and backend != 'tk':
                logger.debug(f"Skipping '{backend}' due to 'Use Tkinter fallback only' debug setting.")
                continue

            start_time = time.time()
            try:
                logger.info(f"Attempting notification via backend: '{backend}'")

                if backend == 'plyer':
                    notification.notify(
                        title=clean_title,
                        message=clean_message,
                        app_name="CryptoPulse Monitor",
                        timeout=duration
                    )
                    notification_sent = True

                elif backend == 'win10toast':
                    # threaded=True makes it non-blocking
                    self._win10toast_toaster.show_toast(
                        title=clean_title,
                        msg=clean_message,
                        duration=duration,
                        threaded=True
                    )
                    notification_sent = True

                elif backend == 'tk':
                    if self._show_tkinter_notification(clean_title, clean_message, duration):
                        notification_sent = True

                if notification_sent:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(f"Notification sent successfully via '{backend}' in {duration_ms:.2f}ms.")
                    self.stats['success'] += 1
                    self.stats['by_backend'][backend] += 1
                    self.last_notification_time = time.time()
                    break  # Exit loop on first success

            except Exception as e:
                logger.warning(f"Backend '{backend}' failed: {e}", exc_info=False)
                # Continue to next backend

        if not notification_sent:
            self.stats['failed'] += 1
            logger.error("All notification backends failed.")
        

    def _show_tkinter_notification(self, title: str, message: str, duration: int) -> bool:
        """Fallback notification using a simple Tkinter window."""
        try:
            # Use app's safe_gui_call to ensure thread safety
            self.app.safe_gui_call(lambda: self._create_tk_popup(title, message, duration))
            return True
        except Exception as e:
            logger.error(f"Failed to show Tkinter fallback notification: {e}")
            return False

    def _create_tk_popup(self, title, message, duration):
        """Creates the Tkinter popup window."""
        popup = tk.Toplevel(self.app.root)
        popup.title(title)
        popup.configure(bg=self.app.colors['surface'])
        popup.transient(self.app.root)
        popup.attributes("-topmost", True)

        # Center popup on the main window
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() // 2) - 150
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() // 2) - 50
        popup.geometry(f"350x100+{x}+{y}")

        label = ttk.Label(popup, text=message, wraplength=330, style='Info.TLabel', justify='center')
        label.pack(padx=20, pady=20, expand=True, fill='both')

        # Auto-close after duration
        popup.after(duration * 1000, popup.destroy)

class SafeSystemTray:
    """Safe system tray manager with fallbacks"""
    
    def __init__(self):
        self.available = SYSTEM_TRAY_AVAILABLE
        self.tray_icon = None
        self.tray_image = None
        self.running = False
        
    def create_icon(self) -> bool:
        """Create system tray icon with error handling"""
        if not self.available:
            return False
            
        try:
            # Create professional icon
            size = 64
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            center = size // 2
            
            # Outer circle
            draw.ellipse([4, 4, size-4, size-4], 
                        fill='#3B82F6', outline='#1E40AF', width=2)
            
            # Inner crypto symbol
            bar_width = 4
            bar_height = 24
            bar_y = center - bar_height // 2
            
            draw.rectangle([center-10, bar_y, center-10+bar_width, bar_y+bar_height], 
                          fill='white')
            draw.rectangle([center+6, bar_y, center+6+bar_width, bar_y+bar_height], 
                          fill='white')
            
            draw.rectangle([center-14, center-6, center+14, center-2], fill='white')
            draw.rectangle([center-14, center+2, center+14, center+6], fill='white')
            
            self.tray_image = image
            return True
            
        except Exception as e:
            logger.error(f"Tray icon creation failed: {e}")
            return False
    
    def setup_tray(self, app_instance) -> bool:
        """Setup system tray with error handling"""
        if not self.available or not self.create_icon():
            return False
            
        try:
            self.tray_icon = pystray.Icon(
                "cryptopulse_monitor",
                self.tray_image,
                "CryptoPulse Monitor",
                menu=pystray.Menu(
                    item('Show CryptoPulse', app_instance.show_window, default=True),
                    item('Toggle Monitoring', app_instance.toggle_monitoring),
                    pystray.Menu.SEPARATOR,
                    item('Settings', lambda: app_instance.show_window() or app_instance.toggle_settings()),
                    item('About', lambda: app_instance.show_window() or app_instance.show_about()),
                    pystray.Menu.SEPARATOR,
                    item('Exit', app_instance.quit_application)
                )
            )
            logger.info("System tray configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"System tray setup failed: {e}")
            return False
    
    def run_tray(self):
        """Run system tray with error recovery"""
        if not self.tray_icon:
            return
            
        try:
            self.running = True
            self.tray_icon.run()
        except Exception as e:
            logger.error(f"System tray runtime error: {e}")
        finally:
            self.running = False
    
    def stop_tray(self):
        """Stop system tray safely"""
        if self.tray_icon and self.running:
            try:
                self.tray_icon.stop()
            except Exception as e:
                logger.warning(f"Tray stop error: {e}")

class CryptoPulseMonitor:
    """Professional Cryptocurrency Price Monitor Application"""
    
    def __init__(self):
        logger.info("Initializing CryptoPulse Monitor v2.1.0...")
        
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
        self.gui_initialized = False
        
        # Default settings must be initialized before managers that use them
        self.settings = self.get_default_settings()

        # Safe managers
        self.notification_manager = NotificationManager(self)
        self.tray_manager = SafeSystemTray()
        
        # Professional color scheme
        self.colors = {
            'primary': '#3B82F6', 'secondary': '#6B7280', 'accent': '#8B5CF6',
            'background': '#0F172A', 'surface': '#1E293B', 'card': '#334155',
            'text_primary': '#F8FAFC', 'text_secondary': '#CBD5E1', 'text_muted': '#64748B',
            'success': '#10B981', 'warning': '#F59E0B', 'error': '#EF4444',
            'chart_grid': '#374151', 'border': '#475569'
        }
        
        # Cryptocurrency display names
        self.crypto_names = {
            'bitcoin': 'Bitcoin (BTC)', 'ethereum': 'Ethereum (ETH)',
            'cardano': 'Cardano (ADA)', 'solana': 'Solana (SOL)',
            'litecoin': 'Litecoin (LTC)', 'ripple': 'Ripple (XRP)',
            'polkadot': 'Polkadot (DOT)', 'chainlink': 'Chainlink (LINK)'
        }
        
        # API configuration
        self.api_endpoints = {
            APIProvider.COINGECKO: {
                'base_url': 'https://api.coingecko.com/api/v3',
                'price_endpoint': '/simple/price', 'timeout': 10
            },
            APIProvider.BINANCE: {
                'base_url': 'https://api.binance.com/api/v3',
                'price_endpoint': '/ticker/24hr', 'timeout': 8
            },
            APIProvider.CRYPTOCOMPARE: {
                'base_url': 'https://min-api.cryptocompare.com/data',
                'price_endpoint': '/pricemultifull', 'timeout': 12
            }
        }
        
        # Initialize components
        self.load_settings()
        self.load_app_state()
        logger.info("CryptoPulse Monitor initialized successfully")

    def get_default_settings(self) -> dict:
        """Get default application settings"""
        return {
            'refresh_interval': 30,
            'cryptocurrency': 'bitcoin',
            'vs_currency': 'usd',
            'api_provider': APIProvider.COINGECKO.value,
            'enable_notifications': True,
            'min_notification_interval': 6,
            'alert_config': {
                'price_drop': {'enabled': True, 'threshold': 2.0},
                'price_rise': {'enabled': False, 'threshold': 5.0},
                'volume_spike': {'enabled': True, 'threshold': 300.0}
            },
            'debug': {
                'force_startup_test': False,
                'use_tkinter_fallback_only': False
            },
            'ui_config': {
                'window_width': 1200, 'window_height': 800,
                'window_x': 100, 'window_y': 100,
                'auto_minimize': False
            },
            'data_retention': {
                'price_history_hours': 168,
                'alert_history_count': 100
            }
        }

    def load_settings(self) -> None:
        """Load settings with comprehensive error handling"""
        try:
            settings_dir = Path.home() / '.cryptopulse'
            settings_dir.mkdir(exist_ok=True)
            settings_path = settings_dir / 'settings.json'
            
            if settings_path.exists():
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        saved_settings = json.load(f)
                    
                    # Merge settings safely
                    self._merge_settings(self.settings, saved_settings)
                    logger.info("Settings loaded successfully")
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Settings file corrupted, using defaults: {e}")
                except Exception as e:
                    logger.warning(f"Could not load settings: {e}")
            else:
                logger.info("No existing settings found, using defaults")
                
        except Exception as e:
            logger.error(f"Settings loading error: {e}")

    def _merge_settings(self, default: dict, saved: dict) -> None:
        """Recursively merge saved settings into defaults safely"""
        for key, value in saved.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_settings(default[key], value)
                else:
                    # Validate setting value
                    try:
                        if key == 'refresh_interval':
                            default[key] = max(10, int(value))
                        elif key == 'cryptocurrency' and value in self.crypto_names:
                            default[key] = value
                        elif key == 'api_provider' and value in [p.value for p in APIProvider]:
                            default[key] = value
                        else:
                            default[key] = value
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid setting value for {key}: {value}")

    def save_settings(self) -> None:
        """Save settings with atomic write and error handling"""
        try:
            settings_dir = Path.home() / '.cryptopulse'
            settings_dir.mkdir(exist_ok=True)
            settings_path = settings_dir / 'settings.json'
            temp_path = settings_path.with_suffix('.tmp')
            
            # Atomic write
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            temp_path.replace(settings_path)
            
            logger.debug("Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def load_app_state(self) -> None:
        """Loads application state from state.json."""
        self.app_state = {}
        try:
            state_path = Path.home() / '.cryptopulse' / 'state.json'
            if state_path.exists():
                with open(state_path, 'r', encoding='utf-8') as f:
                    self.app_state = json.load(f)
                logger.info("Application state loaded.")
        except Exception as e:
            logger.warning(f"Could not load application state: {e}")

    def save_app_state(self) -> None:
        """Saves application state to state.json."""
        try:
            state_dir = Path.home() / '.cryptopulse'
            state_dir.mkdir(exist_ok=True)
            state_path = state_dir / 'state.json'
            temp_path = state_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.app_state, f, indent=2)
            temp_path.replace(state_path)
            logger.debug("Application state saved.")
        except Exception as e:
            logger.error(f"Error saving application state: {e}")

    def perform_startup_self_check(self):
        """Performs a one-time notification self-check on startup."""
        # Ensure this setting is checked safely
        debug_settings = self.settings.get('debug', {})
        force_test = debug_settings.get('force_startup_test', False)

        if not self.app_state.get('startup_notification_sent') or force_test:
            logger.info("Performing startup notification self-check...")
            self.notification_manager.notify(
                "CryptoPulse Ready",
                "Notifications are enabled.",
                force=True,
                debounce_bypass=True
            )
            self.app_state['startup_notification_sent'] = True
            self.save_app_state()

    def setup_gui(self) -> bool:
        """Setup GUI with comprehensive error handling"""
        try:
            self.root = tk.Tk()
            self.root.title("CryptoPulse Monitor v2.1.0")
            
            # Window configuration with error handling
            try:
                width = self.settings['ui_config']['window_width']
                height = self.settings['ui_config']['window_height']
                x = self.settings['ui_config']['window_x']
                y = self.settings['ui_config']['window_y']
                self.root.geometry(f"{width}x{height}+{x}+{y}")
            except Exception as e:
                logger.warning(f"Could not set window geometry: {e}")
                self.root.geometry("1200x800+100+100")
            
            self.root.configure(bg=self.colors['background'])
            self.root.minsize(800, 600)
            
            # Configure styles
            self.setup_styles()
            
            # Create layout
            self.create_header()
            self.create_main_content()
            self.create_sidebar()
            self.create_status_bar()
            
            # Bind events
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.bind("<Configure>", self.on_window_configure)
            self.root.bind_all('<F9>', self.run_test_notification)
            
            # Set icon
            self.set_window_icon()
            
            self.gui_initialized = True
            return True
            
        except Exception as e:
            logger.critical(f"GUI setup failed: {e}")
            return False

    def set_window_icon(self) -> None:
        """Set window icon with error handling"""
        try:
            icon_size = 32
            icon = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(icon)
            
            center = icon_size // 2
            
            # Draw icon
            draw.ellipse([2, 2, icon_size-2, icon_size-2], 
                        fill='#3B82F6', outline='#1E40AF', width=1)
            draw.rectangle([center-6, center-8, center-2, center+8], fill='white')
            draw.rectangle([center+2, center-8, center+6, center+8], fill='white')
            draw.rectangle([center-8, center-2, center+8, center+2], fill='white')
            
            photo = ImageTk.PhotoImage(icon)
            self.root.iconphoto(True, photo)
            
        except Exception as e:
            logger.debug(f"Could not set window icon: {e}")

    def setup_styles(self) -> None:
        """Configure ttk styles with error handling"""
        try:
            style = ttk.Style()
            style.theme_use('clam')
            
            styles = {
                'App.TFrame': {'background': self.colors['background']},
                'Card.TFrame': {'background': self.colors['surface'], 'relief': 'flat'},
                'Header.TLabel': {'background': self.colors['surface'], 
                                'foreground': self.colors['text_primary'], 
                                'font': ('Segoe UI', 18, 'bold')},
                'Price.TLabel': {'background': self.colors['surface'], 
                               'foreground': self.colors['text_primary'], 
                               'font': ('Segoe UI', 42, 'bold')},
                'Change.TLabel': {'background': self.colors['surface'], 
                                'font': ('Segoe UI', 16, 'bold')},
                'Info.TLabel': {'background': self.colors['surface'], 
                              'foreground': self.colors['text_secondary'], 
                              'font': ('Segoe UI', 11)},
                'Title.TLabel': {'background': self.colors['surface'], 
                               'foreground': self.colors['text_primary'], 
                               'font': ('Segoe UI', 14, 'bold')}
            }
            
            for style_name, config in styles.items():
                style.configure(style_name, **config)
                
        except Exception as e:
            logger.warning(f"Style setup failed: {e}")

    def create_header(self) -> None:
        """Create application header"""
        try:
            header_frame = ttk.Frame(self.root, style='Card.TFrame')
            header_frame.pack(fill='x')
            
            # Brand section
            brand_frame = ttk.Frame(header_frame, style='Card.TFrame')
            brand_frame.pack(side='left', padx=20, pady=15)
            
            title = ttk.Label(brand_frame, text="CryptoPulse Monitor", style='Header.TLabel')
            title.pack(anchor='w')
            
            subtitle = ttk.Label(brand_frame, text="Professional Cryptocurrency Tracking", 
                                style='Info.TLabel')
            subtitle.pack(anchor='w', pady=(2, 0))
            
            # Controls
            controls_frame = ttk.Frame(header_frame, style='Card.TFrame')
            controls_frame.pack(side='right', padx=20, pady=15)
            
            # Buttons
            test_btn = self.create_button(controls_frame, "Test Notif",
                                         self.colors['secondary'], self.run_test_notification)
            test_btn.pack(side='right', padx=5)
            Tooltip(test_btn, "Send a test toast now (F9)")

            self.settings_btn = self.create_button(controls_frame, "Settings", 
                                                 self.colors['primary'], self.toggle_settings)
            self.settings_btn.pack(side='right', padx=5)
            
            about_btn = self.create_button(controls_frame, "About", 
                                         self.colors['accent'], self.show_about)
            about_btn.pack(side='right', padx=5)
            
            # Minimize button (only if tray available)
            if self.tray_manager.available:
                minimize_btn = self.create_button(controls_frame, "Minimize", 
                                                self.colors['warning'], self.minimize_to_tray)
                minimize_btn.pack(side='right', padx=2)
                
        except Exception as e:
            logger.error(f"Header creation failed: {e}")

    def create_button(self, parent, text: str, color: str, command, width: int = None) -> tk.Button:
        """Create styled button with error handling"""
        try:
            btn = tk.Button(parent, text=text, command=command, bg=color, fg='white',
                          font=('Segoe UI', 10, 'bold'), border=0, padx=15, pady=6,
                          cursor='hand2', activebackground=self.darken_color(color))
            
            if width:
                btn.config(width=width, padx=5)
            
            # Hover effects
            def on_enter(e):
                try:
                    btn.config(bg=self.lighten_color(color))
                except:
                    pass
            def on_leave(e):
                try:
                    btn.config(bg=color)
                except:
                    pass
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            
            return btn
        except Exception as e:
            logger.error(f"Button creation failed: {e}")
            # Return simple button as fallback
            return tk.Button(parent, text=text, command=command)

    def lighten_color(self, hex_color: str, factor: float = 1.2) -> str:
        """Lighten color with error handling"""
        try:
            hex_color = hex_color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            new_rgb = tuple(min(255, int(c * factor)) for c in rgb)
            return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"
        except:
            return hex_color

    def darken_color(self, hex_color: str, factor: float = 0.8) -> str:
        """Darken color with error handling"""
        return self.lighten_color(hex_color, factor)

    def create_main_content(self) -> None:
        """Create main content area"""
        try:
            main_frame = ttk.Frame(self.root, style='App.TFrame')
            main_frame.pack(fill='both', expand=True, padx=20, pady=10)
            
            left_frame = ttk.Frame(main_frame, style='App.TFrame')
            left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
            
            self.create_price_card(left_frame)
            self.create_chart_card(left_frame)
            self.create_controls_card(left_frame)
            
        except Exception as e:
            logger.error(f"Main content creation failed: {e}")

    def create_price_card(self, parent) -> None:
        """Create price display card"""
        try:
            price_card = ttk.Frame(parent, style='Card.TFrame')
            price_card.pack(fill='x', pady=(0, 15))
            
            # Header
            header_frame = ttk.Frame(price_card, style='Card.TFrame')
            header_frame.pack(fill='x', padx=25, pady=(20, 10))
            
            self.crypto_display_label = ttk.Label(header_frame, 
                                                text=self.get_crypto_display_name(), 
                                                style='Title.TLabel')
            self.crypto_display_label.pack(side='left')
            
            # Live indicator
            self.live_indicator = tk.Canvas(header_frame, width=12, height=12,
                                          bg=self.colors['surface'], highlightthickness=0)
            self.live_indicator.pack(side='right', padx=(10, 0))
            
            # Price display
            price_frame = ttk.Frame(price_card, style='Card.TFrame')
            price_frame.pack(fill='x', padx=25, pady=(0, 10))
            
            self.price_label = ttk.Label(price_frame, text="Loading...", style='Price.TLabel')
            self.price_label.pack(anchor='w')
            
            # Change display
            change_frame = ttk.Frame(price_card, style='Card.TFrame')
            change_frame.pack(fill='x', padx=25, pady=(0, 10))
            
            self.change_label = ttk.Label(change_frame, text="---", style='Change.TLabel')
            self.change_label.pack(anchor='w')
            
            # Metrics
            metrics_frame = ttk.Frame(price_card, style='Card.TFrame')
            metrics_frame.pack(fill='x', padx=25, pady=(0, 20))
            
            self.volume_label = ttk.Label(metrics_frame, text="Volume: ---", style='Info.TLabel')
            self.volume_label.pack(side='left')
            
            self.update_label = ttk.Label(metrics_frame, text="Last updated: Never", 
                                        style='Info.TLabel')
            self.update_label.pack(side='right')
            
        except Exception as e:
            logger.error(f"Price card creation failed: {e}")

    def get_crypto_display_name(self) -> str:
        """Get formatted display name for current cryptocurrency"""
        try:
            crypto = self.settings['cryptocurrency']
            currency = self.settings['vs_currency'].upper()
            
            if crypto in self.crypto_names:
                return f"{self.crypto_names[crypto]}/{currency}"
            else:
                return f"{crypto.title()} ({crypto[:3].upper()})/{currency}"
        except Exception:
            return "Bitcoin (BTC)/USD"

    def create_chart_card(self, parent) -> None:
        """Create chart card with error handling"""
        try:
            chart_card = ttk.Frame(parent, style='Card.TFrame')
            chart_card.pack(fill='both', expand=True, pady=(0, 15))
            
            # Chart header
            chart_header = ttk.Frame(chart_card, style='Card.TFrame')
            chart_header.pack(fill='x', padx=25, pady=(20, 10))
            
            chart_title = ttk.Label(chart_header, text="Price History", style='Title.TLabel')
            chart_title.pack(side='left')
            
            # Timeframe buttons
            timeframe_frame = ttk.Frame(chart_header, style='Card.TFrame')
            timeframe_frame.pack(side='right')
            
            self.timeframe_buttons = {}
            for period in TimeFrame:
                active = period == self.current_timeframe
                color = self.colors['primary'] if active else self.colors['secondary']
                btn = self.create_button(timeframe_frame, period.value, color,
                                       lambda p=period: self.change_chart_timeframe(p), width=3)
                btn.pack(side='left', padx=2)
                self.timeframe_buttons[period] = btn
            
            # Chart setup
            self.setup_chart(chart_card)
            
        except Exception as e:
            logger.error(f"Chart card creation failed: {e}")

    def setup_chart(self, parent) -> None:
        """Setup matplotlib chart with error handling"""
        try:
            # Configure matplotlib
            plt.style.use('dark_background')
            
            self.fig = Figure(figsize=(10, 5), dpi=100, facecolor=self.colors['surface'])
            self.ax = self.fig.add_subplot(111, facecolor=self.colors['card'])
            
            # Styling
            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['bottom'].set_color(self.colors['border'])
            self.ax.spines['left'].set_color(self.colors['border'])
            self.ax.tick_params(colors=self.colors['text_secondary'], labelsize=10)
            self.ax.grid(True, alpha=0.2, color=self.colors['chart_grid'])
            
            # Initial setup
            self.price_line, = self.ax.plot([], [], color=self.colors['primary'], 
                                          linewidth=2.5, alpha=0.9)
            self.ax.set_ylabel('Price ($)', color=self.colors['text_primary'], fontsize=11)
            self.ax.set_title('Price Trend', color=self.colors['text_primary'], fontsize=12)
            
            # Add to GUI
            self.canvas = FigureCanvasTkAgg(self.fig, parent)
            self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=25, pady=(0, 20))
            
        except Exception as e:
            logger.error(f"Chart setup failed: {e}")

    def create_controls_card(self, parent) -> None:
        """Create controls card"""
        try:
            controls_card = ttk.Frame(parent, style='Card.TFrame')
            controls_card.pack(fill='x')
            
            controls_frame = ttk.Frame(controls_card, style='Card.TFrame')
            controls_frame.pack(fill='x', padx=25, pady=20)
            
            # Left controls
            left_controls = ttk.Frame(controls_frame, style='Card.TFrame')
            left_controls.pack(side='left')
            
            self.monitor_btn = self.create_button(left_controls, "Pause", 
                                                self.colors['primary'], self.toggle_monitoring)
            self.monitor_btn.pack(side='left', padx=(0, 10))
            
            refresh_btn = self.create_button(left_controls, "Refresh", 
                                           self.colors['success'], self.manual_refresh)
            refresh_btn.pack(side='left', padx=(0, 10))
            
            # Right controls
            right_controls = ttk.Frame(controls_frame, style='Card.TFrame')
            right_controls.pack(side='right')
            
            export_btn = self.create_button(right_controls, "Export", 
                                          self.colors['accent'], self.export_data)
            export_btn.pack(side='right', padx=10)
            
            clear_btn = self.create_button(right_controls, "Clear", 
                                         self.colors['error'], self.clear_history)
            clear_btn.pack(side='right')
            
        except Exception as e:
            logger.error(f"Controls creation failed: {e}")

    def create_sidebar(self) -> None:
        """Create sidebar with error handling"""
        try:
            self.sidebar = ttk.Frame(self.root, style='App.TFrame', width=320)
            self.sidebar.pack(side='right', fill='y', padx=(10, 20), pady=10)
            self.sidebar.pack_propagate(False)
            
            self.create_status_card()
            self.create_alerts_card()
            self.create_stats_card()
            
        except Exception as e:
            logger.error(f"Sidebar creation failed: {e}")

    def create_status_card(self) -> None:
        """Create connection status card"""
        try:
            status_card = ttk.Frame(self.sidebar, style='Card.TFrame')
            status_card.pack(fill='x', pady=(0, 15))
            
            # Header
            status_header = ttk.Frame(status_card, style='Card.TFrame')
            status_header.pack(fill='x', padx=20, pady=(15, 10))
            
            ttk.Label(status_header, text="Connection Status", style='Title.TLabel').pack(side='left')
            
            # Content
            status_content = ttk.Frame(status_card, style='Card.TFrame')
            status_content.pack(fill='x', padx=20, pady=(0, 15))
            
            self.connection_label = ttk.Label(status_content, text="Connecting...", style='Info.TLabel')
            self.connection_label.pack(anchor='w')
            
            self.api_provider_label = ttk.Label(status_content, text="Provider: CoinGecko", style='Info.TLabel')
            self.api_provider_label.pack(anchor='w', pady=(5, 0))
            
            self.next_update_label = ttk.Label(status_content, text="Next update: ---", style='Info.TLabel')
            self.next_update_label.pack(anchor='w', pady=(5, 0))

            # Manual notify button
            manual_notify_btn = self.create_button(status_card, "Notify Now",
                                                   self.colors['accent'], self.run_manual_notification)
            manual_notify_btn.pack(fill='x', padx=20, pady=(10, 15))
            
        except Exception as e:
            logger.error(f"Status card creation failed: {e}")

    def create_alerts_card(self) -> None:
        """Create alerts card"""
        try:
            alerts_card = ttk.Frame(self.sidebar, style='Card.TFrame')
            alerts_card.pack(fill='both', expand=True, pady=(0, 15))
            
            # Header
            alerts_header = ttk.Frame(alerts_card, style='Card.TFrame')
            alerts_header.pack(fill='x', padx=20, pady=(15, 10))
            
            ttk.Label(alerts_header, text="Recent Alerts", style='Title.TLabel').pack(side='left')
            
            clear_btn = self.create_button(alerts_header, "Clear", self.colors['secondary'],
                                         self.clear_alerts, width=5)
            clear_btn.pack(side='right')
            
            # Alerts list
            self.alerts_listbox = tk.Listbox(alerts_card, bg=self.colors['card'],
                                           fg=self.colors['text_primary'], font=('Segoe UI', 9),
                                           border=0, selectbackground=self.colors['primary'])
            self.alerts_listbox.pack(fill='both', expand=True, padx=20, pady=(0, 20))
            
        except Exception as e:
            logger.error(f"Alerts card creation failed: {e}")

    def create_stats_card(self) -> None:
        """Create statistics card"""
        try:
            stats_card = ttk.Frame(self.sidebar, style='Card.TFrame')
            stats_card.pack(fill='x')
            
            # Header
            stats_header = ttk.Frame(stats_card, style='Card.TFrame')
            stats_header.pack(fill='x', padx=20, pady=(15, 10))
            
            ttk.Label(stats_header, text="24H Statistics", style='Title.TLabel').pack(side='left')
            
            # Content
            stats_content = ttk.Frame(stats_card, style='Card.TFrame')
            stats_content.pack(fill='x', padx=20, pady=(0, 15))
            
            self.high_label = ttk.Label(stats_content, text="24H High: ---", style='Info.TLabel')
            self.high_label.pack(anchor='w')
            
            self.low_label = ttk.Label(stats_content, text="24H Low: ---", style='Info.TLabel')
            self.low_label.pack(anchor='w', pady=(5, 0))
            
            self.avg_label = ttk.Label(stats_content, text="24H Average: ---", style='Info.TLabel')
            self.avg_label.pack(anchor='w', pady=(5, 0))
            
        except Exception as e:
            logger.error(f"Stats card creation failed: {e}")

    def create_status_bar(self) -> None:
        """Create status bar"""
        try:
            self.status_bar = ttk.Frame(self.root, style='Card.TFrame')
            self.status_bar.pack(side='bottom', fill='x')
            
            status_content = ttk.Frame(self.status_bar, style='Card.TFrame')
            status_content.pack(fill='x', padx=10, pady=8)
            
            self.status_text = ttk.Label(status_content, text="Ready", style='Info.TLabel')
            self.status_text.pack(side='left')
            
            version_label = ttk.Label(status_content, text="v2.1.0", style='Info.TLabel')
            version_label.pack(side='right')
            
        except Exception as e:
            logger.error(f"Status bar creation failed: {e}")

    def start_monitoring(self) -> None:
        """Start monitoring thread with error handling"""
        try:
            # Setup tray first
            if self.tray_manager.available:
                self.tray_manager.setup_tray(self)
            
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(target=self.monitor_price_loop, 
                                                    daemon=True, name="PriceMonitor")
            self.monitoring_thread.start()
            logger.info("Price monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.safe_show_error("Monitoring Error", f"Failed to start monitoring: {e}")

    def monitor_price_loop(self) -> None:
        """Main monitoring loop with bulletproof error handling"""
        while not self.shutdown_requested:
            try:
                if self.is_monitoring:
                    self.fetch_and_update_price()
                    
                    # Update next refresh time
                    next_update = datetime.now() + timedelta(seconds=self.settings['refresh_interval'])
                    self.safe_gui_call(lambda: self.update_next_refresh_time(next_update))
                    
                    # Reset failures on success
                    self.api_failures = 0
                else:
                    # Update status when paused
                    self.safe_gui_call(lambda: self.update_connection_status("Monitoring Paused", 
                                                                          self.colors['warning']))
                
            except Exception as e:
                self.handle_monitoring_error(e)
            
            # Efficient sleep with responsiveness
            self.sleep_with_interrupt(self.settings['refresh_interval'])

    def sleep_with_interrupt(self, total_seconds: int) -> None:
        """Sleep with interrupt capability and pause efficiency"""
        for i in range(total_seconds):
            if self.shutdown_requested:
                break
            
            time.sleep(1)
            
            # When paused, reduce CPU usage
            if not self.is_monitoring:
                time.sleep(min(2, total_seconds - i))

    def safe_gui_call(self, func) -> None:
        """Safe GUI thread call with error handling"""
        try:
            if self.gui_initialized and self.root and self.root.winfo_exists():
                self.root.after(0, func)
        except Exception as e:
            logger.debug(f"GUI call failed: {e}")

    def fetch_and_update_price(self) -> None:
        """Fetch price with smart provider rotation"""
        # Get provider priority list
        primary = APIProvider(self.settings.get('api_provider', 'coingecko'))
        providers = [primary] + [p for p in APIProvider if p != primary]
        
        for provider in providers:
            try:
                self.safe_gui_call(lambda: self.update_connection_status("Fetching...", 
                                                                       self.colors['warning']))
                
                price_data = self.fetch_price_from_provider(provider)
                if price_data:
                    # Update provider info
                    self.safe_gui_call(lambda p=provider: self.api_provider_label.config(
                        text=f"Provider: {p.value.title()}"))
                    
                    # Update display
                    self.safe_gui_call(lambda pd=price_data: self.update_price_display(pd))
                    self.safe_gui_call(lambda: self.update_connection_status("Connected", 
                                                                           self.colors['success']))
                    return
                    
            except Exception as e:
                logger.warning(f"Provider {provider.value} failed: {e}")
                continue
        
        # All providers failed
        raise Exception("All API providers failed")

    def fetch_price_from_provider(self, provider: APIProvider) -> Optional[PriceData]:
        """Fetch from specific provider with timeout"""
        config = self.api_endpoints[provider]
        
        if provider == APIProvider.COINGECKO:
            return self.fetch_from_coingecko(config)
        elif provider == APIProvider.BINANCE:
            return self.fetch_from_binance(config)
        elif provider == APIProvider.CRYPTOCOMPARE:
            return self.fetch_from_cryptocompare(config)
        
        return None

    def fetch_from_coingecko(self, config: dict) -> Optional[PriceData]:
        """Fetch from CoinGecko with correct change calculation"""
        try:
            url = f"{config['base_url']}{config['price_endpoint']}"
            params = {
                'ids': self.settings['cryptocurrency'],
                'vs_currencies': self.settings['vs_currency'],
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true',
                'include_market_cap': 'true'
            }
            
            response = requests.get(url, params=params, timeout=config['timeout'])
            response.raise_for_status()
            
            data = response.json()
            crypto_data = data.get(self.settings['cryptocurrency'], {})
            
            if not crypto_data:
                raise ValueError("No data returned")
            
            currency = self.settings['vs_currency']
            current_price = float(crypto_data.get(currency, 0))
            change_percent = float(crypto_data.get(f'{currency}_24h_change', 0))
            
            # Calculate absolute change from percentage
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
            logger.debug(f"CoinGecko fetch failed: {e}")
            raise

    def fetch_from_binance(self, config: dict) -> Optional[PriceData]:
        """Fetch from Binance with symbol mapping"""
        try:
            symbol_map = {
                'bitcoin': 'BTCUSDT', 'ethereum': 'ETHUSDT', 'cardano': 'ADAUSDT',
                'solana': 'SOLUSDT', 'litecoin': 'LTCUSDT', 'ripple': 'XRPUSDT',
                'polkadot': 'DOTUSDT', 'chainlink': 'LINKUSDT'
            }
            
            symbol = symbol_map.get(self.settings['cryptocurrency'])
            if not symbol:
                raise ValueError(f"Unsupported cryptocurrency: {self.settings['cryptocurrency']}")
            
            url = f"{config['base_url']}{config['price_endpoint']}"
            params = {'symbol': symbol}
            
            response = requests.get(url, params=params, timeout=config['timeout'])
            response.raise_for_status()
            
            data = response.json()
            
            return PriceData(
                symbol=self.settings['cryptocurrency'].upper(),
                price=float(data['lastPrice']),
                change_24h=float(data['priceChange']),
                change_percent_24h=float(data['priceChangePercent']),
                timestamp=datetime.now(),
                volume_24h=float(data.get('volume', 0))
            )
            
        except Exception as e:
            logger.debug(f"Binance fetch failed: {e}")
            raise

    def fetch_from_cryptocompare(self, config: dict) -> Optional[PriceData]:
        """Fetch from CryptoCompare with symbol mapping"""
        try:
            symbol_map = {
                'bitcoin': 'BTC', 'ethereum': 'ETH', 'cardano': 'ADA',
                'solana': 'SOL', 'litecoin': 'LTC', 'ripple': 'XRP',
                'polkadot': 'DOT', 'chainlink': 'LINK'
            }
            
            symbol = symbol_map.get(self.settings['cryptocurrency'])
            if not symbol:
                raise ValueError(f"Unsupported cryptocurrency: {self.settings['cryptocurrency']}")
            
            url = f"{config['base_url']}{config['price_endpoint']}"
            params = {
                'fsyms': symbol,
                'tsyms': self.settings['vs_currency'].upper()
            }
            
            response = requests.get(url, params=params, timeout=config['timeout'])
            response.raise_for_status()
            
            data = response.json()
            crypto_data = data['RAW'][symbol][self.settings['vs_currency'].upper()]
            
            return PriceData(
                symbol=symbol,
                price=float(crypto_data['PRICE']),
                change_24h=float(crypto_data['CHANGE24HOUR']),
                change_percent_24h=float(crypto_data['CHANGEPCT24HOUR']),
                timestamp=datetime.now(),
                volume_24h=float(crypto_data.get('VOLUME24HOURTO', 0))
            )
            
        except Exception as e:
            logger.debug(f"CryptoCompare fetch failed: {e}")
            raise

    def handle_monitoring_error(self, error: Exception) -> None:
        """Handle monitoring errors with backoff"""
        self.api_failures += 1
        logger.error(f"Monitoring error (attempt {self.api_failures}): {error}")
        
        if self.api_failures >= self.max_api_failures:
            self.safe_gui_call(lambda: self.update_connection_status("Connection Failed", 
                                                                   self.colors['error']))
            # Exponential backoff
            backoff_time = min(60, 5 * (2 ** (self.api_failures - 3)))
            time.sleep(backoff_time)
        else:
            self.safe_gui_call(lambda: self.update_connection_status("Retrying...", 
                                                                   self.colors['warning']))

    def update_price_display(self, price_data: PriceData) -> None:
        """Update price display with comprehensive error handling"""
        try:
            self.last_price_data = self.current_price_data
            self.current_price_data = price_data
            
            # Update price
            if hasattr(self, 'price_label'):
                self.price_label.config(text=f"${price_data.price:,.2f}")
            
            # Update change
            change_text, change_color = self.format_price_change(
                price_data.change_24h, price_data.change_percent_24h)
            if hasattr(self, 'change_label'):
                self.change_label.config(text=change_text, foreground=change_color)
            
            # Update volume
            if price_data.volume_24h and hasattr(self, 'volume_label'):
                volume_text = self.format_volume(price_data.volume_24h)
                self.volume_label.config(text=f"24H Volume: {volume_text}")
            
            # Update timestamp
            if hasattr(self, 'update_label'):
                self.update_label.config(
                    text=f"Last updated: {price_data.timestamp.strftime('%H:%M:%S')}")
            
            # Add to history
            self.add_to_price_history(price_data)
            
            # Check alerts
            if not self.is_first_check and self.last_price_data:
                self.check_and_trigger_alerts(self.last_price_data, price_data)
            
            # Update components
            self.update_chart()
            self.update_live_indicator()
            self.update_statistics()
            
            self.is_first_check = False
            
        except Exception as e:
            logger.error(f"Price display update failed: {e}")

    def format_price_change(self, change: float, change_percent: float) -> Tuple[str, str]:
        """Format price change with color"""
        try:
            if change > 0:
                return f"+${abs(change):,.2f} (+{change_percent:.2f}%)", self.colors['success']
            elif change < 0:
                return f"-${abs(change):,.2f} ({change_percent:.2f}%)", self.colors['error']
            else:
                return "No Change (0.00%)", self.colors['text_secondary']
        except Exception:
            return "---", self.colors['text_secondary']

    def format_volume(self, volume: float) -> str:
        """Format volume with units"""
        try:
            if volume >= 1e9:
                return f"${volume/1e9:.2f}B"
            elif volume >= 1e6:
                return f"${volume/1e6:.2f}M"
            elif volume >= 1e3:
                return f"${volume/1e3:.2f}K"
            else:
                return f"${volume:.2f}"
        except Exception:
            return "---"

    def add_to_price_history(self, price_data: PriceData) -> None:
        """Add price data to history with cleanup"""
        try:
            self.price_history.append(price_data)
            
            # Cleanup old data
            cutoff_hours = self.settings['data_retention']['price_history_hours']
            cutoff_time = datetime.now() - timedelta(hours=cutoff_hours)
            self.price_history = [p for p in self.price_history if p.timestamp > cutoff_time]
            
        except Exception as e:
            logger.error(f"Price history update failed: {e}")

    def check_and_trigger_alerts(self, last_data: PriceData, current_data: PriceData) -> None:
        """Check for tick-to-tick alerts"""
        try:
            if last_data.price == 0:
                return
                
            # Calculate tick-to-tick change
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

            # Volume spike alert
            if (last_data.volume_24h and current_data.volume_24h and last_data.volume_24h > 0 and
                self.settings['alert_config']['volume_spike']['enabled']):

                volume_change_percent = ((current_data.volume_24h - last_data.volume_24h) / last_data.volume_24h) * 100

                if volume_change_percent >= self.settings['alert_config']['volume_spike']['threshold']:
                    self.trigger_alert("Volume Spike",
                        f"{current_data.symbol} 24h volume spiked {volume_change_percent:.0f}%")
                    
        except Exception as e:
            logger.error(f"Alert check failed: {e}")

    def trigger_alert(self, alert_type: str, message: str) -> None:
        """Trigger alert with notification"""
        try:
            timestamp = datetime.now()
            
            # Send notification
            if self.settings['enable_notifications']:
                success = self.notification_manager.send_notification(
                    f"CryptoPulse: {alert_type}", message)
                if not success:
                    logger.debug("Notification failed or on cooldown")
            
            # Add to history
            alert_record = {
                'type': alert_type,
                'message': message,
                'timestamp': timestamp
            }
            self.alerts_history.append(alert_record)
            
            # Update GUI
            self.safe_gui_call(lambda: self.add_alert_to_gui(alert_record))
            
            logger.info(f"Alert: {alert_type} - {message}")
            
        except Exception as e:
            logger.error(f"Alert trigger failed: {e}")

    def add_alert_to_gui(self, alert_record: dict) -> None:
        """Add alert to GUI list"""
        try:
            if not hasattr(self, 'alerts_listbox'):
                return
                
            timestamp_str = alert_record['timestamp'].strftime("%H:%M:%S")
            display_text = f"[{timestamp_str}] {alert_record['type']}: {alert_record['message']}"
            
            self.alerts_listbox.insert(0, display_text)
            
            # Limit alerts display
            max_alerts = self.settings['data_retention']['alert_history_count']
            if self.alerts_listbox.size() > max_alerts:
                self.alerts_listbox.delete(max_alerts, tk.END)
                
        except Exception as e:
            logger.error(f"Alert GUI update failed: {e}")

    def get_filtered_history(self) -> List[PriceData]:
        """Get history filtered by timeframe"""
        try:
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
            
        except Exception as e:
            logger.error(f"History filtering failed: {e}")
            return self.price_history

    def update_chart(self) -> None:
        """Update chart with error handling"""
        try:
            if not hasattr(self, 'ax') or not hasattr(self, 'canvas'):
                return
                
            filtered_history = self.get_filtered_history()
            
            if len(filtered_history) < 2:
                return
            
            # Clear and plot
            self.ax.clear()
            
            timestamps = [p.timestamp for p in filtered_history]
            prices = [p.price for p in filtered_history]
            
            # Main line
            self.ax.plot(timestamps, prices, color=self.colors['primary'], 
                        linewidth=2.5, alpha=0.9)
            
            # Points
            self.ax.scatter(timestamps, prices, color=self.colors['primary'], 
                           s=15, alpha=0.7, zorder=5)
            
            # Fill under curve
            self.ax.fill_between(timestamps, prices, alpha=0.1, color=self.colors['primary'])
            
            # Styling
            self.ax.set_facecolor(self.colors['card'])
            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['bottom'].set_color(self.colors['border'])
            self.ax.spines['left'].set_color(self.colors['border'])
            self.ax.tick_params(colors=self.colors['text_secondary'], labelsize=10)
            self.ax.grid(True, alpha=0.3, color=self.colors['chart_grid'])
            
            # Labels
            self.ax.set_ylabel('Price ($)', color=self.colors['text_primary'], fontsize=11)
            self.ax.set_title(f'Price Trend ({self.current_timeframe.value})', 
                            color=self.colors['text_primary'], fontsize=12)
            
            # Format x-axis
            if self.current_timeframe == TimeFrame.ONE_HOUR:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
            elif self.current_timeframe in [TimeFrame.SIX_HOURS, TimeFrame.TWENTY_FOUR_HOURS]:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                interval = 1 if self.current_timeframe == TimeFrame.SIX_HOURS else 4
                self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=interval))
            elif self.current_timeframe == TimeFrame.SEVEN_DAYS:
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            
            # Auto-scale
            self.ax.margins(x=0.02, y=0.05)
            
            # Refresh
            self.canvas.draw_idle()
            
        except Exception as e:
            logger.error(f"Chart update failed: {e}")

    def change_chart_timeframe(self, timeframe: TimeFrame) -> None:
        """Change chart timeframe"""
        try:
            self.current_timeframe = timeframe
            
            # Update button colors
            for tf, btn in self.timeframe_buttons.items():
                color = self.colors['primary'] if tf == timeframe else self.colors['secondary']
                btn.config(bg=color)
            
            # Update chart
            self.update_chart()
            logger.info(f"Timeframe changed to {timeframe.value}")
            
        except Exception as e:
            logger.error(f"Timeframe change failed: {e}")

    def update_connection_status(self, text: str, color: str) -> None:
        """Update connection status safely"""
        try:
            if hasattr(self, 'connection_label'):
                self.connection_label.config(text=text, foreground=color)
            if hasattr(self, 'status_text'):
                clean_text = text.replace("●", "").strip()
                self.status_text.config(text=clean_text)
        except Exception as e:
            logger.debug(f"Status update failed: {e}")

    def update_live_indicator(self) -> None:
        """Update live indicator with animation"""
        try:
            if not hasattr(self, 'live_indicator'):
                return
                
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
            
        except Exception as e:
            logger.debug(f"Live indicator update failed: {e}")

    def update_next_refresh_time(self, next_time: datetime) -> None:
        """Update next refresh time display"""
        try:
            if hasattr(self, 'next_update_label'):
                time_str = next_time.strftime("%H:%M:%S")
                self.next_update_label.config(text=f"Next update: {time_str}")
        except Exception as e:
            logger.debug(f"Refresh time update failed: {e}")

    def update_statistics(self) -> None:
        """Update 24H statistics"""
        try:
            if len(self.price_history) < 2:
                return
            
            # Get last 24 hours
            last_24h = datetime.now() - timedelta(hours=24)
            recent_prices = [p.price for p in self.price_history if p.timestamp > last_24h]
            
            if recent_prices and all(hasattr(self, attr) for attr in ['high_label', 'low_label', 'avg_label']):
                high_24h = max(recent_prices)
                low_24h = min(recent_prices)
                avg_24h = sum(recent_prices) / len(recent_prices)
                
                self.high_label.config(text=f"24H High: ${high_24h:,.2f}")
                self.low_label.config(text=f"24H Low: ${low_24h:,.2f}")
                self.avg_label.config(text=f"24H Average: ${avg_24h:,.2f}")
                
        except Exception as e:
            logger.debug(f"Statistics update failed: {e}")

    def run_test_notification(self, event=None):
        """Sends a test notification. The 'event' param allows binding."""
        logger.info("Running test notification.")
        self.notification_manager.notify(
            "CryptoPulse Test",
            "Notifications are working.",
            force=True,
            debounce_bypass=True
        )

    def run_manual_notification(self, event=None):
        """Sends a notification with the current price data."""
        if self.current_price_data:
            logger.info("Running manual price notification.")
            data = self.current_price_data
            crypto_name = self.get_crypto_display_name().split('/')[0]
            title = f"{crypto_name} Update"
            message = f"Price: ${data.price:,.2f}\n24h Change: {data.change_percent_24h:.2f}%"
            self.notification_manager.notify(
                title,
                message,
                force=True,
                debounce_bypass=True
            )
        else:
            logger.warning("Could not send manual notification, no price data available.")
            self.safe_show_warning("No Data", "Cannot send notification until price data is loaded.")

    # GUI Event Handlers
    def toggle_monitoring(self) -> None:
        """Toggle monitoring with safe UI updates"""
        try:
            self.is_monitoring = not self.is_monitoring
            
            if hasattr(self, 'monitor_btn'):
                if self.is_monitoring:
                    self.monitor_btn.config(text="Pause", bg=self.colors['primary'])
                    message = 'Monitoring resumed'
                else:
                    self.monitor_btn.config(text="Start", bg=self.colors['success'])
                    message = 'Monitoring paused'
                
                self.add_alert_to_gui({
                    'type': 'System', 'message': message, 'timestamp': datetime.now()
                })
                
            logger.info(f"Monitoring {'resumed' if self.is_monitoring else 'paused'}")
            
        except Exception as e:
            logger.error(f"Toggle monitoring failed: {e}")

    def manual_refresh(self) -> None:
        """Manual refresh with validation"""
        try:
            if not self.is_monitoring:
                self.safe_show_warning("Monitoring Paused", "Please resume monitoring first.")
                return
            
            if hasattr(self, 'status_text'):
                self.status_text.config(text="Manual refresh requested...")
                
            # Trigger refresh in background
            threading.Thread(target=self.fetch_and_update_price, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Manual refresh failed: {e}")

    def clear_history(self) -> None:
        """Clear history with confirmation"""
        try:
            if not self.safe_ask_yes_no("Clear History", 
                                      "Clear all price history and chart data?\n\nThis cannot be undone."):
                return
            
            self.price_history.clear()
            
            # Reset chart
            if hasattr(self, 'ax'):
                self.ax.clear()
                self.ax.set_facecolor(self.colors['card'])
                self.ax.set_ylabel('Price ($)', color=self.colors['text_primary'])
                self.ax.set_title(f'Price Trend ({self.current_timeframe.value})', 
                                color=self.colors['text_primary'])
                if hasattr(self, 'canvas'):
                    self.canvas.draw()
            
            # Reset statistics
            for attr in ['high_label', 'low_label', 'avg_label']:
                if hasattr(self, attr):
                    getattr(self, attr).config(text=f"{attr.split('_')[0].title()}: ---")
            
            self.add_alert_to_gui({
                'type': 'System', 'message': 'Price history cleared', 'timestamp': datetime.now()
            })
            
            logger.info("Price history cleared")
            
        except Exception as e:
            logger.error(f"Clear history failed: {e}")

    def clear_alerts(self) -> None:
        """Clear alerts history"""
        try:
            if hasattr(self, 'alerts_listbox'):
                self.alerts_listbox.delete(0, tk.END)
            self.alerts_history.clear()
            logger.info("Alerts cleared")
        except Exception as e:
            logger.error(f"Clear alerts failed: {e}")

    def export_data(self) -> None:
        """Export data with comprehensive error handling"""
        try:
            if not self.price_history:
                self.safe_show_warning("No Data", "No price history to export.")
                return
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Price Data",
                initialname=f"cryptopulse_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
                
                self.safe_show_info("Export Complete", f"Data exported successfully!\n\nFile: {filename}")
                logger.info(f"Data exported to {filename}")
                
        except Exception as e:
            self.safe_show_error("Export Failed", f"Failed to export data: {str(e)}")
            logger.error(f"Data export failed: {e}")

    def toggle_settings(self) -> None:
        """Toggle settings window"""
        try:
            if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
                self.settings_window.focus()
                return
            
            self.create_settings_window()
            
        except Exception as e:
            logger.error(f"Settings toggle failed: {e}")

    def create_settings_window(self) -> None:
        """Create settings window with error handling"""
        try:
            self.settings_window = tk.Toplevel(self.root)
            self.settings_window.title("CryptoPulse Settings")
            self.settings_window.geometry("600x800")
            self.settings_window.configure(bg=self.colors['background'])
            self.settings_window.resizable(False, False)
            self.settings_window.transient(self.root)
            self.settings_window.grab_set()
            
            # Center window
            self.settings_window.geometry("+{}+{}".format(
                self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 30))

            # Main content frame
            main_frame = ttk.Frame(self.settings_window)
            main_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Create notebook
            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Tabs
            general_frame = ttk.Frame(notebook)
            notifications_frame = ttk.Frame(notebook)
            alerts_frame = ttk.Frame(notebook)
            advanced_frame = ttk.Frame(notebook)
            diagnostics_frame = ttk.Frame(notebook)
            
            notebook.add(general_frame, text='General')
            notebook.add(notifications_frame, text='Notifications')
            notebook.add(alerts_frame, text='Alerts')
            notebook.add(advanced_frame, text='Advanced')
            notebook.add(diagnostics_frame, text='Diagnostics')
            
            # Create tab content
            self.create_general_settings(general_frame)
            self.create_notifications_settings(notifications_frame)
            self.create_alerts_settings(alerts_frame)
            self.create_advanced_settings(advanced_frame)
            self.create_diagnostics_panel(diagnostics_frame)

            # Action buttons frame
            buttons_frame = ttk.Frame(main_frame)
            buttons_frame.pack(fill='x', padx=20, pady=(10, 20))

            save_btn = self.create_button(buttons_frame, "Save & Close",
                                        self.colors['success'], self.save_settings_gui)
            save_btn.pack(side='left', padx=(0, 10))

            reset_btn = self.create_button(buttons_frame, "Reset",
                                         self.colors['warning'], self.reset_settings)
            reset_btn.pack(side='left', padx=(0, 10))

            cancel_btn = self.create_button(buttons_frame, "Cancel",
                                          self.colors['secondary'],
                                          lambda: self.settings_window.destroy())
            cancel_btn.pack(side='right')

            # Update diagnostics on open
            self.update_diagnostics_panel()
            
        except Exception as e:
            logger.error(f"Settings window creation failed: {e}")

    def create_general_settings(self, parent) -> None:
        """Create general settings with validation"""
        try:
            # Refresh interval
            interval_frame = ttk.LabelFrame(parent, text="Refresh Settings", padding=15)
            interval_frame.pack(fill='x', padx=20, pady=15)
            
            ttk.Label(interval_frame, text="Refresh Interval (seconds):").pack(anchor='w')
            self.interval_var = tk.StringVar(value=str(self.settings['refresh_interval']))
            interval_spin = tk.Spinbox(interval_frame, from_=10, to=300, increment=5,
                                      textvariable=self.interval_var, width=15)
            interval_spin.pack(anchor='w', pady=(5, 0))
            
            # Cryptocurrency
            crypto_frame = ttk.LabelFrame(parent, text="Cryptocurrency", padding=15)
            crypto_frame.pack(fill='x', padx=20, pady=15)
            
            ttk.Label(crypto_frame, text="Select Cryptocurrency:").pack(anchor='w')
            self.crypto_var = tk.StringVar(value=self.settings['cryptocurrency'])
            crypto_options = list(self.crypto_names.keys())
            crypto_combo = ttk.Combobox(crypto_frame, textvariable=self.crypto_var, 
                                       values=crypto_options, state='readonly', width=25)
            crypto_combo.pack(anchor='w', pady=(5, 0))
            
            # Currency
            currency_frame = ttk.LabelFrame(parent, text="Display Currency", padding=15)
            currency_frame.pack(fill='x', padx=20, pady=15)
            
            ttk.Label(currency_frame, text="Base Currency:").pack(anchor='w')
            self.currency_var = tk.StringVar(value=self.settings['vs_currency'])
            currency_combo = ttk.Combobox(currency_frame, textvariable=self.currency_var,
                                         values=['usd', 'eur', 'gbp', 'jpy', 'cad', 'aud'],
                                         state='readonly', width=15)
            currency_combo.pack(anchor='w', pady=(5, 0))
            
        except Exception as e:
            logger.error(f"General settings creation failed: {e}")

    def create_notifications_settings(self, parent) -> None:
        """Create notification settings tab"""
        try:
            # General Notification Settings
            notif_frame = ttk.LabelFrame(parent, text="General Notification Settings", padding=15)
            notif_frame.pack(fill='x', padx=20, pady=15)

            self.notifications_var = tk.BooleanVar(value=self.settings['enable_notifications'])
            notif_check = ttk.Checkbutton(notif_frame, text="Enable desktop notifications",
                                         variable=self.notifications_var)
            notif_check.pack(anchor='w')
            
            ttk.Label(notif_frame, text="Min notification interval (s):").pack(anchor='w', pady=(10,0))
            self.notif_interval_var = tk.StringVar(value=str(self.settings['min_notification_interval']))
            notif_interval_spin = tk.Spinbox(notif_frame, from_=1, to=300, increment=1,
                                             textvariable=self.notif_interval_var, width=15)
            notif_interval_spin.pack(anchor='w', pady=(5,0))

            test_btn = self.create_button(notif_frame, "Run Test", self.colors['accent'], self.run_test_notification)
            test_btn.pack(anchor='w', pady=(15,5))

            # Debug Settings
            debug_frame = ttk.LabelFrame(parent, text="Debug Options", padding=15)
            debug_frame.pack(fill='x', padx=20, pady=15)

            debug_settings = self.settings.get('debug', {})
            self.force_startup_test_var = tk.BooleanVar(value=debug_settings.get('force_startup_test', False))
            force_check = ttk.Checkbutton(debug_frame, text="Force startup test on next launch",
                                          variable=self.force_startup_test_var)
            force_check.pack(anchor='w')

            self.use_tk_fallback_var = tk.BooleanVar(value=debug_settings.get('use_tkinter_fallback_only', False))
            tk_fallback_check = ttk.Checkbutton(debug_frame, text="Use Tkinter fallback only (for testing)",
                                                variable=self.use_tk_fallback_var)
            tk_fallback_check.pack(anchor='w', pady=(5,0))

        except Exception as e:
            logger.error(f"Notifications settings creation failed: {e}")


    def create_alerts_settings(self, parent) -> None:
        """Create alerts settings"""
        try:
            # Price drop alerts
            drop_frame = ttk.LabelFrame(parent, text="Price Drop Alerts", padding=15)
            drop_frame.pack(fill='x', padx=20, pady=15)
            
            self.drop_enabled_var = tk.BooleanVar(
                value=self.settings['alert_config']['price_drop']['enabled'])
            drop_check = ttk.Checkbutton(drop_frame, text="Enable price drop alerts",
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
            rise_check = ttk.Checkbutton(rise_frame, text="Enable price rise alerts",
                                        variable=self.rise_enabled_var)
            rise_check.pack(anchor='w')
            
            ttk.Label(rise_frame, text="Rise threshold (%):").pack(anchor='w', pady=(10, 0))
            self.rise_threshold_var = tk.StringVar(
                value=str(self.settings['alert_config']['price_rise']['threshold']))
            rise_spin = tk.Spinbox(rise_frame, from_=0.1, to=50, increment=0.5,
                                  textvariable=self.rise_threshold_var, width=15)
            rise_spin.pack(anchor='w', pady=(5, 0))

            # Volume spike alerts
            volume_frame = ttk.LabelFrame(parent, text="Volume Spike Alerts", padding=15)
            volume_frame.pack(fill='x', padx=20, pady=15)

            self.volume_enabled_var = tk.BooleanVar(
                value=self.settings['alert_config']['volume_spike']['enabled'])
            volume_check = ttk.Checkbutton(volume_frame, text="Enable volume spike alerts",
                                          variable=self.volume_enabled_var)
            volume_check.pack(anchor='w')

            ttk.Label(volume_frame, text="Volume spike threshold (% increase):").pack(anchor='w', pady=(10, 0))
            self.volume_threshold_var = tk.StringVar(
                value=str(self.settings['alert_config']['volume_spike']['threshold']))
            volume_spin = tk.Spinbox(volume_frame, from_=50, to=5000, increment=50,
                                    textvariable=self.volume_threshold_var, width=15)
            volume_spin.pack(anchor='w', pady=(5, 0))

        except Exception as e:
            logger.error(f"Alerts settings creation failed: {e}")

    def create_advanced_settings(self, parent) -> None:
        """Create advanced settings"""
        try:
            # API Provider
            api_frame = ttk.LabelFrame(parent, text="API Provider", padding=15)
            api_frame.pack(fill='x', padx=20, pady=15)
            
            ttk.Label(api_frame, text="Primary API Provider:").pack(anchor='w')
            self.api_provider_var = tk.StringVar(value=self.settings['api_provider'])
            api_combo = ttk.Combobox(api_frame, textvariable=self.api_provider_var,
                                    values=['coingecko', 'binance', 'cryptocompare'],
                                    state='readonly', width=20)
            api_combo.pack(anchor='w', pady=(5, 0))
            
            # Data retention
            retention_frame = ttk.LabelFrame(parent, text="Data Retention", padding=15)
            retention_frame.pack(fill='x', padx=20, pady=15)
            
            ttk.Label(retention_frame, text="Price history (hours):").pack(anchor='w')
            self.retention_var = tk.StringVar(
                value=str(self.settings['data_retention']['price_history_hours']))
            retention_spin = tk.Spinbox(retention_frame, from_=24, to=720, increment=24,
                                       textvariable=self.retention_var, width=15)
            retention_spin.pack(anchor='w', pady=(5, 0))
            
            # UI Settings
            ui_frame = ttk.LabelFrame(parent, text="UI Settings", padding=15)
            ui_frame.pack(fill='x', padx=20, pady=15)
            
            self.auto_minimize_var = tk.BooleanVar(
                value=self.settings['ui_config']['auto_minimize'])
            minimize_check = ttk.Checkbutton(ui_frame, text="Auto-minimize to tray on startup",
                                            variable=self.auto_minimize_var)
            minimize_check.pack(anchor='w')
            
            if not self.tray_manager.available:
                minimize_check.config(state='disabled')
                ttk.Label(ui_frame, text="(System tray not available)", 
                         foreground='gray').pack(anchor='w', pady=(2, 0))
            
        except Exception as e:
            logger.error(f"Advanced settings creation failed: {e}")

    def create_diagnostics_panel(self, parent) -> None:
        """Create diagnostics panel"""
        try:
            diag_frame = ttk.LabelFrame(parent, text="Notification Diagnostics", padding=15)
            diag_frame.pack(fill='both', expand=True, padx=20, pady=15)

            self.diag_vars = {
                'total': tk.StringVar(value="Total Attempts: 0"),
                'success': tk.StringVar(value="Successful: 0"),
                'failed': tk.StringVar(value="Failed: 0"),
                'debounced': tk.StringVar(value="Debounced: 0"),
                'forced': tk.StringVar(value="Forced: 0"),
                'plyer': tk.StringVar(value="Via Plyer: 0"),
                'win10toast': tk.StringVar(value="Via win10toast: 0"),
                'tk': tk.StringVar(value="Via Tkinter: 0")
            }

            for key, var in self.diag_vars.items():
                ttk.Label(diag_frame, textvariable=var).pack(anchor='w')
            
            refresh_btn = self.create_button(diag_frame, "Refresh Stats", self.colors['primary'], self.update_diagnostics_panel)
            refresh_btn.pack(pady=(15,5))

        except Exception as e:
            logger.error(f"Diagnostics panel creation failed: {e}")

    def update_diagnostics_panel(self) -> None:
        """Update the diagnostics panel with current stats"""
        try:
            if not hasattr(self, 'diag_vars'):
                return
            
            stats = self.notification_manager.stats
            self.diag_vars['total'].set(f"Total Attempts: {stats['total_attempts']}")
            self.diag_vars['success'].set(f"Successful: {stats['success']}")
            self.diag_vars['failed'].set(f"Failed: {stats['failed']}")
            self.diag_vars['debounced'].set(f"Debounced: {stats['debounced']}")
            self.diag_vars['forced'].set(f"Forced: {stats['forced']}")
            self.diag_vars['plyer'].set(f"Via Plyer: {stats['by_backend']['plyer']}")
            self.diag_vars['win10toast'].set(f"Via win10toast: {stats['by_backend']['win10toast']}")
            self.diag_vars['tk'].set(f"Via Tkinter: {stats['by_backend']['tk']}")

        except Exception as e:
            logger.warning(f"Failed to update diagnostics panel: {e}")


    def save_settings_gui(self) -> None:
        """Save settings from GUI with validation"""
        try:
            # Validate inputs
            new_interval = max(10, int(self.interval_var.get()))
            new_notif_interval = max(1, int(self.notif_interval_var.get()))
            new_drop_threshold = max(0.1, float(self.drop_threshold_var.get()))
            new_rise_threshold = max(0.1, float(self.rise_threshold_var.get()))
            new_volume_threshold = max(1, float(self.volume_threshold_var.get()))
            new_retention = max(24, int(self.retention_var.get()))
            
            # Update settings
            old_crypto = self.settings['cryptocurrency']
            self.settings['refresh_interval'] = new_interval
            self.settings['cryptocurrency'] = self.crypto_var.get()
            self.settings['vs_currency'] = self.currency_var.get()
            self.settings['api_provider'] = self.api_provider_var.get()

            self.settings['enable_notifications'] = self.notifications_var.get()
            self.settings['min_notification_interval'] = new_notif_interval
            
            self.settings['alert_config']['price_drop']['enabled'] = self.drop_enabled_var.get()
            self.settings['alert_config']['price_drop']['threshold'] = new_drop_threshold
            self.settings['alert_config']['price_rise']['enabled'] = self.rise_enabled_var.get()
            self.settings['alert_config']['price_rise']['threshold'] = new_rise_threshold
            self.settings['alert_config']['volume_spike']['enabled'] = self.volume_enabled_var.get()
            self.settings['alert_config']['volume_spike']['threshold'] = new_volume_threshold
            
            self.settings['data_retention']['price_history_hours'] = new_retention
            self.settings['ui_config']['auto_minimize'] = self.auto_minimize_var.get()

            self.settings['debug']['force_startup_test'] = self.force_startup_test_var.get()
            self.settings['debug']['use_tkinter_fallback_only'] = self.use_tk_fallback_var.get()

            # Save to file
            self.save_settings()
            
            # Update UI if crypto changed
            if old_crypto != self.settings['cryptocurrency']:
                if hasattr(self, 'crypto_display_label'):
                    self.crypto_display_label.config(text=self.get_crypto_display_name())
                self.price_history.clear()
                self.is_first_check = True
            
            # Update provider label
            if hasattr(self, 'api_provider_label'):
                self.api_provider_label.config(
                    text=f"Provider: {self.settings['api_provider'].title()}")
            
            # Close window
            self.settings_window.destroy()
            
            # Success message
            self.safe_show_info("Settings Saved", "Settings saved successfully!")
            
            self.add_alert_to_gui({
                'type': 'System', 'message': 'Settings updated', 'timestamp': datetime.now()
            })
            
            logger.info("Settings saved successfully")
            
        except ValueError as e:
            self.safe_show_error("Invalid Input", f"Please check your input: {str(e)}")
        except Exception as e:
            self.safe_show_error("Settings Error", f"Failed to save settings: {str(e)}")
            logger.error(f"Settings save failed: {e}")

    def reset_settings(self) -> None:
        """Reset settings to defaults"""
        try:
            if not self.safe_ask_yes_no("Reset Settings", 
                                      "Reset all settings to defaults?\n\nThis will restore factory settings."):
                return
            
            # Reset to defaults
            self.settings = self.get_default_settings()
            self.save_settings()

            # Re-open the settings window to reflect the changes
            self.settings_window.destroy()
            self.toggle_settings()

            self.safe_show_info("Settings Reset", "Settings have been reset to default values.")
            logger.info("Settings reset to defaults")
            
        except Exception as e:
            logger.error(f"Settings reset failed: {e}")

    def show_about(self) -> None:
        """Show comprehensive about dialog"""
        try:
            about_window = tk.Toplevel(self.root)
            about_window.title("About CryptoPulse Monitor")
            about_window.geometry("550x500")
            about_window.configure(bg=self.colors['background'])
            about_window.resizable(False, False)
            about_window.transient(self.root)
            about_window.grab_set()
            
            # Center window
            about_window.geometry("+{}+{}".format(
                self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 50))
            
            # Content frame
            content_frame = ttk.Frame(about_window, style='Card.TFrame')
            content_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Title
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
            
            # Info
            info_frame = ttk.Frame(content_frame, style='Card.TFrame')
            info_frame.pack(fill='x', pady=(0, 20))
            
            info_text = f"""Version: 2.1.0
Author: Guillaume Lessard
Company: iD01t Productions
Website: https://id01t.store
Email: admin@id01t.store
Year: 2025
License: MIT License
Python: {sys.version.split()[0]}
Platform: {platform.system()} {platform.release()}"""
            
            info_label = ttk.Label(info_frame, text=info_text, style='Info.TLabel', justify='center')
            info_label.pack()
            
            # Features
            features_frame = ttk.LabelFrame(content_frame, text="Key Features", padding=15)
            features_frame.pack(fill='x', pady=(0, 20))
            
            features_text = """• Real-time cryptocurrency monitoring with smart API fallback
• Professional dark interface with modern responsive design
• Intelligent notification system with customizable thresholds
• Interactive charts with multiple timeframes (1H, 6H, 24H, 7D)
• System tray integration for minimal resource usage
• Multi-exchange support (CoinGecko, Binance, CryptoCompare)
• Persistent settings and automatic crash recovery
• Cross-platform compatibility (Windows, macOS, Linux)
• Professional data export and comprehensive statistics
• Bulletproof error handling and memory-efficient operation"""
            
            features_label = ttk.Label(features_frame, text=features_text,
                                      style='Info.TLabel', justify='left')
            features_label.pack(anchor='w')
            
            # Buttons
            buttons_frame = ttk.Frame(content_frame, style='Card.TFrame')
            buttons_frame.pack(fill='x', pady=10)
            
            website_btn = self.create_button(buttons_frame, "Visit Website",
                                           self.colors['accent'],
                                           lambda: webbrowser.open('https://id01t.store'))
            website_btn.pack(side='left', padx=(0, 10))
            
            close_btn = self.create_button(buttons_frame, "Close",
                                         self.colors['primary'], about_window.destroy)
            close_btn.pack(side='right')
            
        except Exception as e:
            logger.error(f"About dialog failed: {e}")

    # Safe GUI methods
    def safe_show_info(self, title: str, message: str) -> None:
        """Safely show info message"""
        try:
            messagebox.showinfo(title, message)
        except Exception as e:
            logger.error(f"Info message failed: {e}")

    def safe_show_warning(self, title: str, message: str) -> None:
        """Safely show warning message"""
        try:
            messagebox.showwarning(title, message)
        except Exception as e:
            logger.error(f"Warning message failed: {e}")

    def safe_show_error(self, title: str, message: str) -> None:
        """Safely show error message"""
        try:
            messagebox.showerror(title, message)
        except Exception as e:
            logger.error(f"Error message failed: {e}")

    def safe_ask_yes_no(self, title: str, message: str) -> bool:
        """Safely ask yes/no question"""
        try:
            return messagebox.askyesno(title, message)
        except Exception as e:
            logger.error(f"Yes/No dialog failed: {e}")
            return False

    # System tray methods
    def minimize_to_tray(self) -> None:
        """Minimize to tray with fallback"""
        try:
            if self.tray_manager.available:
                self.root.withdraw()
                if not self.tray_manager.running:
                    threading.Thread(target=self.tray_manager.run_tray, daemon=True).start()
            else:
                self.root.iconify()
        except Exception as e:
            logger.error(f"Minimize to tray failed: {e}")
            try:
                self.root.iconify()
            except:
                pass

    def show_window(self) -> None:
        """Show window from tray"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception as e:
            logger.error(f"Show window failed: {e}")

    # Window event handlers
    def on_closing(self) -> None:
        """Handle window closing"""
        try:
            if self.settings['ui_config']['auto_minimize'] and self.tray_manager.available:
                self.minimize_to_tray()
            else:
                if self.tray_manager.available:
                    choice = self.safe_ask_yes_no("Exit CryptoPulse", 
                        "Exit completely? Click No to minimize to tray.")
                    
                    if choice:
                        self.quit_application()
                    else:
                        self.minimize_to_tray()
                else:
                    if self.safe_ask_yes_no("Exit CryptoPulse", "Are you sure you want to exit?"):
                        self.quit_application()
        except Exception as e:
            logger.error(f"Window closing handler failed: {e}")
            self.quit_application()

    def on_window_configure(self, event) -> None:
        """Handle window configuration"""
        try:
            if event.widget == self.root and self.root.winfo_viewable():
                self.settings['ui_config']['window_x'] = self.root.winfo_x()
                self.settings['ui_config']['window_y'] = self.root.winfo_y()
                self.settings['ui_config']['window_width'] = self.root.winfo_width()
                self.settings['ui_config']['window_height'] = self.root.winfo_height()
        except Exception as e:
            logger.debug(f"Window configure failed: {e}")

    def quit_application(self) -> None:
        """Quit application with cleanup"""
        try:
            logger.info("Shutting down CryptoPulse Monitor...")
            
            # Set shutdown flag
            self.shutdown_requested = True
            
            # Stop monitoring
            self.is_monitoring = False
            
            # Save settings
            self.save_settings()
            
            # Stop tray
            if self.tray_manager:
                self.tray_manager.stop_tray()
            
            # Close settings window
            try:
                if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
                    self.settings_window.destroy()
            except:
                pass
            
            # Quit GUI
            try:
                if hasattr(self, 'root'):
                    self.root.quit()
                    self.root.destroy()
            except:
                pass
            
            logger.info("Application shutdown complete")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")

    def run(self) -> bool:
        """Run application with comprehensive error handling"""
        try:
            logger.info("Starting CryptoPulse Monitor v2.1.0...")
            
            # Setup GUI
            if not self.setup_gui():
                logger.critical("GUI setup failed")
                return False
            
            # Start monitoring
            self.start_monitoring()
            
            # Initial fetch
            threading.Thread(target=self.fetch_and_update_price, daemon=True).start()
            
            # Auto-minimize if configured
            if (self.settings['ui_config']['auto_minimize'] and 
                self.tray_manager.available):
                self.root.after(2000, self.minimize_to_tray)

            # Perform startup self-check after a short delay
            self.root.after(1500, self.perform_startup_self_check)
            
            logger.info("CryptoPulse Monitor started successfully")
            
            # Start main loop
            self.root.mainloop()
            return True
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            return True
        except Exception as e:
            logger.critical(f"Critical runtime error: {e}")
            logger.critical(traceback.format_exc())
            return False
        finally:
            self.quit_application()


# Utility functions for scaffolding
def create_requirements_file():
    """Create requirements.txt file"""
    requirements_content = """# CryptoPulse Monitor v2.1.0 Requirements
# Professional Cryptocurrency Tracking Application
# Author: Guillaume Lessard / iD01t Productions
# Website: https://id01t.store

requests>=2.25.0
matplotlib>=3.5.0
Pillow>=8.0.0
plyer>=2.1.0
pystray>=0.19.0

# Optional for building executables
# pyinstaller>=4.0
# cx_Freeze>=6.0
"""
    
    try:
        with open('requirements.txt', 'w') as f:
            f.write(requirements_content)
        print("✓ requirements.txt created successfully")
        return True
    except Exception as e:
        print(f"Warning: Could not create requirements.txt: {e}")
        return False


def create_launcher_scripts():
    """Create platform-specific launcher scripts"""
    # Windows launcher
    windows_launcher = """@echo off
title CryptoPulse Monitor v2.1.0
echo ========================================
echo   CryptoPulse Monitor v2.1.0
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
    
    # Unix launcher
    unix_launcher = """#!/bin/bash
echo "========================================"
echo "  CryptoPulse Monitor v2.1.0"
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
        try:
            import stat
            os.chmod('start_cryptopulse.sh', stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        except:
            pass
            
        print("✓ Launcher scripts created successfully")
        return True
    except Exception as e:
        print(f"Warning: Could not create launcher scripts: {e}")
        return False


def create_build_script():
    """Create build script for executables"""
    build_script = '''#!/usr/bin/env python3
"""
Build script for CryptoPulse Monitor v2.1.0
Creates standalone executables for distribution

Author: Guillaume Lessard / iD01t Productions
Website: https://id01t.store
"""

import os
import sys
import subprocess
from pathlib import Path

def build_with_pyinstaller():
    """Build using PyInstaller"""
    try:
        print("Building with PyInstaller...")
        
        cmd = [
            'pyinstaller',
            '--onefile',
            '--windowed', 
            '--name', 'CryptoPulse_Monitor',
            '--hidden-import', 'plyer.platforms.win.notification',
            '--hidden-import', 'pystray._win32',
            '--exclude-module', 'pytest',
            '--exclude-module', 'unittest',
            'cryptopulse_monitor.py'
        ]
        
        subprocess.run(cmd, check=True)
        print("Build successful! Check dist/ folder")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False
    except FileNotFoundError:
        print("PyInstaller not found. Install with: pip install pyinstaller")
        return False

def main():
    print("=" * 50)
    print("CryptoPulse Monitor v2.1.0 Build Script")
    print("Guillaume Lessard / iD01t Productions")
    print("=" * 50)
    
    if not Path('cryptopulse_monitor.py').exists():
        print("Error: cryptopulse_monitor.py not found")
        sys.exit(1)
    
    if build_with_pyinstaller():
        print("\\nBuild completed successfully!")
    else:
        print("\\nBuild failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    try:
        with open('build.py', 'w') as f:
            f.write(build_script)
        
        try:
            import stat
            os.chmod('build.py', stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        except:
            pass
            
        print("✓ Build script created successfully")
        return True
    except Exception as e:
        print(f"Warning: Could not create build script: {e}")
        return False


def create_readme():
    """Create comprehensive README"""
    readme_content = """# CryptoPulse Monitor v2.1.0

Professional cryptocurrency price tracking application with real-time monitoring, intelligent alerts, and comprehensive data visualization.

## Author & Company

**Guillaume Lessard**  
**iD01t Productions**  
📧 admin@id01t.store  
🌐 https://id01t.store  
📅 2025

## Features

### Core Functionality
- Real-time price monitoring with configurable refresh intervals
- Multi-exchange API support (CoinGecko, Binance, CryptoCompare) 
- Smart notification system with tick-to-tick alert thresholds
- Interactive price charts with multiple timeframes (1H, 6H, 24H, 7D)
- Data persistence and automatic crash recovery
- CSV export functionality for data analysis

### User Interface  
- Professional dark theme with modern design
- System tray integration for minimal resource usage
- Comprehensive settings with tabbed interface
- Cross-platform compatibility (Windows, macOS, Linux)
- Customizable alerts and monitoring preferences

### Technical Features
- Bulletproof error handling with automatic API fallback
- Intelligent provider rotation for maximum uptime
- Memory-efficient data management with automatic cleanup
- Professional logging system for debugging and monitoring
- Optimized performance with responsive UI

## Installation

### Prerequisites
- Python 3.8 or higher
- Internet connection for API access

### Quick Start
1. Clone or download the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python cryptopulse_monitor.py
   ```

### Alternative Launchers
- **Windows:** Double-click `start_cryptopulse.bat`
- **Unix/Linux/macOS:** Run `./start_cryptopulse.sh`

## Usage

### Basic Operation
1. Launch the application
2. Select your preferred cryptocurrency from settings
3. Configure alert thresholds and notification preferences  
4. Monitor real-time price changes and trends
5. Export data for further analysis when needed

### Settings Configuration
- **General:** Refresh intervals, cryptocurrency selection, display currency
- **Alerts:** Enable/disable notifications, set price change thresholds
- **Advanced:** API provider preferences, data retention settings

## Supported Cryptocurrencies

- Bitcoin (BTC)
- Ethereum (ETH)
- Cardano (ADA)
- Solana (SOL)
- Litecoin (LTC)
- Ripple (XRP)
- Polkadot (DOT)
- Chainlink (LINK)

## Building Executables

### Using PyInstaller
```bash
# Install PyInstaller
pip install pyinstaller

# Run build script  
python build.py
```

## Configuration Files

### Settings Location
- **Windows:** `%USERPROFILE%\\.cryptopulse\\settings.json`
- **macOS:** `~/.cryptopulse/settings.json`
- **Linux:** `~/.cryptopulse/settings.json`

### Log Files
- **Location:** Same as settings directory
- **File:** `cryptopulse.log`
- **Rotation:** Automatic cleanup of old entries

## Troubleshooting

### Common Issues

**"Dependencies missing" error:**
```bash
pip install --upgrade -r requirements.txt
```

**"API connection failed" error:**
- Check internet connection
- Verify API provider status
- Try switching primary API provider in settings

**"System tray not available" warning:**
- Install system-specific tray dependencies
- Use regular window minimize instead

**Performance issues:**
- Increase refresh interval in settings
- Clear price history data
- Reduce data retention period

## License

MIT License

Copyright (c) 2025 Guillaume Lessard / iD01t Productions

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Support

For support, feature requests, or bug reports:

- 📧 Email: admin@id01t.store
- 🌐 Website: https://id01t.store

## Changelog

### v2.1.0 (2025)
- Enhanced professional UI with modern design
- Fixed CoinGecko 24h change calculation
- Improved CPU efficiency during pause mode
- Smart API provider selection and fallback
- Tick-to-tick alert system for real-time notifications
- Multiple chart timeframes with filtering
- Enhanced settings management and validation
- Bulletproof error handling and recovery
- Comprehensive logging and monitoring
- Updated branding and contact information

---

**CryptoPulse Monitor v2.1.0** - Professional cryptocurrency tracking made simple.

*Created by Guillaume Lessard / iD01t Productions*
"""
    
    try:
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print("✓ README.md created successfully")
        return True
    except Exception as e:
        print(f"Warning: Could not create README.md: {e}")
        return False


def main():
    """Main entry point with professional startup"""
    print("=" * 70)
    print("🚀 CRYPTOPULSE MONITOR v2.1.0")
    print("   Professional Cryptocurrency Tracking Application")
    print("   Author: Guillaume Lessard / iD01t Productions")
    print("   Website: https://id01t.store")
    print("   Email: admin@id01t.store")
    print("=" * 70)
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='CryptoPulse Monitor v2.1.0')
    parser.add_argument('--scaffold', action='store_true', 
                       help='Create project files (requirements.txt, launchers, etc.)')
    parser.add_argument('--build', action='store_true',
                       help='Create build script for executable generation')
    parser.add_argument('--version', action='version', version='CryptoPulse Monitor v2.1.0')
    
    args = parser.parse_args()
    
    # Create scaffolding if requested
    if args.scaffold:
        print("📝 Creating project scaffolding files...")
        
        success_count = 0
        total_count = 3
        
        if create_requirements_file():
            success_count += 1
        if create_launcher_scripts():
            success_count += 1
        if create_readme():
            success_count += 1
            
        if args.build:
            total_count += 1
            if create_build_script():
                success_count += 1
        
        print(f"✓ Scaffolding complete! ({success_count}/{total_count} files created)")
        return
    
    # Run application
    try:
        print("🔧 Initializing application...")
        app = CryptoPulseMonitor()
        
        print("📊 Starting price monitoring...")
        success = app.run()
        
        if success:
            print("✓ Application closed normally")
        else:
            print("⚠ Application exited with errors")
            
    except KeyboardInterrupt:
        print("\n👋 Application terminated by user")
    except Exception as e:
        logger.critical(f"Critical startup error: {e}")
        logger.critical(traceback.format_exc())
        print(f"⚠ Critical error: {e}")
        print("Check log file: ~/.cryptopulse/cryptopulse.log")
        input("Press Enter to exit...")
    finally:
        print("✓ Shutdown complete")


if __name__ == "__main__":
    main()
