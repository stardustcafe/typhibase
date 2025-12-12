from model import Model
from simulation import Simulation
from initialparaandconst import (
    INITIAL_POPULATION, SIMULATION_YEARS, MALE_BIRTH_RATE, FEMALE_BIRTH_RATE
)

def main():
    # All parameters are now imported from the central constants file.
    model = Model(
        initial_population=INITIAL_POPULATION,
        male_birth_rate=MALE_BIRTH_RATE,
        female_birth_rate=FEMALE_BIRTH_RATE
    )

    sim = Simulation(model)
    sim.run(duration_years=SIMULATION_YEARS)

if __name__ == "__main__":
    main()