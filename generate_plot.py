import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def visualize_results():
    results = {
        "No Vaccine": "vaccine_No_Vaccine_sir_history.json",
        "9m-15y": "vaccine_9m-15y_sir_history.json",
        "16m-15y": "vaccine_16m-15y_sir_history.json"
    }
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Infected Population Over Time", "Cost Analysis (DALYs)"),
        vertical_spacing=0.15,
        specs=[[{"type": "scatter"}], [{"type": "bar"}]]
    )
    
    daly_results = {}

    for scenario_name, filepath in results.items():
        if not filepath or not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        days = [d['day'] for d in data]
        # Calculate Total Infected (Acute + Subclinical)
        infected = [d.get('ACUTE', 0) + d.get('SUBCLINICAL', 0) for d in data]
        
        # Calculate DALYs
        # YLD = Sum(Acute Cases * Disability Weight)
        # Disability weight for Typhoid (Infectious disease: acute episode, moderate) = 0.051 (GBD 2017)
        total_yld = sum([d.get('ACUTE', 0) for d in data]) * 0.051 / 365.0 
        
        # YLL = Sum(YLL from model)
        total_yll = sum([d.get('yll', 0) for d in data])
        
        total_daly = total_yld + total_yll
        daly_results[scenario_name] = total_daly
        
        fig.add_trace(go.Scatter(
            x=days, 
            y=infected, 
            mode='lines', 
            name=scenario_name
        ), row=1, col=1)

    # Add DALY bar chart
    fig.add_trace(go.Bar(
        x=list(daly_results.keys()),
        y=list(daly_results.values()),
        name="Total DALYs",
        marker_color='indianred'
    ), row=2, col=1)

    fig.update_layout(
        title=f"Vaccine Impact & Cost Analysis (N=100000, 15 Years)",
        height=900,
        hovermode="x unified",
        font=dict(size=18)
    )
    
    fig.update_xaxes(title_text="Day", row=1, col=1)
    fig.update_yaxes(title_text="Infected Agents", row=1, col=1)
    
    fig.update_xaxes(title_text="Scenario", row=2, col=1)
    fig.update_yaxes(title_text="Total DALYs", row=2, col=1)
    
    fig.write_html("vaccine_cost_analysis.html")
    print("Saved visualization to vaccine_cost_analysis.html")

if __name__ == "__main__":
    visualize_results()
