from textual.app import ComposeResult
from textual.widgets import Input, Select, Button
from textual.containers import Vertical, Horizontal, VerticalScroll
from widgets.graphWidget import GraphWidget

class GraphsPage(Vertical):
    """
    A page with being able to add graphs with format {[x,y], [x,y], ...}, custom title, the x and y labels are determined by the compnent and it's stat (eg. CPU temp, GPU usage, etc.). 
    The graphs also get displayed and can be edited by entering the same title as the graph title in add graph page. 
    The graphs are also saved to a JSON file and loaded on startup.        
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graphs = {}
        self.input_row_count = 0
        self.input_rows_container = None
        self.graphs_container = None

    def add_graph(self, title: str, data: list[tuple], xlabel: str, ylabel: str) -> None:
        """
        Add a new graph to the page.
        Args:
            title: Title of the graph.
            data: List of (x, y) tuples representing the graph data points.
            xlabel: Label for the X axis.
            ylabel: Label for the Y axis.
        """
        if title in self.graphs:
            self.remove_graph(title)
        
        sorted_data = sorted(data, key=lambda point: point[0])
        
        graph = GraphWidget(
            data_y=[y for x, y in sorted_data],
            data_x=[x for x, y in sorted_data],
            xlabel=xlabel,
            ylabel=ylabel,
            title=title
        )
        self.graphs[title] = graph
        if self.graphs_container:
            self.graphs_container.mount(graph)
            self.save_graphs_to_file()

    def remove_graph(self, title: str) -> None:
        """Remove a graph from the page."""
        graph = self.graphs.pop(title, None)
        if graph:
            graph.remove()

    def update_graph(self, title: str, data: list[tuple]) -> None:
        """
        Update an existing graph with new data.
        Args:
            title: Title of the graph to update.
            data: New list of (x, y) tuples representing the graph data points.
        """
        graph = self.graphs.get(title)
        if graph:
            sorted_data = sorted(data, key=lambda point: point[0])
            graph.set_data(
                [y for x, y in sorted_data],
                [x for x, y in sorted_data]
            )

    def save_graphs_to_file(self) -> None:
        """Save the graph JSON"""
        with open("graphs.json", "w") as f:
            import json
            json.dump({
                title: {
                    "data": [(x, y) for x, y in zip(graph.graph.data_x, graph.graph.data_y)],
                    "xlabel": graph.graph.xlabel,
                    "ylabel": graph.graph.ylabel
                }
                for title, graph in self.graphs.items()
            }, f, indent=4)

    def load_graphs_from_file(self) -> None:
        """Load the graph JSON"""
        try:
            with open("graphs.json", "r") as f:
                import json
                content = f.read().strip()
                if not content:
                    return
                graphs_data = json.loads(content)
                for title, graph_data in graphs_data.items():
                    if self.graphs_container:
                        # Convert data format: [[x, y], [x, y]] -> [(x, y), (x, y)]
                        data_tuples = [tuple(pair) if isinstance(pair, list) else pair 
                                      for pair in graph_data["data"]]
                        self.add_graph(
                            title,
                            data_tuples,
                            graph_data["xlabel"],
                            graph_data["ylabel"]
                        )
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            pass 

    def expanding_input(self) -> ComposeResult:
        """Expand the input area for adding graph data."""
        yield self.create_input_row()
    
    def create_input_row(self) -> Horizontal:
        """Create a single input row with x, y inputs, add button, and remove button."""
        row_id = self.input_row_count
        self.input_row_count += 1
        
        return Horizontal(
            Input(placeholder="Stat Value (X)", id=f"x-input-{row_id}", classes="coord-input"),
            Input(placeholder="Fan Speed % (Y)", id=f"y-input-{row_id}", classes="coord-input"),
            Button("+", id=f"add-row-{row_id}", variant="success", classes="add-row-btn"),
            Button("-", id=f"remove-row-{row_id}", variant="error", classes="remove-row-btn"),
            classes="input-row"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle adding new input rows and removing rows."""
        if event.button.id and event.button.id.startswith("add-row-"):
            new_row = self.create_input_row()
            if self.input_rows_container:
                self.input_rows_container.mount(new_row)
        elif event.button.id and event.button.id.startswith("remove-row-"):
            button = event.button
            row = button.parent
            if row and isinstance(row, Horizontal):
                row.remove()
        elif event.button.id == "add-graph-btn":
            self.handle_add_graph()

    def handle_add_graph(self) -> None:
        """Handle the add graph button press."""
        title_input = self.query_one("#graph-title-input", Input)
        component_select = self.query_one("#notif-component", Select)
        
        title = title_input.value
        component = component_select.value
        
        if not title or not component:
            return
        
        data = []
        for row in self.query(".input-row"):
            try:
                x_input = row.query_one(".coord-input")
                inputs = list(row.query(".coord-input"))
                if len(inputs) >= 2:
                    x_val = float(inputs[0].value)  # Stat value
                    y_val = float(inputs[1].value)  # Fan speed %
                    data.append((x_val, y_val))
            except (ValueError, Exception):
                continue
        
        if data:
            xlabel_unit = '°C' if 'temp' in component else '%' if 'usage' in component else 'W'
            xlabel = f"{component.replace('_', ' ').title()} ({xlabel_unit})"
            
            self.add_graph(title, data, xlabel, "Fan Speed (%)")
            
            # Clear inputs
            title_input.value = ""

    def on_mount(self) -> None:
        """Load graphs when the widget mounts."""
        self.call_after_refresh(self.load_graphs_from_file)

    def on_unmount(self) -> None:
        """Save graphs when the app closes."""
        self.save_graphs_to_file()
    
    def compose(self) -> ComposeResult:
        """Contains graph title input """
        with Vertical(classes="graph-input-container"):
            yield Input(placeholder="Graph Title", id="graph-title-input", classes="graph-title-input")
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
            with Vertical(id="input-rows-container", classes="input-rows-container") as container:
                self.input_rows_container = container
                yield from self.expanding_input()
            yield Button("Add Graph", id="add-graph-btn", variant="primary", classes="add-graph-btn")

        with VerticalScroll(classes="graphs-display-container", id="graphs-display") as scroll_container:
            self.graphs_container = scroll_container