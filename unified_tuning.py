import os
import shutil
import subprocess
import re
import json
import itertools
import matplotlib.pyplot as plt
import numpy as np
import time

# Configuration
CONSTANTS_FILE = "initialparaandconst.py"
BACKUP_FILE = "initialparaandconst.py.bak"
POPULATION = 10000
YEARS = 15

# Parameter Grid
PARAM_GRID = {
    "BASE_TRANSMISSION_RISK": [1e-4, 1e-3, 1e-2],
    "ENVIRONMENTAL_SHEDDING_RATE": [100, 1000, 10000],
    "K_HALF": [1e7, 1e8, 1e9]
}

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

    # Update Parameters
    for key, value in params.items():
        # Regex to match 'KEY = VALUE' with potential whitespace and comments
        # We assume the values are numbers (float or int)
        pattern = rf"{key}\s*=\s*[\d\.eE+-]+"
        replacement = f"{key} = {value}"
        content = re.sub(pattern, replacement, content)

    with open(CONSTANTS_FILE, 'w') as f:
        f.write(content)

def run_simulation(params):
    print(f"Running simulation with params: {params}")
    try:
        subprocess.run(["python", "runmain.py"], check=True)
        
        # Get output filename
        with open("latest_simulation_name.txt", "r") as f:
            sim_name = f.read().strip()
        
        # Load SIR history
        sir_file = f"{sim_name}_sir_history.json"
        
        if os.path.exists(sir_file):
            with open(sir_file, 'r') as f:
                data = json.load(f)
            return data
        else:
            print(f"Error: Output file {sir_file} not found.")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Simulation failed: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def visualize_results(results):
    # We have 3 parameters. We can create a grid of plots.
    # Let's fix one parameter (e.g., K_HALF) for the rows/cols and maybe create multiple figures?
    # Or use a FacetGrid style approach.
    
    # Let's group by K_HALF
    k_values = sorted(list(set(p['K_HALF'] for p in results.keys())))
    
    for k in k_values:
        fig, axes = plt.subplots(len(PARAM_GRID['ENVIRONMENTAL_SHEDDING_RATE']), 
                                 len(PARAM_GRID['BASE_TRANSMISSION_RISK']), 
                                 figsize=(15, 10), sharex=True, sharey=True)
        
        fig.suptitle(f"Infected Population (K_HALF = {k:.0e})", fontsize=16)
        
        shedding_rates = sorted(PARAM_GRID['ENVIRONMENTAL_SHEDDING_RATE'])
        risks = sorted(PARAM_GRID['BASE_TRANSMISSION_RISK'])
        
        for i, shedding in enumerate(shedding_rates):
            for j, risk in enumerate(risks):
                ax = axes[i, j]
                
                # Find the result for this combination
                key = (risk, shedding, k)
                # We need to reconstruct the key from the loop variables to match how we stored it
                # Actually, let's store results with a tuple key: (risk, shedding, k)
                
                # Filter results
                data = None
                for params, history in results.items():
                    if (params['BASE_TRANSMISSION_RISK'] == risk and 
                        params['ENVIRONMENTAL_SHEDDING_RATE'] == shedding and 
                        params['K_HALF'] == k):
                        data = history
                        break
                
                if data:
                    days = [d['day'] for d in data]
                    infected = [d.get('ACUTE', 0) + d.get('SUBCLINICAL', 0) for d in data]
                    ax.plot(days, infected, label='Infected')
                    ax.set_title(f"Risk={risk:.0e}, Shedding={shedding}")
                    ax.grid(True)
                
                if i == len(shedding_rates) - 1:
                    ax.set_xlabel("Day")
                if j == 0:
                    ax.set_ylabel("Infected Count")
                    
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        filename = f"tuning_k_{k:.0e}.png"
        plt.savefig(filename)
        print(f"Saved plot to {filename}")
        plt.close()

