import numpy as np

# --- AGENT CONSTANTS ---
MALE = 0
FEMALE = 1

# --- DISEASE MODEL CONSTANTS ---
# Explicit integer constants for use in Numba-compiled functions
SUSCEPTIBLE = 0
MATERNALLY_IMMUNE = 1
PREPATENT = 2
ACUTE = 3
SUBCLINICAL = 4
CHRONIC = 5
RECOVERED = 6
VACCINATED = 7

# Using a dictionary allows for dynamic visualization and logging
DISEASE_STATES = {
    SUSCEPTIBLE: "SUSCEPTIBLE",
    MATERNALLY_IMMUNE: "MATERNALLY_IMMUNE",
    PREPATENT: "PREPATENT",
    ACUTE: "ACUTE",
    SUBCLINICAL: "SUBCLINICAL",
    CHRONIC: "CHRONIC",
    RECOVERED: "RECOVERED",
    VACCINATED: "VACCINATED"
}

# --- SIMULATION PARAMETERS ---
INITIAL_POPULATION = 10000000 # Default test population
SIMULATION_YEARS = 20 # Default simulation duration

# --- DEMOGRAPHIC PARAMETERS ---

# Daily Birth Rates (per person per day)
MALE_BIRTH_RATE = 0.0 / 365.0 # Births are attributed to the female population
FEMALE_BIRTH_RATE = 0.028 / 365.0 # Annual rate of 2.8% converted to daily

# Simplified age distribution for a developing country
AGE_DISTRIBUTION = {
    # (min_age_years, max_age_years): probability
    (0, 4):     7974/100000,
    (5, 9):     8326/100000,
    (10, 14):   8757/100000,
    (15, 19):   8918/100000,
    (20, 24):   9014/100000,
    (25, 29):   8596/100000,
    (30, 34):   8190/100000,
    (35, 39):   7644/100000,
    (40, 44):   6754/100000,
    (45, 49):   5883/100000,
    (50, 54):   5097/100000,
    (55, 59):   4331/100000,
    (60, 64):   3595/100000,
    (65, 69):   2827/100000,
    (70, 74):   1946/100000,
    (75, 79):   1109/100000,
    (80, 100):  1039/100000,
}

# Age-specific daily death rates (per person per day)
MALE_DEATH_RATES = {
    (0, 4): (5.75 / 1000) / 365.0,
    (5, 14): (0.4 / 1000) / 365.0,
    (15, 24): (0.74 / 1000) / 365.0,
    (25, 69): (6.12 / 1000) / 365.0,
    (70, 150): (19.5 * 1.5 / 1000) / 365.0,
}

FEMALE_DEATH_RATES = {
    (0, 4): (5.75 * 1.04 / 1000) / 365.0,
    (5, 14): (0.4 * 1.1 / 1000) / 365.0,
    (15, 24): (0.74 * 1.05 / 1000) / 365.0,
    (25, 69): (6.12 / 1000) / 365.0,
    (70, 150): (19.5 / 1000) / 365.0,
}

# --- DISEASE MODEL PARAMETERS ---
INITIAL_INFECTED_COUNT = int(3000/ 100000 * INITIAL_POPULATION )# Initial number of infected agents
TRANSMISSION_RATE = 0.0001 # Probability of transmission per contact, per day

# --- State Durations (in days, using Gaussian distribution: mean, std_dev) ---
MATERNAL_IMMUNITY_DURATION = 180 # Fixed 6 months

# Prepatent: High exposure = shorter duration. Simplified for now.
PREPATENT_DURATION = (10, 2) # Mean of 10 days, SD of 2

# Acute: Longer for older individuals
ACUTE_DURATION_UNDER_30 = (14, 3)
ACUTE_DURATION_OVER_30 = (21, 4)

# Subclinical: Longer for older individuals
SUBCLINICAL_DURATION_UNDER_30 = (28, 5)
SUBCLINICAL_DURATION_OVER_30 = (40, 8)

# Immunity duration after recovery
RECOVERY_DURATION = (180, 30) # Mean of 6 months, SD of 1 month

# --- Transition Probabilities ---
PROB_ACUTE_AFTER_PREPATENT = 0.2 # Probability of developing acute symptoms
# Probability of becoming a chronic carrier (dependent on age and gender)
# Bins: 0-9, 10-19, 20-29, 30-39, 40-49, 50-59, 60+
PROB_CHRONIC_MALE = np.array(  [0.01, 0.02, 0.03, 0.04, 0.05, 0.04, 0.03])*2
PROB_CHRONIC_FEMALE = np.array([0.01, 0.02, 0.04, 0.05, 0.06, 0.05, 0.04])*2
CHRONIC_PROB_AGE_BINS = np.array([10, 20, 30, 40, 50, 60, np.inf])

# Probability of progressing to chronic state (vs. recovering)
PROB_CHRONIC_AFTER_ACUTE = 0.05
PROB_CHRONIC_AFTER_SUBCLINICAL = 0.01

# --- Vaccination Parameters ---
class Vaccine:
    is_enabled = False      # Master switch for vaccination campaign
    start_year = 0         # Year the campaign begins

    # Agent attributes to target for vaccination
    target_group_min_age = 9  # months
    target_group_max_age = 12*15 # months

    # Coverage and efficacy
    coverage = 0.50        # 80% of the target group is vaccinated
    efficacy = 0.80        # 90% reduction in transmission risk

    # Duration of vaccine-induced immunity (mean, std_dev in days)
    duration = (5*365, 60) # Mean of 10 years, SD of 2 months

# Disease-related mortality (daily probability)
ACUTE_MORTALITY_RATE = 0.01 # 1% daily chance of death while in the ACUTE state
# In initialparaandconst.py, add this to the Environmental Transmission section
 # Contagion level for 50% of max hazard. TUNABLE PARAMETER.
# --- Environmental Transmission Parameters ---
ENABLE_ENVIRONMENTAL_TRANSMISSION = True # Master switch for the environmental model

# If environmental transmission is OFF, the model uses the simple person-to-person TRANSMISSION_RATE.
# If it is ON, the following parameters are used:

ENVIRONMENTAL_SHEDDING_RATE = 10000 # Contagion units shed per infected person per day
K_HALF = 5e7
ENVIRONMENTAL_CONTAGION_DECAY_RATE = 1.0/21.0 # Daily decay rate of contagion in the environment (10%)
BASE_TRANSMISSION_RISK = 0.0005 # Base risk factor per day

# Trapezoidal Seasonality Parameters (for environmental model)
# This creates a peak season for transmission.
SEASONALITY_MIN_MULTIPLIER = 0.93 # Multiplier during the low season
SEASONALITY_MAX_DAY = 255 # Day of the year with the highest transmission risk (peak of the season)
SEASONALITY_RAMP_DURATION = 45 # Days it takes to ramp up to peak and ramp down

# --- VISUALIZATION CONSTANTS ---
PYRAMID_AGE_BINS = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, np.inf]
PYRAMID_AGE_LABELS = [
    "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39",
    "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74",
    "75-79", "80-84", "85-89", "90-94", "95-99", "100+"
]

VAX_CAMPAIGN_NAME="NOVAX"