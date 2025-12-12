import os
import shutil
import subprocess
import re
import json
import plotly.graph_objects as go
import time

# Configuration
# Configuration
SCENARIOS = {
    "Baseline": {
        "BASE_TRANSMISSION_RISK_MULTIPLIER": 1.0,
        "INITIAL_INFECTED_COUNT": 300, # Default for 10k pop
        "ENVIRONMENTAL_SHEDDING_RATE": 1000
    },
    "High_Base_Risk": {
        "BASE_TRANSMISSION_RISK_MULTIPLIER": 10.0,
        "INITIAL_INFECTED_COUNT": 300,
        "ENVIRONMENTAL_SHEDDING_RATE": 1000
    },
    "Low_Base_Risk": {
        "BASE_TRANSMISSION_RISK_MULTIPLIER": 0.1,
        "INITIAL_INFECTED_COUNT": 300,
        "ENVIRONMENTAL_SHEDDING_RATE": 1000
    },
    "High_Initial_Infected": {
        "BASE_TRANSMISSION_RISK_MULTIPLIER": 1.0,
        "INITIAL_INFECTED_COUNT": 1000,
        "ENVIRONMENTAL_SHEDDING_RATE": 1000
    },
    "Low_Initial_Infected": {
        "BASE_TRANSMISSION_RISK_MULTIPLIER": 1.0,
        "INITIAL_INFECTED_COUNT": 50,
        "ENVIRONMENTAL_SHEDDING_RATE": 1000
    },
    "High_Shedding_Rate": {
        "BASE_TRANSMISSION_RISK_MULTIPLIER": 1.0,
        "INITIAL_INFECTED_COUNT": 300,
        "ENVIRONMENTAL_SHEDDING_RATE": 5000
    },
    "Low_Shedding_Rate": {
        "BASE_TRANSMISSION_RISK_MULTIPLIER": 1.0,
        "INITIAL_INFECTED_COUNT": 300,
        "ENVIRONMENTAL_SHEDDING_RATE": 200
    }
}

CONSTANTS_FILE = "initialparaandconst.py"
BACKUP_FILE = "initialparaandconst.py.bak"
POPULATION = 10000
YEARS = 4

def backup_config():
    if os.path.exists(CONSTANTS_FILE):
        shutil.copy(CONSTANTS_FILE, BACKUP_FILE)
        print(f"Backed up {CONSTANTS_FILE} to {BACKUP_FILE}")

def restore_config():
    if os.path.exists(BACKUP_FILE):
        shutil.copy(BACKUP_FILE, CONSTANTS_FILE)
        os.remove(BACKUP_FILE)
        print(f"Restored {CONSTANTS_FILE} from {BACKUP_FILE}")

def update_config(params):
    with open(BACKUP_FILE, 'r') as f:
        content = f.read()

    # Update Population and Years
    content = re.sub(r"INITIAL_POPULATION = \d+", f"INITIAL_POPULATION = {POPULATION}", content)
    content = re.sub(r"SIMULATION_YEARS = \d+", f"SIMULATION_YEARS = {YEARS}", content)

    # Update Initial Infected Count
    if "INITIAL_INFECTED_COUNT" in params:
        # Replace the calculation with a fixed number
        content = re.sub(r"INITIAL_INFECTED_COUNT = .*?#", f"INITIAL_INFECTED_COUNT = {params['INITIAL_INFECTED_COUNT']} #", content)

    # Update Environmental Shedding Rate
    if "ENVIRONMENTAL_SHEDDING_RATE" in params:
        content = re.sub(r"ENVIRONMENTAL_SHEDDING_RATE = \d+", f"ENVIRONMENTAL_SHEDDING_RATE = {params['ENVIRONMENTAL_SHEDDING_RATE']}", content)

    # Update Base Transmission Risk
    # We multiply the existing calculation by the multiplier
    if "BASE_TRANSMISSION_RISK_MULTIPLIER" in params:
        multiplier = params["BASE_TRANSMISSION_RISK_MULTIPLIER"]
        # Regex to find the line and append the multiplier
        # Looking for: BASE_TRANSMISSION_RISK = INITIAL_INFECTED_COUNT/INITIAL_POPULATION /365.0# Base risk factor per day
        content = re.sub(
            r"(BASE_TRANSMISSION_RISK = .*?)(# Base risk factor per day)", 
            f"\\1 * {multiplier} \\2", 
            content
        )

    with open(CONSTANTS_FILE, 'w') as f:
        f.write(content)

