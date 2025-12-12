import random
import numpy as np
from numba import jit , config
from icecream import ic
from initialparaandconst import (
    MALE, FEMALE, AGE_DISTRIBUTION, MALE_DEATH_RATES, FEMALE_DEATH_RATES,
    DISEASE_STATES, SUSCEPTIBLE, MATERNALLY_IMMUNE, PREPATENT, ACUTE, SUBCLINICAL,
    CHRONIC, RECOVERED, VACCINATED, INITIAL_INFECTED_COUNT, TRANSMISSION_RATE,
    MATERNAL_IMMUNITY_DURATION, PREPATENT_DURATION, ACUTE_DURATION_UNDER_30,
    ACUTE_DURATION_OVER_30, SUBCLINICAL_DURATION_UNDER_30,
    SUBCLINICAL_DURATION_OVER_30, RECOVERY_DURATION, PROB_ACUTE_AFTER_PREPATENT,
    PROB_CHRONIC_MALE, PROB_CHRONIC_FEMALE, CHRONIC_PROB_AGE_BINS,
    PROB_CHRONIC_AFTER_ACUTE, PROB_CHRONIC_AFTER_SUBCLINICAL,
    ENABLE_ENVIRONMENTAL_TRANSMISSION, ENVIRONMENTAL_SHEDDING_RATE,
    ENVIRONMENTAL_CONTAGION_DECAY_RATE, BASE_TRANSMISSION_RISK, K_HALF, 
    SEASONALITY_MIN_MULTIPLIER,
    SEASONALITY_MAX_DAY, SEASONALITY_RAMP_DURATION, ACUTE_MORTALITY_RATE, Vaccine, VAX_CAMPAIGN_NAME
)

# Pre-calculate daily death rates for faster lookup
DAILY_MALE_DEATH_RATES = np.array(
    list(MALE_DEATH_RATES.values())
)
MALE_DEATH_RATE_AGE_BINS = np.array([
    key[1] * 365 for key in MALE_DEATH_RATES.keys() # Convert years to days
])
DAILY_FEMALE_DEATH_RATES = np.array(
    list(FEMALE_DEATH_RATES.values())
)
FEMALE_DEATH_RATE_AGE_BINS = np.array([
    key[1] * 365 for key in FEMALE_DEATH_RATES.keys() # Convert years to days
])
  # Ensure JIT is enabled
@jit(nopython=True)
def _get_death_rate_for_age_numba(age_days, death_rate_age_bins, daily_death_rates):
    """
    Numba-optimized function to get the daily death rate for a given age.
    """
    # np.searchsorted finds the index where the age would be inserted to maintain order.
    # This is a fast way to find the correct age bin.
    bin_index = np.searchsorted(death_rate_age_bins, age_days)
    return daily_death_rates[bin_index]

@jit(nopython=True)
def _get_chronic_prob(age_years, gender, prob_bins, male_probs, female_probs):
    """Numba-optimized function to get the probability of becoming a chronic carrier."""
    bin_index = np.searchsorted(prob_bins, age_years)
    if gender == MALE:
        return male_probs[bin_index]
    else:
        return female_probs[bin_index]

