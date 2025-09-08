import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import json
from datetime import datetime, timedelta

# Set an environment variable to prevent dependency installation during tests
os.environ['CRYPTOPULSE_TESTING'] = '1'

# Mock GUI and other problematic libraries before importing the application
mock_tkinter = MagicMock()
mock_tkinter.filedialog = MagicMock()
mock_tkinter.simpledialog = MagicMock()
mock_tkinter.ttk = MagicMock()
mock_tkinter.font = MagicMock()
mock_tkinter.messagebox = MagicMock()
sys.modules['tkinter'] = mock_tkinter
sys.modules['tkinter.ttk'] = mock_tkinter.ttk
sys.modules['tkinter.font'] = mock_tkinter.font
sys.modules['tkinter.filedialog'] = mock_tkinter.filedialog
sys.modules['tkinter.messagebox'] = mock_tkinter.messagebox
sys.modules['tkinter.simpledialog'] = mock_tkinter.simpledialog

sys.modules['pystray'] = MagicMock()
sys.modules['plyer'] = MagicMock()
sys.modules['win10toast'] = MagicMock()

# Mock matplotlib
mock_matplotlib = MagicMock()
mock_matplotlib.pyplot = MagicMock()
mock_matplotlib.figure = MagicMock()
mock_matplotlib.dates = MagicMock()
mock_matplotlib.backends = MagicMock()
mock_matplotlib.backends.backend_tkagg = MagicMock()
sys.modules['matplotlib'] = mock_matplotlib
sys.modules['matplotlib.pyplot'] = mock_matplotlib.pyplot
sys.modules['matplotlib.figure'] = mock_matplotlib.figure
sys.modules['matplotlib.dates'] = mock_matplotlib.dates
sys.modules['matplotlib.backends'] = mock_matplotlib.backends
sys.modules['matplotlib.backends.backend_tkagg'] = mock_matplotlib.backends.backend_tkagg

# Mock PIL
mock_pil = MagicMock()
mock_pil.Image = MagicMock()
mock_pil.ImageTk = MagicMock()
mock_pil.ImageDraw = MagicMock()
mock_pil.ImageFont = MagicMock()
sys.modules['PIL'] = mock_pil
sys.modules['PIL.Image'] = mock_pil.Image
sys.modules['PIL.ImageTk'] = mock_pil.ImageTk
sys.modules['PIL.ImageDraw'] = mock_pil.ImageDraw
sys.modules['PIL.ImageFont'] = mock_pil.ImageFont

# Add the application's directory to the path to allow imports
# Assuming the test file is in the same directory as the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cryptopulse_monitor import CryptoPulseMonitor, ProviderManager, APIProvider, NotificationManager, PriceData

