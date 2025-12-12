from model import Model
from initialparaandconst import INITIAL_POPULATION, MALE_BIRTH_RATE, FEMALE_BIRTH_RATE, INITIAL_INFECTED_COUNT, K_HALF, ENVIRONMENTAL_SHEDDING_RATE, DISEASE_STATES, PREPATENT

def investigate():
    print(f"INITIAL_POPULATION: {INITIAL_POPULATION}")
    print(f"INITIAL_INFECTED_COUNT: {INITIAL_INFECTED_COUNT}")
    print(f"K_HALF: {K_HALF}")
    print(f"ENVIRONMENTAL_SHEDDING_RATE: {ENVIRONMENTAL_SHEDDING_RATE}")

    print("Initializing Model...")
    model = Model(INITIAL_POPULATION, MALE_BIRTH_RATE, FEMALE_BIRTH_RATE)
    model.initialize_population()
    
    # Check initial infected count
    initial_infected = (model.disease_state == PREPATENT).sum()
    print(f"Initial agents in PREPATENT state: {initial_infected}")

    print("Running Step 1...")
    results = model.step(1)
    
    print("Step 1 Results:")
    print(f"Contagion: {results['contagion']}")
    print(f"Infection Pressure: {results['infection_pressure']}")
    print(f"New Infections: {results['yearly_new_infections']}")
    print(f"State Counts: {results['state_counts']}")
    
    prepatent_count = results['state_counts'][PREPATENT]
    print(f"PREPATENT Count after Step 1: {prepatent_count}")

if __name__ == "__main__":
    investigate()
