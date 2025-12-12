import plotly.graph_objects as go
import json
import numpy as np

with open('latest_simulation_name.txt', 'r') as f:
    latest_fname = f.read().strip() 
# Define the same age bins and labels as used in simulation.py
PYRAMID_AGE_BINS = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 150]
PYRAMID_AGE_LABELS = []
for i in range(len(PYRAMID_AGE_BINS) - 2):
    PYRAMID_AGE_LABELS.append(f'{PYRAMID_AGE_BINS[i]}-{PYRAMID_AGE_BINS[i+1]-1}')
PYRAMID_AGE_LABELS.append(f'{PYRAMID_AGE_BINS[-2]}+') # This will be '80+'

def create_population_pyramid_visualization(history_file=f'{latest_fname}_population_history.json'):
    """
    Creates an interactive Plotly population pyramid visualization with a slider
    based on the simulation history.
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
        print("Please ensure the simulation runs for at least one year and generates data.")
        return

    # Create figure
    fig = go.Figure()

    # Create frames for the animation/slider
    frames = []
    max_population_count = 0
    for i, year_data in enumerate(population_history):
        year = year_data['year']
        male_counts = np.array(year_data['male_age_counts'])
        female_counts = np.array(year_data['female_age_counts'])
        
        # Update max_population_count for x-axis range
        current_max = 0
        if male_counts.size > 0:
            current_max = max(current_max, np.max(male_counts))
        if female_counts.size > 0:
            current_max = max(current_max, np.max(female_counts))
        max_population_count = max(max_population_count, current_max)
        
        frame_data = [
            go.Bar(
                y=PYRAMID_AGE_LABELS,
                x=-male_counts, # Negative values for males to plot on the left
                orientation='h',
                name='Male',
                marker=dict(color='cornflowerblue'),
                customdata=male_counts, # Store absolute values for hover text
                hovertemplate='Age: %{y}<br>Population: %{customdata}<extra></extra>'
            ),
            go.Bar(
                y=PYRAMID_AGE_LABELS,
                x=female_counts, # Positive values for females
                orientation='h',
                name='Female',
                marker=dict(color='lightcoral'),
                hoverinfo='y+x'
            ),
            go.Bar(
                y=PYRAMID_AGE_LABELS,
                x=female_counts-male_counts, # Positive values for females
                orientation='h',
                name='Excess',
                marker=dict(color='grey'),
                hoverinfo='y+x'
            ),
        ]
        
        frames.append(go.Frame(data=frame_data, name=str(year)))

    # Add initial trace (first year)
    initial_year_data = population_history[0]
    initial_male_counts = np.array(initial_year_data['male_age_counts'])
    initial_female_counts = np.array(initial_year_data['female_age_counts'])
    initial_difference = initial_female_counts-initial_male_counts
    fig.add_trace(go.Bar(
        y=PYRAMID_AGE_LABELS,
        x=-initial_male_counts,
        orientation='h',
        name='Male',
        marker=dict(color='cornflowerblue'),
        customdata=initial_male_counts,
        hovertemplate='Age: %{y}<br>Population: %{customdata}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        y=PYRAMID_AGE_LABELS,
        x=initial_female_counts,
        orientation='h',
        name='Female',
        marker=dict(color='lightcoral'),
        hovertemplate='Age: %{y}<br>Population: %{x}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        y=PYRAMID_AGE_LABELS,
        x=initial_difference,
        orientation='h',
        name='Excess',
        marker=dict(color='grey'),
        hovertemplate='Age: %{y}<br>Population: %{x}<extra></extra>'
    ))
    # Add a scatter trace for the central y-axis labels
    fig.add_trace(go.Scatter(
        x=[0] * len(PYRAMID_AGE_LABELS), # Position at x=0
        y=PYRAMID_AGE_LABELS,
        mode='text',
        text=PYRAMID_AGE_LABELS,
        textposition='middle center',
        hoverinfo='none',
        showlegend=False
    ))

    # Add frames to the figure
    fig.frames = frames

    # Create slider steps
    slider_steps = []
    for i, year_data in enumerate(population_history):
        step = dict(
            method="animate",
            args=[
                [str(year_data['year'])],
                dict(mode="immediate",
                     frame=dict(duration=300, redraw=True),
                     transition=dict(duration=0))
            ],
            label=str(year_data['year'])
        )
        slider_steps.append(step)

    # Add slider and update layout
    fig.update_layout(
        barmode='relative', # Bars drawn from zero
        title='Population Pyramid Over Years',
        xaxis_title='Population',
        yaxis_title='', # Remove the original y-axis title
        yaxis=dict(
            showticklabels=False # Hide the labels on the left axis
        ),
        sliders=[dict(steps=slider_steps, active=0, currentvalue={"prefix": "Year: "}, pad={"t": 50})],
        updatemenus=[dict(type="buttons", buttons=[dict(label="Play", method="animate", args=[None, {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True, "transition": {"duration": 300, "easing": "quadratic-in-out"}}])])],
        # Set x-axis range and format labels to be positive
        xaxis=dict(
            range=[-max_population_count * 1.1, max_population_count * 1.1],
            tickvals=[-max_population_count, -max_population_count/2, 0, max_population_count/2, max_population_count],
            ticktext=[f'{max_population_count:,.0f}', f'{max_population_count/2:,.0f}', '0', f'{max_population_count/2:,.0f}', f'{max_population_count:,.0f}']
        ),
        font=dict(size=18)
    )

    fig.show()

if __name__ == '__main__':
    create_population_pyramid_visualization()