class TestProviderManager(unittest.TestCase):

    def setUp(self):
        self.logger = Mock()
        self.providers = [APIProvider.COINGECKO, APIProvider.BINANCE, APIProvider.CRYPTOCOMPARE]
        self.primary_provider = APIProvider.COINGECKO
        self.manager = ProviderManager(self.logger, self.providers, primary_provider=self.primary_provider)

    def test_get_ordered_providers_primary_first(self):
        """Test that the primary provider is returned first."""
        ordered_providers = self.manager.get_ordered_providers()
        self.assertEqual(ordered_providers[0], self.primary_provider)
        self.assertIn(APIProvider.BINANCE, ordered_providers)
        self.assertIn(APIProvider.CRYPTOCOMPARE, ordered_providers)

    def test_blacklist_provider(self):
        """Test that a provider can be blacklisted and is not returned."""
        self.manager.blacklist_provider(APIProvider.BINANCE, duration_seconds=60)
        ordered_providers = self.manager.get_ordered_providers()
        self.assertNotIn(APIProvider.BINANCE, ordered_providers)
        self.assertIn(APIProvider.COINGECKO, ordered_providers)

    def test_blacklist_expiry(self):
        """Test that a blacklisted provider is available again after the TTL expires."""
        with patch('cryptopulse_monitor.datetime') as mock_datetime:
            now = datetime(2025, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = now

            self.manager.blacklist_provider(APIProvider.BINANCE, duration_seconds=60)

            # Move time forward to after expiry
            mock_datetime.now.return_value = now + timedelta(seconds=61)

            ordered_providers = self.manager.get_ordered_providers()
            self.assertIn(APIProvider.BINANCE, ordered_providers)

    def test_report_failure_and_blacklist(self):
        """Test that enough failures lead to blacklisting."""
        provider_to_fail = APIProvider.BINANCE
        for _ in range(self.manager.max_failures):
            self.manager.report_failure(provider_to_fail)

        self.assertIn(provider_to_fail, self.manager.blacklist)
        ordered_providers = self.manager.get_ordered_providers()
        self.assertNotIn(provider_to_fail, ordered_providers)

    def test_report_success_resets_failures(self):
        """Test that reporting success resets the failure count."""
        provider = APIProvider.BINANCE
        self.manager.report_failure(provider)
        self.assertEqual(self.manager.failure_counts[provider], 1)
        self.manager.report_success(provider)
        self.assertEqual(self.manager.failure_counts[provider], 0)

class TestNotificationManager(unittest.TestCase):
    def setUp(self):
        self.logger = Mock()
        self.root = MagicMock()
        # Mock the `after` method to call the function immediately for synchronous testing
        self.root.after = lambda delay, func, *args, **kwargs: func(*args, **kwargs)

        self.manager = NotificationManager(self.logger, root=self.root, debounce_seconds=0)
        # We need to re-patch the notification object within the cryptopulse_monitor module's namespace
        self.plyer_patcher = patch('cryptopulse_monitor.notification', MagicMock())
        self.messagebox_patcher = patch('cryptopulse_monitor.messagebox', MagicMock())

        self.mock_plyer_notification = self.plyer_patcher.start()
        self.mock_messagebox = self.messagebox_patcher.start()

    def tearDown(self):
        self.plyer_patcher.stop()
        self.messagebox_patcher.stop()

    def test_notify_plyer_success(self):
        """Test that plyer is called first and successfully."""
        with patch.object(self.manager, 'win10toast', None):
            with patch('cryptopulse_monitor.NOTIFICATIONS_AVAILABLE', True):
                self.manager.notify("title", "message")
                import time
                time.sleep(0.1)
                self.mock_plyer_notification.notify.assert_called_once()
                self.mock_messagebox.showinfo.assert_not_called()

    @patch('cryptopulse_monitor.os.name', 'nt')
    def test_notify_plyer_fails_win10toast_succeeds(self, mock_os_name):
        """Test fallback to win10toast when plyer fails on Windows."""
        self.mock_plyer_notification.notify.side_effect = Exception("Plyer error")

        mock_toast = MagicMock()
        with patch.object(self.manager, 'win10toast', mock_toast):
            with patch('cryptopulse_monitor.NOTIFICATIONS_AVAILABLE', True):
                self.manager.notify("title", "message")
                import time
                time.sleep(0.1)
                self.mock_plyer_notification.notify.assert_called_once()
                mock_toast.show_toast.assert_called_once()
                self.mock_messagebox.showinfo.assert_not_called()

    @patch('cryptopulse_monitor.os.name', 'posix') # Non-windows
    def test_notify_fallback_to_tkinter(self, mock_os_name):
        """Test fallback to Tkinter when other backends fail."""
        self.mock_plyer_notification.notify.side_effect = Exception("Plyer error")
        with patch.object(self.manager, 'win10toast', None):
            with patch('cryptopulse_monitor.NOTIFICATIONS_AVAILABLE', True):
                self.manager.notify("title", "message")
                import time
                time.sleep(0.1)
                self.mock_plyer_notification.notify.assert_called_once()
                self.mock_messagebox.showinfo.assert_called_once()

@patch('threading.Thread')
@patch('cryptopulse_monitor.CryptoPulseMonitor.setup_gui', Mock())
@patch('cryptopulse_monitor.CryptoPulseMonitor.setup_system_tray', Mock())
@patch('cryptopulse_monitor.CryptoPulseMonitor.start_monitoring', Mock())
@patch('cryptopulse_monitor.CryptoPulseMonitor.check_stale_data', Mock())
class TestCryptoPulseMonitor(unittest.TestCase):
    def setUp(self, mock_thread):
        with patch('cryptopulse_monitor.setup_logging'):
            self.app = CryptoPulseMonitor()
            self.app.root = MagicMock()

    def test_fetch_and_update_price_success(self, mock_thread):
        """Test the main fetch loop on a successful API call."""
        mock_provider = APIProvider.COINGECKO
        mock_price_data = PriceData(symbol='BTC', price=50000, change_24h=200, change_percent_24h=0.4, timestamp=datetime.now(), volume_24h=1000, market_cap=1000000)

        self.app.provider_manager.get_ordered_providers = Mock(return_value=[mock_provider])
        self.app.fetch_price_from_provider = Mock(return_value=mock_price_data)
        self.app.safe_after = lambda delay, func, *args, **kwargs: func(*args, **kwargs)
        self.app.update_price_display = Mock()
        self.app.hide_error_banner = Mock()
        self.app.api_provider_label = MagicMock()
        self.app.update_connection_status = Mock()


        self.app.fetch_and_update_price()

        self.app.provider_manager.get_ordered_providers.assert_called_once()
        self.app.fetch_price_from_provider.assert_called_with(mock_provider)
        self.app.update_price_display.assert_called_once()
        self.app.hide_error_banner.assert_called_once()
        self.assertIsNotNone(self.app.last_successful_update_time)

    def test_fetch_and_update_price_all_fail(self, mock_thread):
        """Test the main fetch loop when all providers fail."""
        mock_providers = [APIProvider.COINGECKO, APIProvider.BINANCE]
        self.app.provider_manager.get_ordered_providers = Mock(return_value=mock_providers)
        self.app.fetch_price_from_provider = Mock(return_value=None)
        self.app.safe_after = lambda delay, func, *args, **kwargs: func(*args, **kwargs)
        self.app.show_error_banner = Mock()
        self.app.provider_manager.report_failure = Mock()
        self.app.update_connection_status = Mock()

        with self.assertRaises(Exception):
            self.app.fetch_and_update_price()

        self.assertEqual(self.app.fetch_price_from_provider.call_count, 2)
        self.assertEqual(self.app.provider_manager.report_failure.call_count, 2)
        self.app.show_error_banner.assert_called_once()

    @patch('pathlib.Path.exists', return_value=True)
    @patch('builtins.open')
    def test_settings_migration(self, mock_open, mock_exists, mock_thread):
        """Test that old settings are migrated correctly."""
        old_settings = {'cryptocurrency': 'ethereum', 'schema_version': 0}
        mock_open.return_value = unittest.mock.mock_open(read_data=json.dumps(old_settings)).return_value

        with patch('cryptopulse_monitor.setup_logging'):
            with patch('cryptopulse_monitor.CryptoPulseMonitor.setup_gui'), \
                 patch('cryptopulse_monitor.CryptoPulseMonitor.setup_system_tray'), \
                 patch('cryptopulse_monitor.CryptoPulseMonitor.start_monitoring'), \
                 patch('cryptopulse_monitor.CryptoPulseMonitor.check_stale_data'):
                app = CryptoPulseMonitor()
                app.root = MagicMock()

        self.assertEqual(app.settings['cryptocurrency'], 'ethereum')
        self.assertEqual(app.settings['schema_version'], app.SCHEMA_VERSION)

    @patch('cryptopulse_monitor.filedialog.asksaveasfilename')
    def test_csv_export(self, mock_asksaveasfilename, mock_thread):
        """Test exporting data to CSV."""
        mock_file = unittest.mock.mock_open()
        mock_asksaveasfilename.return_value = 'test_export.csv'

        self.app.price_history = [
            PriceData(symbol='BTC', price=50000, change_24h=200, change_percent_24h=0.4, timestamp=datetime.now(), volume_24h=1000, market_cap=1000000)
        ]

        with patch('builtins.open', mock_file):
            self.app.export_data()

        mock_asksaveasfilename.assert_called_once()
        mock_file.assert_called_once_with('test_export.csv', 'w', newline='', encoding='utf-8')
        self.assertEqual(mock_file().write.call_count, 2)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
