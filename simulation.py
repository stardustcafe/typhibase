import numpy as np
import time
from model import MALE, FEMALE# Import gender constants
from tqdm import tqdm # Optional: for a progress bar
import json # For saving population history
from initialparaandconst import PYRAMID_AGE_BINS, PYRAMID_AGE_LABELS, DISEASE_STATES, VACCINATED, INITIAL_POPULATION, SIMULATION_YEARS

from reporting_config import DAILY_ENVIRONMENT_VARIABLES, YEARLY_SUMMARY_VARIABLES

class Simulation:
    def __init__(self, model):
        self.model = model
        self.population_history = [] # Initialize list to store yearly age distributions
        self.sir_history = [] # Initialize list to store daily SIR counts
        self.environment_history = [] # Initialize list to store daily environmental contagion

    def run(self, duration_years):
        """
        Runs the simulation for a specified number of years.
        """
        print("Initializing population...")
        self.model.initialize_population()
        print(f"Initial population: {np.sum(self.model.is_alive)}")

        duration_days = duration_years * 365
        print(f"Running simulation for {duration_years} years ({duration_days} days)...")

        # The first call to a numba-jitted function includes a one-time compilation cost.
        # We can do a "warm-up" run to get this out of the way before the main loop.
        print("Compiling JIT function (one-time cost)...")
        start_time = time.time()
        # Perform a dummy step to trigger JIT compilation if population is empty
        if np.sum(self.model.is_alive) == 0:
            self.model.add_agents(1) # Add a temporary agent for warm-up
        self.model.step(0) # Pass a dummy day
        if np.sum(self.model.is_alive) == 1 and self.model.age_days[-1] == 0: # Remove temporary agent if added for warm-up
            self.model.is_alive = self.model.is_alive[:-1]
            self.model.age_days = self.model.age_days[:-1]
        end_time = time.time()
        print(f"JIT compilation took: {end_time - start_time:.4f} seconds.")
        
        # Record initial state (Year 0) with a correctly structured dictionary
        initial_aggregates = {var: 0 for var in YEARLY_SUMMARY_VARIABLES}
        initial_aggregates.update({
            'newborn_males': 0, 'newborn_females': 0,
            'male_deaths': 0, 'female_deaths': 0,
            'disease_male_deaths': 0, 'disease_female_deaths': 0
        })
        self._record_population_snapshot(0, initial_aggregates)


        current_day = 0
        # Run the main simulation loop by year
        for year in tqdm(range(1, duration_years + 1), desc="Simulating Years"):
            # --- Annual Vaccination Campaign ---
            self.model.vaccinate(year)
            self.model.num_new_infections=0
            # Initialize yearly aggregate counters dynamically
            yearly_aggregates = {var: 0 for var in YEARLY_SUMMARY_VARIABLES}
            yearly_aggregates.update({
                'newborn_males': 0, 'newborn_females': 0,
                'male_deaths': 0, 'female_deaths': 0
            })
            
            for day in range(365):
                current_day += 1
                daily_results = self.model.step(current_day)
                
                # Aggregate yearly totals
                for key in yearly_aggregates:
                    if key in daily_results:
                        yearly_aggregates[key] += daily_results[key]

                # Record daily disease state data dynamically
                daily_record = {'day': current_day}
                for i, state_name in DISEASE_STATES.items():
                    daily_record[state_name] = int(daily_results['state_counts'][i])
                
                # Add YLL if present
                if 'yll' in daily_results:
                    daily_record['yll'] = float(daily_results['yll'])
                
                self.sir_history.append(daily_record)
                
                # Record daily environmental data
                env_record = {'day': current_day}
                for var in DAILY_ENVIRONMENT_VARIABLES:
                    if var in daily_results:
                        env_record[var] = daily_results[var]
                self.environment_history.append(env_record)

            
            # Log statistics and record snapshot at the end of each year
            total_births = yearly_aggregates['newborn_males'] + yearly_aggregates['newborn_females']
            total_deaths = yearly_aggregates['male_deaths'] + yearly_aggregates['female_deaths'] + yearly_aggregates.get('disease_male_deaths', 0) + yearly_aggregates.get('disease_female_deaths', 0)
            print(f"\nYear {year}: Population = {np.sum(self.model.is_alive)}, Births = {total_births}, Deaths = {total_deaths}")
            self._record_population_snapshot(year, yearly_aggregates)

        # Get the final count of living agents
        final_population = np.sum(self.model.is_alive)
        print(f"\nSimulation finished.")
        print(f"Final population: {final_population}")
        fname=f"{SIMULATION_YEARS}_{INITIAL_POPULATION}_{self.model.vaccine_campaign_name}"
        # Save the population history to a JSON file for demographic visualization
        with open(f'{fname}_population_history.json', 'w') as f: 
            json.dump(self.population_history, f, indent=4)
        print("Population history saved to 'population_history.json'")

        # Save the SIR history to a JSON file for disease visualization
        with open(f'{fname}_sir_history.json', 'w') as f:
            json.dump(self.sir_history, f, indent=4)
        print("SIR history saved to 'sir_history.json'")

        # Save the environment history to a JSON file for visualization
        with open(f'{fname}_environment_history.json', 'w') as f:
            json.dump(self.environment_history, f, indent=4)
        print("Environment history saved to 'environment_history.json'")
        with open('latest_simulation_name.txt', 'w') as f:
            f.write(fname)

    def _record_population_snapshot(self, year, yearly_aggregates):
        """Records the current age distribution of the alive population."""
        alive_mask = self.model.is_alive
        alive_ages_days = self.model.age_days[alive_mask]
        alive_genders = self.model.gender[alive_mask]
        alive_ages_years = alive_ages_days // 365

        # Create masks for males and females
        male_mask = (alive_genders == MALE)
        female_mask = (alive_genders == FEMALE)

        # Use np.histogram to bin ages for each gender
        male_hist, _ = np.histogram(alive_ages_years[male_mask], bins=PYRAMID_AGE_BINS)
        female_hist, _ = np.histogram(alive_ages_years[female_mask], bins=PYRAMID_AGE_BINS)
        vaccinated_count = np.sum(self.model.disease_state[alive_mask] == VACCINATED)
        
        # Store the distribution
        snapshot = {
            'year': year,
            'male_age_counts': male_hist.tolist(),
            'female_age_counts': female_hist.tolist(),
            'vaccinated_count': int(vaccinated_count)
        }
        # Add all aggregated yearly values, converting to standard Python int
        for key, value in yearly_aggregates.items():
            snapshot[key] = int(value)
            
        self.population_history.append(snapshot)