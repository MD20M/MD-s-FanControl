from textual.app import ComposeResult
from textual.widgets import Label
from textual.containers import Vertical
from utils import FanController
from .fan_widget import FanWidget


class FanControlManager(Vertical):
    """Manager for all fan widgets."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fan_controller = FanController()
        self.fan_widgets = []

    def compose(self) -> ComposeResult:
        """Compose fan widgets based on available fans."""
        fan_info = self.fan_controller.get_info()
        
        if fan_info.get('available') and fan_info.get('devices'):
            for fan_data in fan_info['devices']:
                fan_widget = FanWidget(fan_data, classes="fan-widget")
                self.fan_widgets.append(fan_widget)
                yield fan_widget
        else:
            yield Label("No fans detected or fan control not available", classes="error-message")

    def update_fans(self, cpu_data: dict = None, gpu_data: dict = None, ram_data: dict = None) -> None:
        """Update all fan widgets with fresh data."""
        fan_info = self.fan_controller.get_info()
        
        if fan_info.get('available') and fan_info.get('devices'):
            for i, fan_data in enumerate(fan_info['devices']):
                if i < len(self.fan_widgets):
                    self.fan_widgets[i].set_fan_data(fan_data)
                    
                    if cpu_data and gpu_data and ram_data:
                        self.fan_widgets[i].update_temps(cpu_data, gpu_data, ram_data)
