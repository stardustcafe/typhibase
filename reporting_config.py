# reporting_config.py

"""
This file acts as a central registry for variables to be tracked and reported
during the simulation. By defining variables here, they will be automatically
calculated in the model, collected in the simulation runner, and plotted in
the visualization scripts.
"""

# --- Daily Environmental Variables ---
# These are tracked every day and saved to 'environment_history.json'.
# They are plotted by visualize_environment.py.
DAILY_ENVIRONMENT_VARIABLES = [
    "contagion",
    "infection_pressure",
    "seasonality_multiplier",
    "new_contagion_inc",
    "num_environmentally_shedding"
]

# --- Yearly Summary Variables ---
# These are aggregated over a year and saved to 'population_history.json'.
# They are plotted by visualize_summary.py.
YEARLY_SUMMARY_VARIABLES = [
    "yearly_new_infections",
    "num_acute_cases_yearly",
    "disease_male_deaths",
    "disease_female_deaths"
]