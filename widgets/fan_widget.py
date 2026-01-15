from textual.app import ComposeResult
from textual.widgets import Static, Input, Select, Button
from textual.containers import Vertical, Horizontal
from utils import FanController
import re
import json
import os


class FanWidget(Vertical):
    """
    Widget to display and control a single fan.
    Args:
        fan_data: Dictionary with fan information, e.g.:
            {
                'path': '/sys/class/hwmon/hwmon0/fan1',
                'label': 'Chassis Fan 1',
                'current_speed': 45.0,
                'current_rpm': 1200,
                'mode': 'auto',
                'hwmon_chip': 'asus-isa-0000'
            }
    """
    
    def __init__(self, fan_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fan_data = fan_data
        self.fan_controller = FanController()
        self.fan_id = self._sanitize_path(fan_data['path'])
        self.border_title = fan_data.get('label', 'Unknown Fan')
        self.graphs = {}
        self.selected_graph = None
        self.current_temps = {}

    def _sanitize_path(self, path: str) -> str:
        """Convert a file path to a valid widget ID."""
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', path)
        if sanitized and sanitized[0].isdigit():
            sanitized = 'fan_' + sanitized
        return sanitized

    def set_fan_data(self, fan_data):
        """
        Update fan data and refresh display.
        Args:
            fan_data: Dictionary with updated fan information (same format as in __init__).
        """
        self.fan_data = fan_data
        self.border_title = fan_data.get('label', 'Unknown Fan')
        self.refresh_fan_info()

    def get_graphs(self) -> dict:
        """Get graphs from graphs.json"""
        if os.path.exists("graphs.json"):
            try:
                with open("graphs.json", "r") as f:
                    content = f.read().strip()
                    if content:
                        self.graphs = json.loads(content)
                        return self.graphs
            except (json.JSONDecodeError, Exception):
                pass
        return {}
    
    def get_current_value_for_graph(self, graph_title: str, current_stat_value: float) -> float:
        """
        Interpolate fan speed based on current stat value.
        For example, if graph has points [(10, 20), (30, 50), (50, 100)]
        and current value is 20, it returns 35.0
        """
        if graph_title not in self.graphs:
            return 0.0
        
        graph_data = self.graphs[graph_title]["data"]
        if not graph_data:
            return 0.0
        
        sorted_data = sorted(graph_data, key=lambda point: point[0])
        
        if current_stat_value <= sorted_data[0][0]:
            return sorted_data[0][1]
        
        if current_stat_value >= sorted_data[-1][0]:
            return sorted_data[-1][1]
        
        for i in range(len(sorted_data) - 1):
            x1, y1 = sorted_data[i]
            x2, y2 = sorted_data[i + 1]
            
            if x1 <= current_stat_value <= x2:
                if x2 == x1:
                    return y1
                ratio = (current_stat_value - x1) / (x2 - x1)
                interpolated_speed = y1 + ratio * (y2 - y1)
                return interpolated_speed
        
        return 0.0

    def update_temps(self, cpu_data: dict, gpu_data: dict, ram_data: dict):
        """
        Update current temperature data for graph mode.
        Args:
            cpu_data: Dictionary with CPU stats (temps, power_w, usage_percent).
            gpu_data: Dictionary with GPU stats (temp, power_w, usage_percent).
            ram_data: Dictionary with RAM stats (used_gb, total_gb, temps).
        """
        self.current_temps = {
            'cpu_temp': sum(cpu_data.get('temps', [0])) / len(cpu_data.get('temps', [1])),
            'cpu_power': cpu_data.get('power_w', 0),
            'cpu_usage': cpu_data.get('usage_percent', 0),
            'gpu_temp': gpu_data.get('temp', 0),
            'gpu_power': gpu_data.get('power_w', 0),
            'gpu_usage': gpu_data.get('usage_percent', 0),
            'ram_usage': (ram_data.get('used_gb', 0) / ram_data.get('total_gb', 1)) * 100,
            'ram_temp': sum(ram_data.get('temps', [0])) / len(ram_data.get('temps', [1]))
        }
        

        mode_select = self.query_one(f"#fan-mode-{self.fan_id}", Select)
        graph_select = self.query_one(f"#fan-graph-{self.fan_id}", Select)
        
        if mode_select.value == "graph" and graph_select.value and graph_select.value != Select.BLANK:
            self.apply_graph_curve(graph_select.value)

    def apply_graph_curve(self, graph_title: str):
        """Apply fan curve based on selected graph."""
        if graph_title not in self.graphs:
            return
        
        graph_info = self.graphs[graph_title]
        xlabel = graph_info.get("xlabel", "")
        
        component_key = None
        if "Cpu Temp" in xlabel:
            component_key = 'cpu_temp'
        elif "Cpu Power" in xlabel:
            component_key = 'cpu_power'
        elif "Cpu Usage" in xlabel:
            component_key = 'cpu_usage'
        elif "Gpu Temp" in xlabel:
            component_key = 'gpu_temp'
        elif "Gpu Power" in xlabel:
            component_key = 'gpu_power'
        elif "Gpu Usage" in xlabel:
            component_key = 'gpu_usage'
        elif "Ram Usage" in xlabel:
            component_key = 'ram_usage'
        elif "Ram Temp" in xlabel:
            component_key = 'ram_temp'
        
        if component_key and component_key in self.current_temps:
            current_value = self.current_temps[component_key]
            target_speed = self.get_current_value_for_graph(graph_title, current_value)
            
            if 0 <= target_speed <= 100:
                self.fan_controller.set_mode(self.fan_data['path'], 'manual')
                self.fan_controller.set_speed(self.fan_data['path'], int(target_speed))

    def compose(self) -> ComposeResult:
        self.fan_info = Static("Loading...", classes="fan-info-text")
        yield self.fan_info
        
        with Horizontal(classes="fan-control-row"):
            self.mode_select = Select(
                [
                    ("Auto", "auto"),
                    ("Manual", "manual"),
                    ("Graph", "graph"),
                ],
                value="auto" if self.fan_data.get('mode') != 'manual' else "manual",
                id=f"fan-mode-{self.fan_id}"
            )
            yield self.mode_select
            
            graphs = self.get_graphs()
            graph_options = [(title, title) for title in graphs.keys()]
            self.graph_select = Select(
                graph_options,
                prompt="Select graph curve",
                id=f"fan-graph-{self.fan_id}",
            )
            self.graph_select.display = False
            yield self.graph_select
            
            self.speed_input = Input(
                placeholder="Speed %", 
                id=f"fan-speed-{self.fan_id}",
                disabled=False
            )
            yield self.speed_input
            
            yield Button(
                "Set", 
                id=f"set-fan-speed-{self.fan_id}", 
                variant="primary",
                disabled=False
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle setting fan speed."""
        if event.button.id and event.button.id == f"set-fan-speed-{self.fan_id}":
            speed_str = self.speed_input.value
            if speed_str:
                try:
                    speed = int(speed_str)
                    if 0 <= speed <= 100:
                        # Set to manual mode first
                        self.fan_controller.set_mode(self.fan_data['path'], 'manual')
                        # Then set the speed
                        self.fan_controller.set_speed(self.fan_data['path'], speed)
                        self.speed_input.value = ""
                except ValueError:
                    pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Enable/disable speed input based on mode."""
        if event.select.id == f"fan-mode-{self.fan_id}":
            if event.value == "manual":
                self.speed_input.display = "block"
                self.query_one(f"#set-fan-speed-{self.fan_id}", Button).display = "block"
                self.graph_select.display = "none"
                self.fan_controller.set_mode(self.fan_data['path'], 'manual')
            elif event.value == "graph":
                self.speed_input.display = "none"
                self.query_one(f"#set-fan-speed-{self.fan_id}", Button).display = "none"
                self.graph_select.display = "block"
            else:
                self.speed_input.display = "none"
                self.query_one(f"#set-fan-speed-{self.fan_id}", Button).display = "none"
                self.graph_select.display = "none"
                self.fan_controller.set_mode(self.fan_data['path'], 'auto')
        
        elif event.select.id == f"#fan-graph-{self.fan_id}":
            if event.value and event.value != Select.BLANK:
                self.selected_graph = event.value

    def refresh_fan_info(self) -> None:
        """Refresh the displayed fan information."""
        info_text = f"Speed: {self.fan_data.get('current_speed', 0):.1f}% | "
        info_text += f"RPM: {self.fan_data.get('current_rpm', 0)} | "
        info_text += f"Mode: {self.fan_data.get('mode', 'unknown')}\n"
        info_text += f"Chip: {self.fan_data.get('hwmon_chip', 'N/A')}"
        self.fan_info.update(info_text)

    def on_mount(self) -> None:
        """Refresh fan info when widget mounts."""
        self.refresh_fan_info()
