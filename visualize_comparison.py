import json
import plotly.graph_objects as go
import plotly.colors as pcolors
import sys
import os

def load_history(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {filepath} was not found.")
        return None

def visualize_comparison(file1, file2, label1="Run 1", label2="Run 2", normalize=False):
    """
    Compares two SIR history files and generates a Plotly line chart.
    """
    history1 = load_history(file1)
    history2 = load_history(file2)

    if not history1 or not history2:
        return

    # Get keys (assuming both have same keys)
    keys1 = [k for k in history1[0].keys() if k != 'day']
    
    days1 = [item['day'] for item in history1]
    days2 = [item['day'] for item in history2]
    
    colors = pcolors.qualitative.Dark24
    
    fig = go.Figure()

    for i, state in enumerate(keys1):
        color = colors[i % len(colors)]
        
        # Run 1
        counts1 = [item.get(state, 0) for item in history1]
        if normalize:
            totals1 = [sum(item.get(k, 0) for k in keys1) for item in history1]
            counts1 = [c / t if t > 0 else 0 for c, t in zip(counts1, totals1)]
            
        fig.add_trace(go.Scatter(
            x=days1, y=counts1, 
            mode='lines', 
            name=f"{state} ({label1})", 
            line=dict(color=color, width=2),
            legendgroup=state
        ))
        
        # Run 2
        counts2 = [item.get(state, 0) for item in history2]
        if normalize:
            totals2 = [sum(item.get(k, 0) for k in keys1) for item in history2]
            counts2 = [c / t if t > 0 else 0 for c, t in zip(counts2, totals2)]

        fig.add_trace(go.Scatter(
            x=days2, y=counts2, 
            mode='lines', 
            name=f"{state} ({label2})", 
            line=dict(color=color, width=2, dash='dash'),
            legendgroup=state
        ))

    yaxis_title = "Fraction of Population" if normalize else "Number of Agents"
    fig.update_layout(
        title=f"Comparison of Simulation Runs: {label1} vs {label2}",
        xaxis_title="Day",
        yaxis_title=yaxis_title,
        hovermode="x unified",
        font=dict(size=18)
    )

    fig.show()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compare two SIR history files.")
    parser.add_argument("file1", help="Path to the first history file")
    parser.add_argument("file2", help="Path to the second history file")
    parser.add_argument("label1", nargs='?', default="Run 1", help="Label for the first run")
    parser.add_argument("label2", nargs='?', default="Run 2", help="Label for the second run")
    parser.add_argument("--normalize", action="store_true", help="Normalize counts by total population")
    
    args = parser.parse_args()
    
    visualize_comparison(args.file1, args.file2, args.label1, args.label2, args.normalize)
