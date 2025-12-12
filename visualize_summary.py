import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import numpy as np
with open('latest_simulation_name.txt', 'r') as f:
    latest_fname = f.read().strip()
from reporting_config import YEARLY_SUMMARY_VARIABLES
def create_summary_visualization(history_file=f'{latest_fname}_population_history.json'):
    """
    Creates an interactive Plotly line chart showing total population, births,
    and deaths over time from the simulation history.
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
    
    # Define static plots that are always present
    static_plots = {
        "Total Population by Gender": [
            ("Male Population", [np.sum(d['male_age_counts']) for d in population_history], 'blue'),
            ("Female Population", [np.sum(d['female_age_counts']) for d in population_history], 'pink')
        ],
        "Annual Newborns by Gender": [
            ("Newborn Males", [d.get('newborn_males', 0) for d in population_history], 'royalblue'),
            ("Newborn Females", [d.get('newborn_females', 0) for d in population_history], 'lightpink')
        ],
        "Annual Background Deaths by Gender": [
            ("Male Deaths", [d.get('male_deaths', 0) for d in population_history], 'blue'),
            ("Female Deaths", [d.get('female_deaths', 0) for d in population_history], 'pink')
        ],
        "Vaccinated Population": [
            ("Vaccinated", [d.get('vaccinated_count', 0) for d in population_history], 'green')
        ]
    }
    
    # Dynamically add plots from the reporting config
    dynamic_plots = {}
    for var in YEARLY_SUMMARY_VARIABLES:
        title = var.replace('_', ' ').title()
        values = [d.get(var, 0) for d in population_history]
        dynamic_plots[title] = [(title, values, 'purple')]

    all_plots = {**static_plots, **dynamic_plots}
    num_rows = len(all_plots)

    fig = make_subplots(
        rows=num_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=list(all_plots.keys())
    )

    # Add traces for all defined plots
    for i, (title, traces) in enumerate(all_plots.items()):
        row_num = i + 1
        for trace_name, y_data, color in traces:
            fig.add_trace(go.Bar(name=trace_name, x=years, y=y_data, marker_color=color), row=row_num, col=1)
        fig.update_yaxes(title_text="Count", row=row_num, col=1)

    # Update layout
    fig.update_layout(title_text='Demographic and Disease Summary', barmode='group', height=300 * num_rows, showlegend=True, font=dict(size=18))
    fig.update_xaxes(title_text="Year", row=num_rows, col=1)

    fig.show()

if __name__ == '__main__':
    create_summary_visualization()