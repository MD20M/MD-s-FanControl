from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Vertical
from widgets.graphWidget import GraphWidget
from collections import deque


class MonitorBox(Vertical):
    """
    A box widget to monitor system stats with multiple graphs.
    Args:
        title: Title of the monitor box.
        graph_configs: List of dictionaries with graph configurations, e.g.:
            [
                {"title": "Temperature (°C)", "ylabel": "°C"},
                {"title": "Power (W)", "ylabel": "W"},
                {"title": "Usage (%)", "ylabel": "%"}
            ]
        max_data_points: Maximum number of data points to retain for each graph.
    """
    
    def __init__(self, title: str, graph_configs: list[dict], max_data_points: int = 50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.box_title = title
        self.max_data_points = max_data_points
        self.graph_configs = graph_configs
        self.data_histories = [deque(maxlen=max_data_points) for _ in graph_configs]
        self.border_title = title
        self.current_graph_index = 0
    
    def compose(self) -> ComposeResult:
        self.info_text = Static("Initializing...", classes="info-text")
        yield self.info_text
        
        self.graphs = []
        for i, config in enumerate(self.graph_configs):
            graph = GraphWidget(
                data_y=[],
                xlabel="Time",
                ylabel=config.get("ylabel", "Value"),
                title=config.get("title", "")
            )
            graph.display = (i == 0) 
            self.graphs.append(graph)
            yield graph
    
    def update_data(self, text: str, values: list[float]):
        """Update the display with new data."""
        self.info_text.update(text)
        for i, value in enumerate(values):
            if i < len(self.data_histories):
                self.data_histories[i].append(value)
                self.graphs[i].set_data(list(self.data_histories[i]))
    
    def cycle_graph(self):
        """Cycle to the next graph."""
        self.graphs[self.current_graph_index].display = False
        self.current_graph_index = (self.current_graph_index + 1) % len(self.graphs)
        self.graphs[self.current_graph_index].display = True
