from rich.console import Group
from rich.ansi import AnsiDecoder
from rich.jupyter import JupyterMixin
import plotext as plt
from textual.widgets import Static
from time import sleep
import random


class PlotextGraph(JupyterMixin):
    """A Rich-compatible plotext graph that can be used in Textual."""
    
    def __init__(self, data_y=None, data_x=None, xlabel="X Axis", ylabel="Y Axis", title="Graph"):
        """
        Initialize the graph.
        
        Args:
            data_y: List of Y values [1, 2, 3, 5, 7, ...]
            data_x: List of X values [10, 20, 30, ...] (optional, defaults to indices)
            xlabel: Label for X axis
            ylabel: Label for Y axis
            title: Graph title
        """
        self.decoder = AnsiDecoder()
        self.data_y = data_y if data_y is not None else []
        self.data_x = data_x if data_x is not None else list(range(len(self.data_y)))
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title
        self.width = 100
        self.height = 15
    
    def set_data(self, data_y, data_x=None):
        """Update the graph data."""
        self.data_y = data_y
        if data_x is not None:
            self.data_x = data_x
        else:
            self.data_x = list(range(len(data_y)))
    
    def set_labels(self, xlabel=None, ylabel=None, title=None):
        """Update the graph labels."""
        if xlabel is not None:
            self.xlabel = xlabel
        if ylabel is not None:
            self.ylabel = ylabel
        if title is not None:
            self.title = title
    
    def __rich_console__(self, console, options):
        """Render the graph for Rich/Textual."""
        self.width = options.max_width or console.width
        self.height = options.height or 15
        canvas = self._make_plot()
        self.rich_canvas = Group(*self.decoder.decode(canvas))
        yield self.rich_canvas
    
    def _make_plot(self):
        """Generate the plotext graph."""
        plt.clf()
        
        if not self.data_y:
            plt.plotsize(self.width, self.height)
            plt.title(self.title)
            plt.xlabel(self.xlabel)
            plt.ylabel(self.ylabel)
            return plt.build()
        
        data_x = self.data_x if len(self.data_x) == len(self.data_y) else list(range(len(self.data_y)))
        
        plt.plot(data_x, self.data_y, marker="braille")
        plt.plotsize(self.width, self.height)
        plt.title(self.title)
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        plt.theme("clear")
        
        return plt.build()


class GraphWidget(Static):
    """A Textual widget that displays a PlotextGraph."""
    
    def __init__(self, data_y=None, data_x=None, xlabel="X Axis", ylabel="Y Axis", 
                 title="Graph", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = PlotextGraph(data_y, data_x, xlabel, ylabel, title)
    
    def set_data(self, data_y, data_x=None):
        """Update the graph data and re-render."""
        self.graph.set_data(data_y, data_x)
        self.update(self.graph)
    
    def set_labels(self, xlabel=None, ylabel=None, title=None):
        """Update the graph labels and re-render."""
        self.graph.set_labels(xlabel, ylabel, title)
        self.update(self.graph)
    
    def on_mount(self) -> None:
        """Render the initial graph."""
        self.update(self.graph)
