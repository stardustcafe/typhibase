import numpy as np
import plotly.graph_objects as go
from compartmental_model import CompartmentalModel
from initialparaandconst import K_HALF
import os

def run_k_half_foi_sensitivity():
    # Define range of values to test (from tune_k_half.py)
    base_val = 3000000
    k_values = [base_val * 0.001, base_val * 0.01, base_val *0.1, base_val * 10, base_val * 10**2, base_val * 10**3]
    
    results = {}
    
    print(f"Starting sensitivity analysis for K_HALF vs Force of Infection...")
    print(f"Testing values: {k_values}")
    
    for k in k_values:
        print(f"Testing K_HALF = {k:.2e}...")
        model = CompartmentalModel(k_half=k)
        model.run()
        
        # Extract data for plotting
        # Force of Infection is 'infection_pressure' in environment_history
        # We need to access environment_history from the model
        days = [d['day'] for d in model.environment_history]
        foi = [d['infection_pressure'] for d in model.environment_history]
        
        results[k] = {
            'days': days,
            'foi': foi
        }
        
    return results

def visualize_k_half_foi(results):
    fig = go.Figure()
    
    for k, data in results.items():
        fig.add_trace(go.Scatter(
            x=data['days'],
            y=data['foi'],
            mode='lines',
            name=f"K_HALF={k:.2e}"
        ))
        
    fig.update_layout(
        title="Sensitivity of Force of Infection to K_HALF",
        xaxis_title="Day",
        yaxis_title="Force of Infection (Infection Pressure)",
        hovermode="x unified",
        height=800,
        yaxis_type="log" # Log scale might be useful if ranges are huge
    )
    
    output_file = "k_half_foi_sensitivity.html"
    fig.write_html(output_file)
    print(f"Saved visualization to {output_file}")

if __name__ == "__main__":
    results = run_k_half_foi_sensitivity()
    visualize_k_half_foi(results)
