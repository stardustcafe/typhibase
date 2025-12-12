import numpy as np
import plotly.graph_objects as go
from compartmental_model import CompartmentalModel
from initialparaandconst import K_HALF
import os

def run_k_half_prepatent_sensitivity():
    # Define range of values to test
    # Current K_HALF is 3,000,000
    base_val = 3000000
    k_values = [base_val * 0.1, base_val * 0.5, base_val, base_val * 2, base_val * 5, base_val * 10]
    
    results = {}
    
    print(f"Starting sensitivity analysis for K_HALF vs PREPATENT...")
    print(f"Testing values: {k_values}")
    
    for k in k_values:
        print(f"Testing K_HALF = {k:.2e}...")
        model = CompartmentalModel(k_half=k)
        model.run()
        
        # Extract data for plotting
        days = [d['day'] for d in model.sir_history]
        prepatent = [d['PREPATENT'] for d in model.sir_history]
        
        results[k] = {
            'days': days,
            'prepatent': prepatent
        }
        
    return results

def visualize_k_half_prepatent(results):
    fig = go.Figure()
    
    for k, data in results.items():
        fig.add_trace(go.Scatter(
            x=data['days'],
            y=data['prepatent'],
            mode='lines',
            name=f"K_HALF={k:.2e}"
        ))
        
    fig.update_layout(
        title="Sensitivity of Prepatent Population to K_HALF",
        xaxis_title="Day",
        yaxis_title="Prepatent Agents",
        hovermode="x unified",
        height=800
    )
    
    output_file = "k_half_prepatent_sensitivity.html"
    fig.write_html(output_file)
    print(f"Saved visualization to {output_file}")

if __name__ == "__main__":
    results = run_k_half_prepatent_sensitivity()
    visualize_k_half_prepatent(results)
