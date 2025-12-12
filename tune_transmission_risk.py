import numpy as np
import plotly.graph_objects as go
from compartmental_model import CompartmentalModel
import os

def run_parameter_sweep():
    # Define range of values to test
    # Current value causing spikes is around 1e-4 (10/100000)
    # Previous "stable" value was likely around 1e-4 / 365 ~= 2.7e-7
    
    # Let's test logarithmic steps around these values
    risk_values = [1e-4, 1e-3, 1e-2, 1e-1, 1e-0]
    
    results = {}
    
    print(f"Starting parameter sweep for BASE_TRANSMISSION_RISK...")
    print(f"Testing values: {risk_values}")
    
    for risk in risk_values:
        print(f"Testing risk = {risk:.2e}...")
        model = CompartmentalModel(base_transmission_risk=risk)
        
        # Run model (suppress print output if possible, or just let it print)
        # We need to capture the history. The run() method saves files but also populates self.sir_history
        
        # We can't easily suppress print from run() without redirecting stdout, 
        # but run() prints yearly summaries which is fine.
        model.run()
        
        # Extract data for plotting
        # We want Infected (Acute + Subclinical) over time
        days = [d['day'] for d in model.sir_history]
        infected = [d['ACUTE'] + d['SUBCLINICAL'] for d in model.sir_history]
        
        results[risk] = {
            'days': days,
            'infected': infected
        }
        
    return results

def visualize_sweep_results(results):
    fig = go.Figure()
    
    for risk, data in results.items():
        fig.add_trace(go.Scatter(
            x=data['days'],
            y=data['infected'],
            mode='lines',
            name=f"Risk={risk:.2e}"
        ))
        
    fig.update_layout(
        title="Impact of Base Transmission Risk on Infection Stability",
        xaxis_title="Day",
        yaxis_title="Infected Agents (Acute + Subclinical)",
        hovermode="x unified",
        height=800
    )
    
    output_file = "transmission_risk_sweep.html"
    fig.write_html(output_file)
    print(f"Saved visualization to {output_file}")

if __name__ == "__main__":
    results = run_parameter_sweep()
    visualize_sweep_results(results)