@jit(nopython=True,cache=True)
def _daily_step_numba(
    is_alive, age_days, gender, disease_state, days_in_state, state_duration,
    current_day, environmental_contagion, male_birth_rate, female_birth_rate,
    male_death_rate_bins, daily_male_rates, female_death_rate_bins,
    daily_female_rates, num_states, env_decay_rate, env_shedding_rate,
    base_risk, k_half
):
    """
    A Numba-JIT compiled function to perform one daily step of the simulation.
    This function contains the performance-critical loops.

    Args:
        is_alive (np.ndarray): Boolean array indicating if agent at index is alive.
        age_days (np.ndarray): Integer array of agent ages in days.
        gender (np.ndarray): Integer array of agent genders.
        disease_state (np.ndarray): Integer array of agent disease status.
        days_in_state (np.ndarray): Integer array for days agent has been in the current state.
        state_duration (np.ndarray): Float array for the pre-determined duration of the current state.
        current_day (int): The current day of the simulation (1-indexed).
        environmental_contagion (float): The current level of contagion in the environment.
        male_birth_rate (float): The annual birth rate applied to the male population.
        female_birth_rate (float): The annual birth rate applied to the female population.
        male_death_rate_bins (np.ndarray): Age bins for male death rates.
        daily_male_rates (np.ndarray): Corresponding daily male death rates.
        female_death_rate_bins (np.ndarray): Age bins for female death rates.
        daily_female_rates (np.ndarray): Corresponding daily female death rates.
        num_states (int): The total number of disease states.
        env_decay_rate (float): Daily decay rate of environmental contagion.
        env_shedding_rate (float): Contagion units shed per infected person per day.
        base_risk (float): Base transmission risk from the environment.
        k_half (float): Half-saturation constant for the dose-response curve.

    Returns:
        Tuple: Gendered birth/death counts (background and disease), death mask, state counts, new contagion, infection pressure, and seasonality multiplier.
    """
    disease_death_flags = np.zeros_like(is_alive, dtype=np.bool_) # Flag for disease-specific deaths
    num_acute_cases_daily=0
    yll_today = 0.0
    
    # First, count total living and contagious to calculate infection pressure
    total_alive = 0
    num_alive_males = 0
    num_alive_females = 0
    num_shedding = 0

    for i in range(len(is_alive)):
        if is_alive[i]:
            total_alive += 1
            if gender[i] == MALE:
                num_alive_males += 1
            else:
                num_alive_females += 1
            # Contagion is shed by prepatent, acute, subclinical, and chronic carriers
            current_state = disease_state[i]
            if (current_state == PREPATENT or
                current_state == ACUTE or
                current_state == SUBCLINICAL or
                current_state == CHRONIC):
                if random.random()<0.8:
                    num_shedding += 1
    
    # Initialize daily counters
    male_deaths = 0
    female_deaths = 0
    disease_male_deaths = 0
    disease_female_deaths = 0
    deaths_today_mask = np.zeros_like(is_alive, dtype=np.bool_)
    # --- Calculate Force of Infection ---
    infection_pressure = base_risk
    new_environmental_contagion = 0.0
    seasonality_multiplier = 1.0 # Default for non-environmental model
    num_new_infections = 0
    if ENABLE_ENVIRONMENTAL_TRANSMISSION:
        # Environmental Model
        # 1. Calculate new contagion level for the day
        
        new_environmental_contagion_inc = (environmental_contagion * np.exp(-1.0*env_decay_rate)) 
        num_environmentally_shedding = (num_shedding * env_shedding_rate)
        new_environmental_contagion = new_environmental_contagion_inc + num_environmentally_shedding
        # 2. Calculate seasonality multiplier
        day_of_year = (current_day - 1) % 365
        ramp_up_start = SEASONALITY_MAX_DAY - SEASONALITY_RAMP_DURATION
        ramp_up_end = SEASONALITY_MAX_DAY
        ramp_down_start = SEASONALITY_MAX_DAY + 45
        ramp_down_end = ramp_down_start + SEASONALITY_RAMP_DURATION
        
        seasonality_multiplier_min=random.uniform(SEASONALITY_MIN_MULTIPLIER-0.02, SEASONALITY_MIN_MULTIPLIER+0.02) # Random min between 0.8 and 1.0
        seasonality_multiplier = seasonality_multiplier_min
        seasonality_peak = random.uniform(0.97, 0.99) # Random peak between 1.0 and 1.5
        
        if ramp_up_start <= day_of_year < ramp_up_end:
            seasonality_multiplier = seasonality_multiplier_min + (seasonality_peak - seasonality_multiplier_min) * ((day_of_year - ramp_up_start) / SEASONALITY_RAMP_DURATION)
        elif ramp_up_end <= day_of_year < ramp_down_start:
            seasonality_multiplier = seasonality_peak
        elif ramp_down_start <= day_of_year < ramp_down_end:
            seasonality_multiplier = seasonality_peak - (seasonality_peak - seasonality_multiplier_min) * ((day_of_year - ramp_down_start) / SEASONALITY_RAMP_DURATION)
        
        hazard_factor =  new_environmental_contagion/(k_half+new_environmental_contagion)
        # 3. Calculate final infection pressur
        infection_pressure =  base_risk*hazard_factor *seasonality_multiplier
    else:
        # Simple Person-to-Person Model
        if total_alive > 0:
            infection_pressure = (num_shedding / total_alive) * TRANSMISSION_RATE

    # Pre-calculate age bins for chronic probability
    chronic_prob_bins_years = np.array([10, 20, 30, 40, 50, 60, 150])
    acute_mortality_pday = ACUTE_MORTALITY_RATE/365.0

    for i in range(len(is_alive)):
        if is_alive[i]:
            # --- Mortality ---
            death_rate = _get_death_rate_for_age_numba(age_days[i], male_death_rate_bins if gender[i] == MALE else female_death_rate_bins, daily_male_rates if gender[i] == MALE else daily_female_rates)
            if random.random() < death_rate:
                # Background death
                deaths_today_mask[i] = True
                if gender[i] == MALE:
                    male_deaths += 1
                else:
                    female_deaths += 1
                continue # Agent is dead, skip to next agent

            # --- Disease-specific Mortality ---
            elif disease_state[i] == ACUTE:
                if random.random() < acute_mortality_pday:
                    # This is a disease-related death
                    deaths_today_mask[i] = True
                    if gender[i] == MALE:
                        disease_male_deaths += 1
                    else:
                        disease_female_deaths += 1
                    
                    # Calculate YLL (Standard Life Expectancy = 65)
                    age_years_at_death = age_days[i] / 365.0
                    yll_today += max(0.0, 65.0 - age_years_at_death)
                    
                    continue # Agent is dead, skip to next agent
            
            # If the agent survived, proceed with aging and disease state transitions
            age_days[i] += 1
            days_in_state[i] += 1
            current_state = disease_state[i]
            age_years = age_days[i] / 365.0
            if current_state == MATERNALLY_IMMUNE:
                 if days_in_state[i] >= MATERNAL_IMMUNITY_DURATION:
                     disease_state[i] = SUSCEPTIBLE
                     days_in_state[i] = 0
                
            elif current_state == SUSCEPTIBLE:
                 if random.random() < infection_pressure:
                     disease_state[i] = PREPATENT
                     days_in_state[i] = 0
                     state_duration[i] = random.gauss(PREPATENT_DURATION[0], PREPATENT_DURATION[1])
                     num_new_infections += 1

            elif current_state == VACCINATED:
                 if days_in_state[i] >= state_duration[i]:
                     disease_state[i] = SUSCEPTIBLE
                     days_in_state[i] = 0
                 #15% of the days someone vaccinated has chance of infection
                 if random.random() < 0.05:
                     if random.random() < (infection_pressure * (1.0 - 0.9)):
                        disease_state[i] = PREPATENT
                        days_in_state[i] = 0
                        state_duration[i] = random.gauss(PREPATENT_DURATION[0], PREPATENT_DURATION[1])

            elif current_state == PREPATENT:
                 if days_in_state[i] >= state_duration[i]:
                     if random.random() < PROB_ACUTE_AFTER_PREPATENT:
                         disease_state[i] = ACUTE
                         mean, std = ACUTE_DURATION_OVER_30 if age_years >= 30 else ACUTE_DURATION_UNDER_30
                         num_acute_cases_daily+=1
                     else:
                         disease_state[i] = SUBCLINICAL
                         mean, std = SUBCLINICAL_DURATION_OVER_30 if age_years >= 30 else SUBCLINICAL_DURATION_UNDER_30
                     days_in_state[i] = 0
                     state_duration[i] = random.gauss(mean, std)

            elif current_state == ACUTE:
                 if days_in_state[i] >= state_duration[i]:
                     prob_chronic_base = _get_chronic_prob(age_years, gender[i], chronic_prob_bins_years, PROB_CHRONIC_MALE, PROB_CHRONIC_FEMALE)
                     if random.random() < prob_chronic_base * PROB_CHRONIC_AFTER_ACUTE:
                         disease_state[i] = CHRONIC # Lifelong
                     else:
                         disease_state[i] = RECOVERED
                         state_duration[i] = random.gauss(RECOVERY_DURATION[0], RECOVERY_DURATION[1])
                     days_in_state[i] = 0

            elif current_state == SUBCLINICAL:
                 if days_in_state[i] >= state_duration[i]:
                     prob_chronic_base = _get_chronic_prob(age_years, gender[i], chronic_prob_bins_years, PROB_CHRONIC_MALE, PROB_CHRONIC_FEMALE)
                     if random.random() < prob_chronic_base * PROB_CHRONIC_AFTER_SUBCLINICAL:
                         disease_state[i] = CHRONIC # Lifelong
                     else:
                         disease_state[i] = RECOVERED
                         state_duration[i] = random.gauss(RECOVERY_DURATION[0], RECOVERY_DURATION[1])
                     days_in_state[i] = 0

            elif current_state == RECOVERED:
                 if days_in_state[i] >= state_duration[i]:
                     disease_state[i] = SUSCEPTIBLE
                     days_in_state[i] = 0

    # --- Births ---
    # Births are based on the female population only. Gender is assigned upon agent creation.
    female_births = int(num_alive_females * female_birth_rate * random.randint(80,120)/100)
    
    # Count all disease states for daily tracking
    state_counts = np.zeros(num_states, dtype=np.int32)
    for i in range(len(is_alive)):
        if is_alive[i] and not deaths_today_mask[i]: # Count only those who survive the day
            state_counts[disease_state[i]] += 1

    return female_births, male_deaths, female_deaths, disease_male_deaths, disease_female_deaths, deaths_today_mask, state_counts, new_environmental_contagion, infection_pressure, seasonality_multiplier,num_alive_females,num_acute_cases_daily,new_environmental_contagion_inc,num_environmentally_shedding,num_new_infections,num_shedding,hazard_factor, yll_today

