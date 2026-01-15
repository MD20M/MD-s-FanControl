import dbus
import os
import subprocess
import json

class Notifier:
    """Simple notification wrapper for org.freedesktop.Notifications"""
    
    def __init__(self, app_name="SystemMonitor", silent=False):
        """
        Initialize the notifier.
        
        Args:
            app_name: Name of your application (shown in notifications)
            silent: If True, suppress connection error messages
        """
        self.app_name = app_name
        self.interface = None
        self.silent = silent
        self.original_user = self._get_original_user()
        self.original_uid = self._get_original_uid()
        self.use_fallback = False
        self._connect()
    
    def _get_original_user(self):
        """Get the original user who ran sudo"""
        if 'SUDO_USER' in os.environ:
            return os.environ['SUDO_USER']
        
        if os.geteuid() != 0:
            return os.environ.get('USER')
        
        return None
    
    def _get_original_uid(self):
        """Get the original user's UID"""
        if 'SUDO_UID' in os.environ:
            return int(os.environ['SUDO_UID'])
        
        if os.geteuid() != 0:
            return os.getuid()
        
        if self.original_user:
            try:
                import pwd
                return pwd.getpwnam(self.original_user).pw_uid
            except:
                pass
        
        return None
    
    def _find_dbus_address_for_user(self, uid):
        """Find D-Bus session address for a specific user"""
        # Try common socket locations
        common_paths = [
            f'/run/user/{uid}/bus',
            f'/var/run/user/{uid}/bus',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return f'unix:path={path}'
        
        # Try to find from user's processes
        try:
            result = subprocess.run(
                ['pgrep', '-u', str(uid), '-x', 'dbus-daemon'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    env_file = f'/proc/{pid}/environ'
                    if os.path.exists(env_file):
                        try:
                            with open(env_file, 'rb') as f:
                                env_data = f.read().decode('utf-8', errors='ignore')
                                for item in env_data.split('\0'):
                                    if item.startswith('DBUS_SESSION_BUS_ADDRESS='):
                                        return item.split('=', 1)[1]
                        except (IOError, PermissionError):
                            continue
        except (subprocess.TimeoutExpired, Exception):
            pass
        
        return None
    
    def _find_dbus_address(self):
        """Try to find D-Bus session address"""
        # If running as sudo, look for the original user's D-Bus
        if os.geteuid() == 0 and self.original_uid:
            address = self._find_dbus_address_for_user(self.original_uid)
            if address:
                return address
        
        # Check if already set in environment
        if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
            return os.environ['DBUS_SESSION_BUS_ADDRESS']
        
        # Try to find for current user
        address = self._find_dbus_address_for_user(os.getuid())
        if address:
            return address
        
        return None
    
    def _connect(self):
        """Connect to D-Bus notification service"""
        address = self._find_dbus_address()
        
        if not address:
            if os.geteuid() == 0 and self.original_user:
                # Running as root, enable fallback mode
                self.use_fallback = True
                if not self.silent:
                    print(f"[Notifier] Using fallback mode for user {self.original_user}")
                return
            elif not self.silent:
                print("[Notifier] Could not find D-Bus session address")
            return
        
        # Set the address in environment
        os.environ['DBUS_SESSION_BUS_ADDRESS'] = address
        
        try:
            bus = dbus.SessionBus()
            notify_obj = bus.get_object(
                'org.freedesktop.Notifications',
                '/org/freedesktop/Notifications'
            )
            self.interface = dbus.Interface(notify_obj, 'org.freedesktop.Notifications')
            
            if not self.silent and os.geteuid() == 0:
                print(f"[Notifier] ✓ Connected to {self.original_user}'s notification service")
        except dbus.DBusException as e:
            if os.geteuid() == 0 and self.original_user:
                # Connection failed, use fallback
                self.use_fallback = True
                if not self.silent:
                    print(f"[Notifier] D-Bus connection failed, using fallback mode")
            elif not self.silent:
                print(f"[Notifier] Failed to connect to D-Bus: {e}")
            self.interface = None
    
    def _send_via_fallback(self, title, message, urgency, timeout, icon):
        """Send notification via notify-send as the original user"""
        if not self.original_user:
            return None
        
        try:
            # Build notify-send command
            cmd = ['su', self.original_user, '-c']
            
            # Get the user's DBUS address
            dbus_addr = self._find_dbus_address_for_user(self.original_uid)
            
            notify_cmd = []
            if dbus_addr:
                notify_cmd.append(f'DBUS_SESSION_BUS_ADDRESS="{dbus_addr}"')
            
            notify_cmd.append('notify-send')
            notify_cmd.append(f'--app-name={self.app_name}')
            
            # Set urgency
            urgency_str = {0: 'low', 1: 'normal', 2: 'critical'}.get(urgency, 'normal')
            notify_cmd.append(f'--urgency={urgency_str}')
            
            # Set timeout (convert from ms to seconds for notify-send)
            if timeout > 0:
                notify_cmd.append(f'--expire-time={timeout}')
            
            # Set icon
            if icon:
                notify_cmd.append(f'--icon={icon}')
            
            notify_cmd.append(f'"{title}"')
            notify_cmd.append(f'"{message}"')
            
            cmd.append(' '.join(notify_cmd))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5
            )
            
            return 1 if result.returncode == 0 else None
        except Exception as e:
            if not self.silent:
                print(f"[Notifier] Fallback send failed: {e}")
            return None
    
    def is_available(self):
        """Check if notifications are available"""
        return self.interface is not None or self.use_fallback
    
    def send(self, title, message, critical=False, timeout=5000, icon=None):
        """
        Send a notification.
        
        Args:
            title: Notification title
            message: Notification message
            critical: If True, send as critical (urgent) notification
            timeout: How long to show (milliseconds), -1 for default, 0 for persistent
            icon: Icon name or path (e.g., "dialog-warning", "dialog-error")
        
        Returns:
            Notification ID if successful, None if failed
        """
        urgency = 2 if critical else 1
        
        if icon is None:
            icon = "dialog-error" if critical else "dialog-information"
        
        # Try D-Bus first
        if self.interface:
            try:
                notification_id = self.interface.Notify(
                    self.app_name,
                    0,
                    icon,
                    title,
                    message,
                    [],
                    {'urgency': dbus.Byte(urgency)},
                    timeout
                )
                return notification_id
            except Exception:
                # D-Bus failed, try fallback if available
                if self.use_fallback:
                    return self._send_via_fallback(title, message, urgency, timeout, icon)
                return None
        
        # Use fallback if D-Bus not available
        if self.use_fallback:
            return self._send_via_fallback(title, message, urgency, timeout, icon)
        
        return None
    
    def send_info(self, title, message, timeout=5000):
        """Send an informational notification"""
        return self.send(title, message, critical=False, timeout=timeout, icon="dialog-information")
    
    def send_warning(self, title, message, timeout=8000):
        """Send a warning notification"""
        return self.send(title, message, critical=False, timeout=timeout, icon="dialog-warning")
    
    def send_error(self, title, message, timeout=10000):
        """Send an error notification"""
        return self.send(title, message, critical=True, timeout=timeout, icon="dialog-error")
    
    def send_critical(self, title, message, timeout=0):
        """Send a critical notification (persistent)"""
        return self.send("⚠️ "+title, message, critical=True, timeout=timeout, icon="dialog-error")
    
    def close(self, notification_id):
        """
        Close a notification by ID.
        
        Args:
            notification_id: ID returned from send()
        
        Returns:
            True if successful, False otherwise
        """
        if not self.interface or notification_id is None:
            return False
        
        try:
            self.interface.CloseNotification(notification_id)
            return True
        except Exception:
            return False


if __name__ == "__main__":
    # Test with verbose output
    notifier = Notifier("TestApp", silent=False)
    
    if not notifier.is_available():
        print("\n❌ Notifications not available!")
        print("Troubleshooting:")
        if os.geteuid() == 0:
            print(f"  - Running as root, trying to connect to user '{notifier.original_user}'")
            print(f"  - Make sure user {notifier.original_user} has an active desktop session")
            print("  - Try running without sudo if notifications aren't critical")
        else:
            print("  - Make sure you're in a desktop session")
            print("  - Check if notification daemon is running:")
            print("    ps aux | grep -E 'dunst|mako|notification|gsd-print-notifications'")
    else:
        print("\n✓ Notifications available!")
        
        # Send test notifications
        print("\nSending test notifications...")
        notifier.send_info("Info", "This is an info message")
        notifier.send_warning("Warning", "This is a warning")
        notifier.send_error("Error", "This is an error")