def run_simulation(scenario_name):
    print(f"Running scenario: {scenario_name}")
    try:
        subprocess.run(["python", "runmain.py"], check=True)
        
        # Rename output files
        with open("latest_simulation_name.txt", "r") as f:
            sim_name = f.read().strip()
        
        # We are interested in SIR history for visualization
        src_sir = f"{sim_name}_sir_history.json"
        dst_sir = f"sensitivity_{scenario_name}_sir_history.json"
        
        if os.path.exists(src_sir):
            # Check if destination exists and remove it to avoid permission errors
            if os.path.exists(dst_sir):
                os.remove(dst_sir)
            shutil.move(src_sir, dst_sir)
            print(f"Saved output to {dst_sir}")
            return dst_sir
        else:
            print(f"Error: Output file {src_sir} not found.")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Simulation failed for {scenario_name}: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def visualize_results(results):
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("Sensitivity to Base Transmission Risk", "Sensitivity to Initial Infected Population", "Sensitivity to Shedding Rate"),
        vertical_spacing=0.1
    )

    for scenario_name, filepath in results.items():
        if not filepath or not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        days = [d['day'] for d in data]
        # Calculate Total Infected (Acute + Subclinical)
        infected = [d.get('ACUTE', 0) + d.get('SUBCLINICAL', 0) for d in data]
        
        # Get parameter values for legend
        params = SCENARIOS.get(scenario_name, {})
        legend_text = scenario_name
        if params:
            relevant_params = {}
            if "Base_Risk" in scenario_name:
                relevant_params["Base Risk"] = params.get("BASE_TRANSMISSION_RISK_MULTIPLIER")
            elif "Initial_Infected" in scenario_name:
                relevant_params["Initial Infected"] = params.get("INITIAL_INFECTED_COUNT")
            elif "Shedding_Rate" in scenario_name:
                relevant_params["Shedding Rate"] = params.get("ENVIRONMENTAL_SHEDDING_RATE")
            
            if relevant_params:
                param_str = ", ".join([f"{k}={v}" for k, v in relevant_params.items()])
                legend_text = f"{scenario_name} ({param_str})"

        # Determine which subplot to add to
        row = 1
        if "Initial_Infected" in scenario_name:
            row = 2
        elif "Shedding_Rate" in scenario_name:
            row = 3
        elif scenario_name == "Baseline":
            # Add Baseline to all for comparison
            fig.add_trace(go.Scatter(
                x=days, y=infected, mode='lines', name=f"{legend_text} (Ref)",
                line=dict(dash='dash', color='gray'), showlegend=False
            ), row=2, col=1)
            fig.add_trace(go.Scatter(
                x=days, y=infected, mode='lines', name=f"{legend_text} (Ref)",
                line=dict(dash='dash', color='gray'), showlegend=False
            ), row=3, col=1)
        
        fig.add_trace(go.Scatter(
            x=days, 
            y=infected, 
            mode='lines', 
            name=legend_text
        ), row=row, col=1)

    fig.update_layout(
        title=f"Sensitivity Analysis (N={POPULATION})",
        height=1000,
        hovermode="x unified",
        font=dict(size=18)
    )
    
    fig.update_xaxes(title_text="Day", row=1, col=1)
    fig.update_xaxes(title_text="Day", row=2, col=1)
    fig.update_xaxes(title_text="Day", row=3, col=1)
    fig.update_yaxes(title_text="Infected Agents", row=1, col=1)
    fig.update_yaxes(title_text="Infected Agents", row=2, col=1)
    fig.update_yaxes(title_text="Infected Agents", row=3, col=1)
    
    fig.show()

def main():
    backup_config()
    results = {}
    
    try:
        for name, params in SCENARIOS.items():
            update_config(params)
            output_file = run_simulation(name)
            if output_file:
                results[name] = output_file
                
    finally:
        restore_config()
        
    if results:
        visualize_results(results)

if __name__ == "__main__":
    main()
