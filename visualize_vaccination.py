import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

def create_vaccination_visualization(history_file='population_history.json'):
    """
    Creates an interactive Plotly visualization to compare simulations with and without vaccination.
    """
    try:
        with open(history_file, 'r') as f:
            population_history = json.load(f)
    except FileNotFoundError:
        print(f"Error: Population history file '{history_file}' not found.")
        print("Please run 'runmain.py' first to generate the simulation data.")
        return

    if not population_history:
        print("Error: Population history is empty. No data to visualize.")
        return

    # Extract data from history
    years = [d['year'] for d in population_history]
    male_deaths = [d.get('male_deaths', 0) for d in population_history]
    female_deaths = [d.get('female_deaths', 0) for d in population_history]
    disease_male_deaths = [d.get('disease_male_deaths', 0) for d in population_history]
    disease_female_deaths = [d.get('disease_female_deaths', 0) for d in population_history]

    # Calculate total disease deaths for the new chart
    total_disease_deaths = [m + f for m, f in zip(disease_male_deaths, disease_female_deaths)]

    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=("Total Annual Disease-Related Deaths")
    )

    # --- Total Disease Deaths Graph (New) ---
    fig.add_trace(
        go.Bar(name='Total Disease Deaths', x=years, y=total_disease_deaths, marker_color='purple', showlegend=False),
        row=1, col=1
    )

    fig.update_layout(title_text='Vaccination Impact on Mortality', font=dict(size=18))
    fig.show()