def main():
    backup_config()
    results = {}
    
    # Generate all combinations
    keys = PARAM_GRID.keys()
    values = PARAM_GRID.values()
    combinations = list(itertools.product(*values))
    
    print(f"Total simulations to run: {len(combinations)}")
    
    try:
        for combo in combinations:
            params = dict(zip(keys, combo))
            update_config(params)
            
            data = run_simulation(params)
            if data:
                # Store result with params as key (frozen as tuple for dict key? No, just store as list of tuples)
                # Actually, let's just store it in a way we can retrieve.
                # We can't use dict as key.
                # Let's use a custom class or just iterate.
                # For simplicity, let's use the params dict as part of the value or something.
                # Or just use the tuple of values as the key, since we know the order of keys.
                results[tuple(zip(keys, combo))] = data # Key is ((k1, v1), (k2, v2), ...)
                
                # Re-structuring for easier access in visualization
                # Let's make a new results dict where key is a frozenset of items or just the params dict?
                # No, let's just use the params dict in the loop in visualize.
                
    finally:
        restore_config()
        
    # Re-structure results for visualization
    # We want to pass {params_dict: data}
    formatted_results = {}
    for key_tuple, data in results.items():
        params = dict(key_tuple)
        formatted_results[frozenset(params.items())] = data # Frozenset is hashable
        
    # Actually, let's just pass a list of (params, data) tuples or something.
    # Or just keep it simple.
    # visualize_results expects a dict where we can iterate and check params.
    
    # Let's pass {params_tuple: data} and unpack in visualize
    # But visualize needs to know which param is which.
    # So let's pass a list of {'params': p, 'data': d}
    
    final_results = {}
    for key_tuple, data in results.items():
        params = dict(key_tuple)
        # We can't use dict as key.
        # Let's use a custom key object or just filter.
        # Let's just pass the list of results to visualize
        pass

    # Redefine visualize to take the list
    visualize_results_list = []
    for key_tuple, data in results.items():
        visualize_results_list.append({'params': dict(key_tuple), 'data': data})
        
    visualize_results_v2(visualize_results_list)

def visualize_results_v2(results_list):
    k_values = sorted(list(set(r['params']['K_HALF'] for r in results_list)))
    
    for k in k_values:
        fig, axes = plt.subplots(len(PARAM_GRID['ENVIRONMENTAL_SHEDDING_RATE']), 
                                 len(PARAM_GRID['BASE_TRANSMISSION_RISK']), 
                                 figsize=(15, 10), sharex=True, sharey=True)
        
        fig.suptitle(f"Infected Population (K_HALF = {k:.0e})", fontsize=16)
        
        shedding_rates = sorted(PARAM_GRID['ENVIRONMENTAL_SHEDDING_RATE'])
        risks = sorted(PARAM_GRID['BASE_TRANSMISSION_RISK'])
        
        for i, shedding in enumerate(shedding_rates):
            for j, risk in enumerate(risks):
                ax = axes[i, j]
                
                # Find data
                data = None
                for item in results_list:
                    p = item['params']
                    if (p['BASE_TRANSMISSION_RISK'] == risk and 
                        p['ENVIRONMENTAL_SHEDDING_RATE'] == shedding and 
                        p['K_HALF'] == k):
                        data = item['data']
                        break
                
                if data:
                    days = [d['day'] for d in data]
                    infected = [d.get('ACUTE', 0) + d.get('SUBCLINICAL', 0) for d in data]
                    ax.plot(days, infected, color='tab:red')
                    ax.set_title(f"Risk={risk:.0e}, Shed={shedding}")
                    ax.grid(True, alpha=0.3)
                
                if i == len(shedding_rates) - 1:
                    ax.set_xlabel("Day")
                if j == 0:
                    ax.set_ylabel("Infected")
                    
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        filename = f"tuning_k_{k:.0e}.png"
        plt.savefig(filename)
        print(f"Saved plot to {filename}")
        plt.close()

if __name__ == "__main__":
    main()
