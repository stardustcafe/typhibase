from model import Model
from initialparaandconst import *
import numpy as np

def run_debug():
    print("Initializing model...")
    model = Model(initial_population=10000, male_birth_rate=MALE_BIRTH_RATE, female_birth_rate=FEMALE_BIRTH_RATE)
    model.initialize_population()
    
    print(f"Initial Contagion: {model.environmental_contagion}")
    print(f"Decay Rate: {ENVIRONMENTAL_CONTAGION_DECAY_RATE}")
    print(f"Shedding Rate: {ENVIRONMENTAL_SHEDDING_RATE}")
    
    for day in range(1, 101):
        (num_alive_females, newborn_male_count, newborn_female_count, male_deaths, female_deaths, 
         disease_male_deaths, disease_female_deaths, state_counts, 
         env_contagion, infection_pressure, seasonality, num_acute) = model.step(day)
        
        num_shedding = state_counts[PREPATENT] + state_counts[ACUTE] + state_counts[SUBCLINICAL] + state_counts[CHRONIC]
        
        if day % 10 == 0:
            print(f"Day {day}: Contagion={env_contagion:.4f}, Shedding={num_shedding}, Pressure={infection_pressure:.4f}")

if __name__ == "__main__":
    run_debug()
