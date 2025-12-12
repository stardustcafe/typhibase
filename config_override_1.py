
# Auto-generated configuration override
INITIAL_POPULATION = 100000
SIMULATION_YEARS = 5
FEMALE_BIRTH_RATE = 7.671232876712329e-05
TRANSMISSION_RATE = 0.1
INITIAL_INFECTED_COUNT = 3200

ENABLE_ENVIRONMENTAL_TRANSMISSION = True
BASE_TRANSMISSION_RISK = 0.005

class VaccineOverride:
    is_enabled = True
    start_year = 1
    target_group_min_age = 9
    target_group_max_age = 60
    coverage = 0.8
    efficacy = 0.9
    duration = (5 * 365, 60)

Vaccine = VaccineOverride
