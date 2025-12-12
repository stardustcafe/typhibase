from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import json
import plotly
import threading
import visualize
import visualize_summary
import visualize_sir
import visualize_environment
import visualize_vaccination
import initialparaandconst as const

app = Flask(__name__)

# Global status tracking for the background simulation
simulation_status = {"running": False, "error": None}

@app.route('/', methods=['GET'])
def index():
    # Default values from constants for the form
    defaults = {
        "initial_population": const.INITIAL_POPULATION,
        "simulation_years": const.SIMULATION_YEARS,
        "female_birth_rate": const.FEMALE_BIRTH_RATE * 365.0,  # back to annual for UI
        "male_birth_rate": const.MALE_BIRTH_RATE * 365.0,  # back to annual for UI
        "transmission_rate": const.TRANSMISSION_RATE,
        "initial_infected_count": const.INITIAL_INFECTED_COUNT,
        "enable_environmental": const.ENABLE_ENVIRONMENTAL_TRANSMISSION,
        "base_transmission_risk": const.BASE_TRANSMISSION_RISK,
        "environmental_shdding_rate": getattr(const, "ENVIRONMENTAL_SHEDDING_RATE", None),
        "environmental_decay_rate": getattr(const, "ENVIRONMENTAL_CONTAGION_DECAY_RATE", None),
        "seasonality_min_multiplier": getattr(const, "SEASONALITY_MIN_MULTIPLIER", None),
        "seasonality_max_day": getattr(const, "SEASONALITY_MAX_DAY", None),
        "seasonality_ramp_duration": getattr(const, "SEASONALITY_RAMP_DURATION", None),
        "vaccine_start_year": const.Vaccine.start_year,
        "vaccine_coverage": const.Vaccine.coverage,
        "vaccine_efficacy": const.Vaccine.efficacy,
        "vaccine_enabled": const.Vaccine.is_enabled,
        "vaccine_target_min_age": const.Vaccine.target_group_min_age,
        "vaccine_target_max_age": const.Vaccine.target_group_max_age,
        "vaccine_duration_mean": const.Vaccine.duration[0] if hasattr(const.Vaccine, "duration") else None,
        "vaccine_duration_std": const.Vaccine.duration[1] if hasattr(const.Vaccine, "duration") else None,
    }

    # Load existing figures if a previous run succeeded
    graphs = {}
    try:
        graphs["summary"] = json.dumps(visualize_summary.get_figure(), cls=plotly.utils.PlotlyJSONEncoder)
        graphs["pyramid"] = json.dumps(visualize.get_figure(), cls=plotly.utils.PlotlyJSONEncoder)
        graphs["sir"] = json.dumps(visualize_sir.get_figure(), cls=plotly.utils.PlotlyJSONEncoder)
        graphs["environment"] = json.dumps(visualize_environment.get_figure(), cls=plotly.utils.PlotlyJSONEncoder)
        graphs["vaccination"] = json.dumps(visualize_vaccination.get_figure(), cls=plotly.utils.PlotlyJSONEncoder)
    except Exception as e:
        print(f"Could not load graphs: {e}")
        graphs = None

    return render_template(
        "index.html",
        defaults=defaults,
        graphs=graphs,
        simulation_running=simulation_status["running"],
    )

def _run_simulation():
    """Background worker that runs the simulation and updates status."""
    global simulation_status
    simulation_status = {"running": True, "error": None}
    print("Starting simulation in background thread...")
    try:
        subprocess.run(["python", "runmain.py"], check=True)
        simulation_status = {"running": False, "error": None}
        print("Simulation completed successfully.")
    except subprocess.CalledProcessError as e:
        simulation_status = {"running": False, "error": str(e)}
        print(f"Simulation failed: {e}")
    except Exception as e:
        simulation_status = {"running": False, "error": str(e)}
        print(f"Unexpected error during simulation: {e}")

@app.route('/run', methods=['POST'])
def run_simulation():
    # Prevent starting another simulation while one is already running
    if simulation_status["running"]:
        return "Simulation already in progress.", 409

    # Extract form data
    initial_population = int(request.form.get('initial_population', 100000))
    simulation_years = int(request.form.get('simulation_years', 20))
    female_birth_rate = float(request.form.get('female_birth_rate', 0.028)) / 365.0
    transmission_rate = float(request.form.get('transmission_rate', 0.1))
    initial_infected_count = int(request.form.get('initial_infected_count', 3200))
    enable_environmental = 'enable_environmental' in request.form
    base_transmission_risk = float(request.form.get('base_transmission_risk', 0.005))
    vaccine_enabled = 'vaccine_enabled' in request.form
    vaccine_start_year = int(request.form.get('vaccine_start_year', 1))
    vaccine_coverage = float(request.form.get('vaccine_coverage', 0.8))
    vaccine_efficacy = float(request.form.get('vaccine_efficacy', 0.9))

    # Write config_override.py based on user input
    override_content = f"""
# Auto-generated configuration override
INITIAL_POPULATION = {initial_population}
SIMULATION_YEARS = {simulation_years}
FEMALE_BIRTH_RATE = {female_birth_rate}
TRANSMISSION_RATE = {transmission_rate}
INITIAL_INFECTED_COUNT = {initial_infected_count}

ENABLE_ENVIRONMENTAL_TRANSMISSION = {enable_environmental}
BASE_TRANSMISSION_RISK = {base_transmission_risk}

class VaccineOverride:
    is_enabled = {vaccine_enabled}
    start_year = {vaccine_start_year}
    target_group_min_age = 9
    target_group_max_age = 60
    coverage = {vaccine_coverage}
    efficacy = {vaccine_efficacy}
    duration = (5 * 365, 60)

Vaccine = VaccineOverride
"""
    with open('config_override.py', 'w') as f:
        f.write(override_content)

    # Launch simulation in a daemon thread so Flask can continue serving requests
    thread = threading.Thread(target=_run_simulation, daemon=True)
    thread.start()

    return redirect(url_for('loading'))

@app.route('/loading')
def loading():
    return render_template('loading.html')

@app.route('/status')
def status():
    return jsonify(simulation_status)

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
