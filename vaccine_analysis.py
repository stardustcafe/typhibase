import os
import shutil
import subprocess
import re
import json
import plotly.graph_objects as go
import time

# Configuration
SCENARIOS = {
    "No Vaccine": {
        "ENABLED": False
    },
    "9m-15y": {
        "ENABLED": True,
        "MIN_AGE": 9,
        "MAX_AGE": 15 * 12 # 15 years in months
    },
    "16m-15y": {
        "ENABLED": True,
        "MIN_AGE": 16,
        "MAX_AGE": 15 * 12 # 15 years in months
    }
}

CONSTANTS_FILE = "initialparaandconst.py"
BACKUP_FILE = "initialparaandconst.py.bak"
POPULATION = 100000
YEARS = 15

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

    # Update Vaccine Enabled Status
    if "ENABLED" in params:
        # Regex to match 'is_enabled = True' or 'is_enabled = False' with potential whitespace and comments
        content = re.sub(r"is_enabled\s*=\s*(True|False)", f"is_enabled = {params['ENABLED']}", content)

    # Update Vaccine Target Group
    if "MIN_AGE" in params:
        content = re.sub(r"    target_group_min_age = \d+", f"    target_group_min_age = {params['MIN_AGE']}", content)
    if "MAX_AGE" in params:
        content = re.sub(r"    target_group_max_age = \d+", f"    target_group_max_age = {params['MAX_AGE']}", content)

    with open(CONSTANTS_FILE, 'w') as f:
        f.write(content)
    
    # Debug: Check if is_enabled was updated
    match = re.search(r"is_enabled\s*=\s*(True|False)", content)
    if match:
        print(f"DEBUG: Updated {CONSTANTS_FILE}: is_enabled = {match.group(1)}")
    else:
        print("DEBUG: Could not find is_enabled in updated content")

def run_simulation(scenario_name):
    print(f"Running scenario: {scenario_name}")
    try:
        subprocess.run(["python", "runmain.py"], check=True)
        
        # Rename output files
        with open("latest_simulation_name.txt", "r") as f:
            sim_name = f.read().strip()
        
        # We are interested in SIR history for visualization
        src_sir = f"{sim_name}_sir_history.json"
        dst_sir = f"vaccine_{scenario_name.replace(' ', '_')}_sir_history.json"
        
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
        rows=2, cols=1,
        subplot_titles=("Infected Population Over Time", "Cost Analysis (DALYs)"),
        vertical_spacing=0.15,
        specs=[[{"type": "scatter"}], [{"type": "bar"}]]
    )
    
    daly_results = {}

    for scenario_name, filepath in results.items():
        if not filepath or not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        days = [d['day'] for d in data]
        # Calculate Total Infected (Acute + Subclinical)
        infected = [d.get('ACUTE', 0) + d.get('SUBCLINICAL', 0) for d in data]
        
        # Calculate DALYs
        # Disability Weights
        DW_ACUTE = 0.27       # GBD estimate for Typhoid Fever (Acute)
        DW_SUBCLINICAL = 0.01 # Estimate for mild malaise
        DW_CHRONIC = 0.05     # Estimate for carrier burden

        # Filter data for DALY calculation (Start from Year 2, i.e., Day > 730)
        daly_data = [d for d in data if d['day'] > 730]

        # Calculate Person-Days (using filtered data)
        person_days_acute = sum([d.get('ACUTE', 0) for d in daly_data])
        person_days_subclinical = sum([d.get('SUBCLINICAL', 0) for d in daly_data])
        person_days_chronic = sum([d.get('CHRONIC', 0) for d in daly_data])

        # Calculate YLD (Years Lived with Disability)
        yld_acute = (person_days_acute / 365.0) * DW_ACUTE
        yld_subclinical = (person_days_subclinical / 365.0) * DW_SUBCLINICAL
        yld_chronic = (person_days_chronic / 365.0) * DW_CHRONIC
        
        total_yld = yld_acute + yld_subclinical + yld_chronic
        
        # YLL = Sum(YLL from model) (using filtered data)
        total_yll = sum([d.get('yll', 0) for d in daly_data])
        
        total_daly = total_yld + total_yll
        daly_results[scenario_name] = total_daly

        print(f"\n--- DALY Breakdown for {scenario_name} (Years 2-{YEARS}) ---")
        print(f"  Person-Days: Acute={person_days_acute:,.0f}, Sub={person_days_subclinical:,.0f}, Chronic={person_days_chronic:,.0f}")
        print(f"  YLD: Acute={yld_acute:.2f}, Sub={yld_subclinical:.2f}, Chronic={yld_chronic:.2f} -> Total YLD={total_yld:.2f}")
        print(f"  YLL: {total_yll:.2f}")
        print(f"  Total DALY: {total_daly:.2f}")
        
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
        title=f"Vaccine Impact & Cost Analysis (N={POPULATION}, {YEARS} Years)",
        height=900,
        hovermode="x unified",
        font=dict(size=18)
    )
    
    fig.update_xaxes(title_text="Day", row=1, col=1)
    fig.update_yaxes(title_text="Infected Agents", row=1, col=1)
    
    fig.update_xaxes(title_text="Scenario", row=2, col=1)
    fig.update_yaxes(title_text="Total DALYs", row=2, col=1)
    
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