class Model:
    def __init__(self, initial_population, male_birth_rate, female_birth_rate):
        self.initial_population = initial_population
        self.male_birth_rate = male_birth_rate
        self.female_birth_rate = female_birth_rate
        # Use NumPy arrays instead of a DataFrame for performance
        self.is_alive = np.empty(0, dtype=np.bool_)
        self.age_days = np.empty(0, dtype=np.int32)
        self.gender = np.empty(0, dtype=np.int8) # Add gender array (int8 is memory efficient)
        self.disease_state = np.empty(0, dtype=np.int8)
        self.days_in_state = np.empty(0, dtype=np.int32)
        self.state_duration = np.empty(0, dtype=np.float32)
        # Initialize environmental contagion to its approximate equilibrium value
        # to ensure a stable start for the simulation.
        # C_eq = (Initial Shedders * Shedding Rate) / Decay Rate
        #self.environmental_contagion = (INITIAL_INFECTED_COUNT * ENVIRONMENTAL_SHEDDING_RATE)
        self.environmental_contagion=0
        self.vaccine_campaign_name=VAX_CAMPAIGN_NAME
    def initialize_population(self):
        """Initializes the population with ages based on the defined age distribution."""
        ages = np.zeros(self.initial_population, dtype=np.int32)
        genders = np.zeros(self.initial_population, dtype=np.int8)
        for i in range(self.initial_population):
            age_group = self.get_random_age_group()
            age_years = random.randint(age_group[0], age_group[1])
            ages[i] = age_years * 365
            genders[i] = random.randint(MALE, FEMALE) # Assign gender randomly

        self.is_alive = np.ones(self.initial_population, dtype=np.bool_)
        self.age_days = ages
        self.gender = genders
        # Everyone starts as susceptible
        self.disease_state = np.full(self.initial_population, SUSCEPTIBLE, dtype=np.int8)
        self.days_in_state = np.zeros(self.initial_population, dtype=np.int32)
        self.state_duration = np.zeros(self.initial_population, dtype=np.float32)

        # Seed initial infections
        if self.initial_population > INITIAL_INFECTED_COUNT > 0:
            infected_indices = np.random.choice(self.initial_population, INITIAL_INFECTED_COUNT, replace=False)
            self.disease_state[infected_indices] = PREPATENT
            for i in infected_indices:
                self.days_in_state[i] = 0
                self.state_duration[i] = random.gauss(PREPATENT_DURATION[0], PREPATENT_DURATION[1])


    def get_random_age_group(self):
        """Selects a random age group based on the defined distribution probabilities."""
        rand_val = random.random()
        cumulative_prob = 0
        for age_range, prob in AGE_DISTRIBUTION.items():
            cumulative_prob += prob
            if rand_val <= cumulative_prob:
                return age_range
        # Fallback in case of floating point inaccuracies
        return max(AGE_DISTRIBUTION.keys(), key=lambda k: k[1])

    def add_agents(self, num_to_add, age_days=0):
        """Adds a batch of new agents to the population."""
        if num_to_add <= 0:
            return 0, 0

        new_ages = np.full(num_to_add, age_days, dtype=np.int32)
        new_alive = np.ones(num_to_add, dtype=np.bool_)
        # Assign gender randomly to newborns
        new_genders = np.random.choice([MALE, FEMALE], size=num_to_add,p=[0.52,0.48])
        newborn_male_count = np.sum(new_genders == MALE)
        newborn_female_count = num_to_add - newborn_male_count
        # Newborns are maternally immune
        new_disease_state = np.full(num_to_add, MATERNALLY_IMMUNE, dtype=np.int8)
        new_days_in_state = np.zeros(num_to_add, dtype=np.int32)
        new_state_duration = np.zeros(num_to_add, dtype=np.float32)

        self.is_alive = np.concatenate([self.is_alive, new_alive])
        self.age_days = np.concatenate([self.age_days, new_ages])
        self.gender = np.concatenate([self.gender, new_genders])
        self.disease_state = np.concatenate([self.disease_state, new_disease_state])
        self.days_in_state = np.concatenate([self.days_in_state, new_days_in_state])
        self.state_duration = np.concatenate([self.state_duration, new_state_duration])

        return newborn_male_count, newborn_female_count

    def vaccinate(self, current_year):
        """
        Vaccinates a portion of the susceptible population based on the Vaccine configuration.
        This campaign is run once per year.
        """
        if not Vaccine.is_enabled or current_year < Vaccine.start_year:
            self.vaccine_campaign_name="NOVAX"
            return
        self.vaccine_campaign_name=f"VAX_{Vaccine.target_group_min_age}_{Vaccine.target_group_max_age}"
        # Identify agents who are susceptible and within the target age group
        eligible_mask = (
            ((self.disease_state == SUSCEPTIBLE) | (self.disease_state == RECOVERED) | (self.disease_state == PREPATENT)) &
            (self.age_days >= Vaccine.target_group_min_age * 30) &
            (self.age_days < Vaccine.target_group_max_age * 30) &
            self.is_alive
        )
        eligible_indices = np.where(eligible_mask)[0]
        print(f"Year {current_year}: Vaccinating {len(eligible_indices)} eligible agents out of {np.sum(self.is_alive)} alive agents.")
        print(f'Average age of eligible agents: {np.mean(self.age_days[eligible_indices])/365:.2f} years')
        # Vaccinate a random portion based on coverage
        num_to_vaccinate = int(len(eligible_indices) * Vaccine.coverage)
        vaccination_indices = np.random.choice(eligible_indices, num_to_vaccinate, replace=False)
        print(f"Year {current_year}: Vaccinated {len(vaccination_indices)} agents.")
        self.disease_state[vaccination_indices] = VACCINATED
        self.days_in_state[vaccination_indices] = 0
        self.state_duration[vaccination_indices] = np.random.normal(Vaccine.duration[0], Vaccine.duration[1], size=len(vaccination_indices))

    def step(self, current_day):
        """
        Executes one daily step of the simulation by calling the JIT-compiled function.
        """
        # The first run of a JIT function has a compilation overhead.
        # Subsequent runs are much faster.
        num_states = len(DISEASE_STATES)
        (total_births, male_deaths, female_deaths, d_male_deaths, d_female_deaths, deaths_today_mask, state_counts, new_contagion, infection_pressure, seasonality_multiplier,num_alive_females,num_acute_cases_daily,new_contagion_inc,num_environmentally_shedding,num_new_infections,num_shedding_agents,hazard_factor, yll_today) = _daily_step_numba( # disease_death_flags is internal
            self.is_alive,
            self.age_days,
            self.gender,
            self.disease_state,
            self.days_in_state,
            self.state_duration,
            current_day,
            self.environmental_contagion,
            self.male_birth_rate,
            self.female_birth_rate,
            MALE_DEATH_RATE_AGE_BINS,
            DAILY_MALE_DEATH_RATES,
            FEMALE_DEATH_RATE_AGE_BINS,
            DAILY_FEMALE_DEATH_RATES,
            num_states,
            ENVIRONMENTAL_CONTAGION_DECAY_RATE,
            ENVIRONMENTAL_SHEDDING_RATE,
            BASE_TRANSMISSION_RISK,
            K_HALF
        )

        # Apply deaths
        self.is_alive[deaths_today_mask] = False

        # Apply births and get the gender counts of newborns
        newborn_male_count, newborn_female_count = self.add_agents(total_births, age_days=0)

        # Optional: Clean up dead agents periodically to free memory
        # This is a trade-off between memory usage and performance
        if np.sum(~self.is_alive) > len(self.is_alive) * 0.1: # e.g., if >10% are dead
            alive_mask = self.is_alive
            self.is_alive = self.is_alive[alive_mask]
            self.age_days = self.age_days[alive_mask]
            self.gender = self.gender[alive_mask]
            self.disease_state = self.disease_state[alive_mask]
            self.days_in_state = self.days_in_state[alive_mask]
            self.state_duration = self.state_duration[alive_mask]
        
        # Update the model's environmental contagion level
        self.environmental_contagion = new_contagion
        
        # Package results into a dictionary for clarity and extensibility
        results = {
            "num_alive_females": num_alive_females,
            "newborn_males": newborn_male_count,
            "newborn_females": newborn_female_count,
            "male_deaths": male_deaths,
            "female_deaths": female_deaths,
            "disease_male_deaths": d_male_deaths,
            "disease_female_deaths": d_female_deaths,
            "state_counts": state_counts,
            "contagion": self.environmental_contagion,
            "infection_pressure": infection_pressure,
            "seasonality_multiplier": seasonality_multiplier,
            "num_acute_cases_yearly": num_acute_cases_daily, # Note: This is a daily count
            "new_contagion_inc": new_contagion_inc,
            "num_environmentally_shedding": num_environmentally_shedding,
            "yearly_new_infections": num_new_infections, # Note: This is a daily count
            "num_shedding_agents": num_shedding_agents,
            "hazard_factor": hazard_factor,
            "yll": yll_today
        }
        if (current_day % 365) == 0 or current_day==1:
            print(f"Debug Results Day {current_day}: {results}")
        return results