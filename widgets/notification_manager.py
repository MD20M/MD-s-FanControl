from textual.app import ComposeResult
from textual.widgets import Input, Select, Button, ListView, ListItem, Label
from textual.containers import Vertical, Horizontal
from utils import Notifier
import json
import os


class NotificationManager(Vertical, Notifier):
    """
    A manager for system notifications based on component stats.
    Allows users to create, view, save, and delete notifications.
    Notifications can be triggered based on CPU, GPU, and RAM stats
    """
    
    def __init__(self, *args, **kwargs):
        Vertical.__init__(self, *args, **kwargs)
        Notifier.__init__(self, "System Monitor", silent=False)
        self.notifications = []
        self.notification_states = {}  # Track which notifications have been triggered
        self.notifier = Notifier("FanControl")
        self.hysteresis_percent = 0.10  # 10% hysteresis
        self.save_file = "notifications.json"
    
    def compose(self) -> ComposeResult:
        yield Label("Create Notification", classes="form-title")
        
        with Vertical(classes="notification-form"):
            yield Input(placeholder="Notification message", id="notif-message")
            yield Select(
                [
                    ("Info", "info"),
                    ("Warning", "warning"),
                    ("Error", "error"),
                    ("Critical", "critical")
                ],
                prompt="Select notification type",
                id="notif-type"
            )
            yield Select(
                [
                    ("CPU Temperature", "cpu_temp"),
                    ("CPU Power", "cpu_power"),
                    ("CPU Usage", "cpu_usage"),
                    ("GPU Temperature", "gpu_temp"),
                    ("GPU Power", "gpu_power"),
                    ("GPU Usage", "gpu_usage"),
                    ("RAM Usage", "ram_usage"),
                    ("RAM Temperature", "ram_temp")
                ],
                prompt="Select component stat",
                id="notif-component"
            )
            yield Input(placeholder="Threshold value", id="notif-threshold")
            with Horizontal(classes="button-row"):
                yield Button("Create Notification", id="submit-notif", variant="primary")
                yield Button("Save to File", id="save-notif", variant="success")
        
        yield Label("Active Notifications", classes="list-title")
        yield ListView(id="notif-list")
    
    def on_mount(self) -> None:
        """Load notifications from file when widget is ready."""
        self.load_notifications()
    
    def save_notifications(self) -> None:
        """Save notifications to file."""
        try:
            data = {
                "notifications": self.notifications
            }
            with open(self.save_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving notifications: {e}")
    
    def load_notifications(self) -> None:
        """Load notifications from file."""
        if not os.path.exists(self.save_file):
            return
        
        try:
            with open(self.save_file, 'r') as f:
                data = json.load(f)
            
            self.notifications = data.get("notifications", [])
            
            list_view = self.query_one("#notif-list", ListView)
            list_view.clear()
            
            for notif in self.notifications:
                notif_id = notif["id"]
                component = notif["component"]
                threshold = notif["threshold"]
                notif_type = notif["type"]
                message = notif["message"]
                
                unit = '°C' if 'temp' in component else '%' if 'usage' in component else 'W'
                notif_text = f"[!{notif_type.upper()}] {message} when {component} > {threshold} {unit}"
                
                item = ListItem(
                    Horizontal(
                        Label(notif_text, classes="notif-label"),
                        Button("X", id=f"delete-{notif_id}", variant="error", classes="delete-btn"),
                        classes="notif-item-content"
                    )
                )
                list_view.append(item)
                
                self.notification_states[notif_id] = False
                
        except Exception as e:
            print(f"Error loading notifications: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle notification creation and deletion."""
        if event.button.id == "submit-notif":
            message = self.query_one("#notif-message", Input).value
            notif_type = self.query_one("#notif-type", Select).value
            component = self.query_one("#notif-component", Select).value
            threshold = self.query_one("#notif-threshold", Input).value
            
            if message and notif_type and component and threshold:
                try:
                    threshold_val = float(threshold)
                    unit = '°C' if 'temp' in component else '%' if 'usage' in component else 'W'
                    notif_text = f"[!{notif_type.upper()}] {message} when {component} > {threshold_val} {unit}"
                    
                    notif_id = len(self.notifications)
                    
                    self.notifications.append({
                        "id": notif_id,
                        "message": message,
                        "type": notif_type,
                        "component": component,
                        "threshold": threshold_val
                    })
                    
                    self.notification_states[notif_id] = False
                    
                    list_view = self.query_one("#notif-list", ListView)
                    item = ListItem(
                        Horizontal(
                            Label(notif_text, classes="notif-label"),
                            Button("✕", id=f"delete-{notif_id}", variant="error", classes="delete-btn"),
                            classes="notif-item-content"
                        )
                    )
                    list_view.append(item)
                    
                    self.query_one("#notif-message", Input).value = ""
                    self.query_one("#notif-threshold", Input).value = ""
                    
                except ValueError:
                    pass  
        
        elif event.button.id == "save-notif":
            self.save_notifications()
        
        elif event.button.id and event.button.id.startswith("delete-"):
            try:
                notif_id = int(event.button.id.split("-")[1])
                self.delete_notification(notif_id)
            except (ValueError, IndexError):
                pass
    
    def delete_notification(self, notif_id: int) -> None:
        """Delete a notification by ID."""
        self.notifications = [n for n in self.notifications if n["id"] != notif_id]
        
        if notif_id in self.notification_states:
            del self.notification_states[notif_id]
        
        list_view = self.query_one("#notif-list", ListView)
        list_view.clear()
        
        for notif in self.notifications:
            n_id = notif["id"]
            component = notif["component"]
            threshold = notif["threshold"]
            notif_type = notif["type"]
            message = notif["message"]
            
            unit = '°C' if 'temp' in component else '%' if 'usage' in component else 'W'
            notif_text = f"[!{notif_type.upper()}] {message} when {component} > {threshold} {unit}"
            
            item = ListItem(
                Horizontal(
                    Label(notif_text, classes="notif-label"),
                    Button("✕", id=f"delete-{n_id}", variant="error", classes="delete-btn"),
                    classes="notif-item-content"
                )
            )
            list_view.append(item)

    def check_thresholds(self, cpu_data: dict, gpu_data: dict, ram_data: dict):
        """Check if any notification thresholds are crossed."""
        for notif in self.notifications:
            notif_id = notif["id"]
            component = notif["component"]
            threshold = notif["threshold"]
            reset_threshold = threshold * (1 - self.hysteresis_percent)  # 10% below threshold
            crossed = False
            current_value = None
            
            if component == "cpu_temp" and cpu_data.get('temps'):
                avg_temp = sum(cpu_data['temps']) / len(cpu_data['temps'])
                current_value = avg_temp
                crossed = avg_temp > threshold
            elif component == "cpu_power" and cpu_data.get('power_w') is not None:
                current_value = cpu_data['power_w']
                crossed = cpu_data['power_w'] > threshold
            elif component == "cpu_usage" and cpu_data.get('usage_percent') is not None:
                current_value = cpu_data['usage_percent']
                crossed = cpu_data['usage_percent'] > threshold
            elif component == "gpu_temp" and gpu_data.get('temp') is not None:
                current_value = gpu_data['temp']
                crossed = gpu_data['temp'] > threshold
            elif component == "gpu_power" and gpu_data.get('power_w') is not None:
                current_value = gpu_data['power_w']
                crossed = gpu_data['power_w'] > threshold
            elif component == "gpu_usage" and gpu_data.get('usage_percent') is not None:
                current_value = gpu_data['usage_percent']
                crossed = gpu_data['usage_percent'] > threshold
            elif component == "ram_usage" and ram_data.get('used_gb') is not None and ram_data.get('total_gb') is not None:
                ram_percent = (ram_data['used_gb'] / ram_data['total_gb']) * 100
                current_value = ram_percent
                crossed = ram_percent > threshold
            elif component == "ram_temp" and ram_data.get('temps'):
                avg_ram_temp = sum(ram_data['temps']) / len(ram_data['temps'])
                current_value = avg_ram_temp
                crossed = avg_ram_temp > threshold
            
            # Only send notification when threshold is crossed for the first time
            if crossed and not self.notification_states.get(notif_id, False):
                self.notification_states[notif_id] = True
                
                if notif["type"] == "info":
                    self.notifier.send_info("MD's FanControl", notif["message"])
                elif notif["type"] == "warning":
                    self.notifier.send_warning("MD's FanControl", notif["message"])
                elif notif["type"] == "error":
                    self.notifier.send_error("MD's FanControl", notif["message"])
                elif notif["type"] == "critical":
                    self.notifier.send_critical("MD's FanControl", notif["message"])
            
            # Reset state when value drops 10% below threshold
            elif current_value is not None and current_value < reset_threshold and self.notification_states.get(notif_id, False):
                self.notification_states[notif_id] = False
