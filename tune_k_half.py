import numpy as np
import plotly.graph_objects as go
from compartmental_model import CompartmentalModel
from initialparaandconst import K_HALF
import os

def run_k_half_sweep():
    # Define range of values to test
    # Current K_HALF is INITIAL_INFECTED_COUNT * ENVIRONMENTAL_SHEDDING_RATE
    # = 3000 * 1000 = 3,000,000
    
    # Let's test orders of magnitude around this value
    base_val = 3000000
    k_values = [base_val * 0.001, base_val * 0.01, base_val *0.1, base_val * 10, base_val * 10**2, base_val * 10**3]
    
    results = {}
    
    print(f"Starting parameter sweep for K_HALF...")
    print(f"Testing values: {k_values}")
    
    for k in k_values:
        print(f"Testing K_HALF = {k:.2e}...")
        model = CompartmentalModel(k_half=k)
        model.run()
        
        # Extract data for plotting
        # We want Infected (Acute + Subclinical) over time
        days = [d['day'] for d in model.sir_history]
        infected = [d['ACUTE'] + d['SUBCLINICAL'] for d in model.sir_history]
        
        results[k] = {
            'days': days,
            'infected': infected
        }
        
    return results

def visualize_k_half_sweep(results):
    fig = go.Figure()
    
    for k, data in results.items():
        fig.add_trace(go.Scatter(
            x=data['days'],
            y=data['infected'],
            mode='lines',
            name=f"K_HALF={k:.2e}"
        ))
        
    fig.update_layout(
        title="Impact of K_HALF on Infection Stability",
        xaxis_title="Day",
        yaxis_title="Infected Agents (Acute + Subclinical)",
        hovermode="x unified",
        height=800
    )
    
    output_file = "k_half_sweep.html"
    fig.write_html(output_file)
    print(f"Saved visualization to {output_file}")

if __name__ == "__main__":
    results = run_k_half_sweep()
    visualize_k_half_sweep(results)
