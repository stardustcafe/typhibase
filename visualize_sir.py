import json
import plotly.graph_objects as go
import plotly.colors as pcolors

with open('latest_simulation_name.txt', 'r') as f:
    latest_fname = f.read().strip()
    print(latest_fname)

def visualize_sir_history(filepath=f"{latest_fname}_sir_history.json"):
    """
    Loads disease history data and generates a dynamic, interactive Plotly line chart.

    Args:
        filepath (str): The path to the SIR history JSON file.
    """
    try:
        with open(filepath, 'r') as f:
            sir_history = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {filepath} was not found.")
        print("Please run the simulation first to generate the data file.")
        return

    if not sir_history:
        print("Error: The history file is empty.")
        return

    # Dynamically find all state keys, excluding 'day'
    all_keys = sir_history[0].keys()
    state_keys = [key for key in all_keys if key != 'day']
    
    days = [item['day'] for item in sir_history]
    colors = pcolors.qualitative.Dark24 # Get a list of distinct colors

    fig = go.Figure()

    # Loop through the discovered states and add a trace for each one
    for i, state in enumerate(state_keys):
        counts = [item[state] for item in sir_history]
        fig.add_trace(go.Scatter(x=days, y=counts, mode='lines', name=state, line=dict(color=colors[i % len(colors)])))

    fig.update_layout(
        title="Disease Compartment Counts Over Time",
        xaxis_title="Day",
        yaxis_title="Number of Agents",
        hovermode="x unified",
        font=dict(size=18)
    )

    fig.show()

if __name__ == "__main__":
    visualize_sir_history()