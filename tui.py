from textual.app import App, ComposeResult
from textual.widgets import Footer, TabbedContent, TabPane
from textual.containers import Vertical
from utils import get_cpu_info, get_gpu_info, get_ram_info
from widgets import MonitorBox, NotificationManager, FanControlManager, GraphsPage

class GridLayoutExample(App[None]):
    """A Textual app demonstrating a grid layout with system monitors, notifications, and fan control."""
    CSS_PATH = "layout.tcss"
    
    BINDINGS = [
        ("^q", "ctrl+quit", "Quit"),
        ("s", "show_tab('stats')", "Stats"),
        ("n", "show_tab('notifs')", "Notifications"),
        ("f", "show_tab('fc')", "Fan Control"),
        ("c", "cycle_cpu", "Cycle CPU"),
        ("g", "cycle_gpu", "Cycle GPU"),
        ("r", "cycle_ram", "Cycle RAM"),
    ]
    
    def compose(self) -> ComposeResult:
        self.cpu_box = MonitorBox(
            "CPU Monitor",
            [
                {"title": "Temperature (°C)", "ylabel": "°C"},
                {"title": "Power (W)", "ylabel": "W"},
                {"title": "Usage (%)", "ylabel": "%"}
            ],
            classes="box"
        )
        self.gpu_box = MonitorBox(
            "GPU Monitor",
            [
                {"title": "Temperature (°C)", "ylabel": "°C"},
                {"title": "Power (W)", "ylabel": "W"},
                {"title": "Usage (%)", "ylabel": "%"}
            ],
            classes="box"
        )
        self.ram_box = MonitorBox(
            "RAM Monitor",
            [
                {"title": "Usage (%)", "ylabel": "%"},
                {"title": "Temperature (°C)", "ylabel": "°C"}
            ],
            classes="box"
        )

        self.notificationManager = NotificationManager(classes="notification-manager")
        self.fanControlManager = FanControlManager(classes="fan-control-manager")

        with TabbedContent(initial="stats"):
            with TabPane("System Stats", id="stats"):
                with Vertical(classes="stat-container"):
                    yield self.cpu_box
                    yield self.gpu_box
                    yield self.ram_box
            with TabPane("Notifications", id="notifs"):
                yield self.notificationManager
            with TabPane("Fan Control", id="fc"):
                with TabbedContent(initial="fan-control"):
                    with TabPane("Fan Control", id="fan-control"):
                        yield self.fanControlManager
                    with TabPane("Fan Graphs", id="fan-graphs"):
                        yield GraphsPage()
        yield Footer()

    def action_show_tab(self, tab: str) -> None:
        """Switch to a new tab."""
        self.get_child_by_type(TabbedContent).active = tab
    
    def action_cycle_cpu(self) -> None:
        """Cycle CPU graph."""
        self.cpu_box.cycle_graph()
    
    def action_cycle_gpu(self) -> None:
        """Cycle GPU graph."""
        self.gpu_box.cycle_graph()
    
    def action_cycle_ram(self) -> None:
        """Cycle RAM graph."""
        self.ram_box.cycle_graph()
    
    def on_mount(self) -> None:
        """Start the update timer when app mounts."""
        self.set_interval(1.0, self.update_monitors)
    
    def update_monitors(self) -> None:
        """Update all monitors with fresh data."""
        cpu_info = get_cpu_info()
        cpu_temps = cpu_info.get('temps', [])
        avg_temp = sum(cpu_temps) / len(cpu_temps) if cpu_temps else 0
        cpu_power = cpu_info.get('power_w', 0)
        cpu_usage = cpu_info.get('usage_percent', 0)
        
        cpu_text = f"Temperature: {avg_temp:.1f}°C\n"
        cpu_text += f"Power: {cpu_power:.1f}W\n" if cpu_power else ""
        cpu_text += f"Usage: {cpu_usage:.1f}%"
        
        self.cpu_box.update_data(cpu_text, [avg_temp, cpu_power, cpu_usage])
        
        gpu_info = get_gpu_info()
        if isinstance(gpu_info, dict):
            gpu_temp = gpu_info.get('temp', 0)
            gpu_power = gpu_info.get('power_w', 0)
            gpu_usage = gpu_info.get('usage_percent', 0)
            gpu_model = gpu_info.get('model', 'Unknown')
            
            gpu_text = f"Model: {gpu_model}\n"
            gpu_text += f"Temperature: {gpu_temp:.1f}°C\n"
            gpu_text += f"Power: {gpu_power:.1f}W\n" if gpu_power else ""
            gpu_text += f"Usage: {gpu_usage:.1f}%" if gpu_usage is not None else ""
            
            self.gpu_box.update_data(gpu_text, [gpu_temp or 0, gpu_power, gpu_usage if gpu_usage is not None else 0])
        else:
            self.gpu_box.update_data(str(gpu_info), [0, 0, 0])
        
        ram_info = get_ram_info()
        ram_used = ram_info.get('used_gb', 0)
        ram_total = ram_info.get('total_gb', 0)
        ram_percent = (ram_used / ram_total * 100) if ram_total > 0 else 0
        ram_temps = ram_info.get('temps', [])
        avg_ram_temp = sum(ram_temps) / len(ram_temps) if ram_temps else 0
        
        ram_text = f"Usage: {ram_used:.1f}GB / {ram_total:.1f}GB ({ram_percent:.1f}%)\n"
        if ram_temps:
            ram_text += f"Temperature: {avg_ram_temp:.1f}°C"
        
        self.ram_box.update_data(ram_text, [ram_percent, avg_ram_temp])

        self.notificationManager.check_thresholds(cpu_info, gpu_info if isinstance(gpu_info, dict) else {}, ram_info)
        
        self.fanControlManager.update_fans(cpu_info, gpu_info if isinstance(gpu_info, dict) else {}, ram_info)


if __name__ == "__main__":
    app = GridLayoutExample()
    app.run()