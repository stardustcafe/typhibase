import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors as pcolors
with open('latest_simulation_name.txt', 'r') as f:
    latest_fname = f.read().strip()

def visualize_environment_history(filepath=f"{latest_fname}_environment_history.json"):
    """
    Loads environmental contagion history and generates an interactive line chart.

    Args:
        filepath (str): The path to the environment history JSON file.
    """
    try:
        with open(filepath, 'r') as f:
            env_history = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {filepath} was not found.")
        print("Please run the simulation with environmental transmission enabled to generate the data file.")
        return

    if not env_history:
        print("Error: Environment history is empty.")
        return

    # Dynamically discover variables to plot
    plot_keys = [key for key in env_history[0].keys() if key != 'day']
    days = [item['day'] for item in env_history]
    colors = pcolors.qualitative.Plotly

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add a trace for each discovered variable
    for i, key in enumerate(plot_keys):
        values = [item.get(key, 0) for item in env_history]
        
        # Heuristic: Plot 'contagion' on primary axis, others on secondary
        on_secondary_y = True
        if 'contagion' in key.lower():
            on_secondary_y = False

        fig.add_trace(
            go.Scatter(
                x=days, 
                y=values, 
                mode='lines', 
                name=key.replace('_', ' ').title(),
                line=dict(color=colors[i % len(colors)])
            ),
            secondary_y=on_secondary_y,
        )

    fig.update_layout(
        title="Environmental Contagion Level Over Time",
        xaxis_title="Day",
        hovermode="x unified",
        font=dict(size=18)
    )
    fig.update_yaxes(title_text="Contagion Units", secondary_y=False, exponentformat="power")
    fig.update_yaxes(title_text="Value", secondary_y=True, exponentformat="power")

    fig.show()

if __name__ == "__main__":
    visualize_environment_history()