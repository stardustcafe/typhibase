import numpy as np
import json
import math
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
    SEASONALITY_MIN_MULTIPLIER, SEASONALITY_MAX_DAY, SEASONALITY_RAMP_DURATION,
    ACUTE_MORTALITY_RATE, Vaccine, VAX_CAMPAIGN_NAME,
    INITIAL_POPULATION, SIMULATION_YEARS, MALE_BIRTH_RATE, FEMALE_BIRTH_RATE,
    PYRAMID_AGE_BINS
)

# --- Helper Functions for Parameter Aggregation ---

def calculate_weighted_average_duration(duration_under_30, duration_over_30):
    """Calculates the weighted average duration based on age distribution."""
    prob_under_30 = 0
    prob_over_30 = 0
    
    for age_range, prob in AGE_DISTRIBUTION.items():
        min_age, max_age = age_range
        # Simplified overlap logic
        if max_age < 30:
            prob_under_30 += prob
        elif min_age >= 30:
            prob_over_30 += prob
        else:
            # Split the bin
            range_len = max_age - min_age + 1
            under_30_part = (30 - min_age) / range_len
            prob_under_30 += prob * under_30_part
            prob_over_30 += prob * (1 - under_30_part)
            
    # Normalize (just in case)
    total = prob_under_30 + prob_over_30
    if total > 0:
        prob_under_30 /= total
        prob_over_30 /= total

    return (duration_under_30[0] * prob_under_30) + (duration_over_30[0] * prob_over_30)

def calculate_weighted_chronic_prob():
    """Calculates the weighted average probability of becoming chronic."""
    # This is complex because it depends on gender and age bins.
    # We'll approximate by iterating through age distribution and mapping to chronic bins.
    
    weighted_prob = 0
    total_weight = 0

    # Assume 50/50 gender split for this calculation
    
    for age_range, prob in AGE_DISTRIBUTION.items():
        min_age, max_age = age_range
        mid_age = (min_age + max_age) / 2
        
        # Find the bin index for this age
        bin_idx = np.searchsorted(CHRONIC_PROB_AGE_BINS, mid_age)
        
        male_prob = PROB_CHRONIC_MALE[bin_idx]
        female_prob = PROB_CHRONIC_FEMALE[bin_idx]
        
        avg_prob_for_age = (male_prob + female_prob) / 2
        
        weighted_prob += avg_prob_for_age * prob
        total_weight += prob
        
    return weighted_prob / total_weight if total_weight > 0 else 0

def calculate_weighted_death_rate():
    """Calculates weighted average daily death rate."""
    weighted_rate = 0
    total_weight = 0
    
    # Iterate through death rate bins (which are different for M/F and different from AGE_DISTRIBUTION)
    # Actually, it's easier to iterate through AGE_DISTRIBUTION and look up death rates.
    
    for age_range, prob in AGE_DISTRIBUTION.items():
        min_age, max_age = age_range
        mid_age = (min_age + max_age) / 2
        
        # Male Rate
        male_rate = 0
        for (d_min, d_max), rate in MALE_DEATH_RATES.items():
            if d_min <= mid_age <= d_max:
                male_rate = rate
                break
        
        # Female Rate
        female_rate = 0
        for (d_min, d_max), rate in FEMALE_DEATH_RATES.items():
            if d_min <= mid_age <= d_max:
                female_rate = rate
                break
                
        avg_rate = (male_rate + female_rate) / 2
        weighted_rate += avg_rate * prob
        total_weight += prob
        
    return weighted_rate / total_weight if total_weight > 0 else 0


# --- Calculated Parameters ---
AVG_PREPATENT_DURATION = PREPATENT_DURATION[0]
AVG_ACUTE_DURATION = calculate_weighted_average_duration(ACUTE_DURATION_UNDER_30, ACUTE_DURATION_OVER_30)
AVG_SUBCLINICAL_DURATION = calculate_weighted_average_duration(SUBCLINICAL_DURATION_UNDER_30, SUBCLINICAL_DURATION_OVER_30)
AVG_RECOVERY_DURATION = RECOVERY_DURATION[0]
AVG_MATERNAL_IMMUNITY_DURATION = MATERNAL_IMMUNITY_DURATION
AVG_VACCINE_DURATION = Vaccine.duration[0]

AVG_CHRONIC_PROB_BASE = calculate_weighted_chronic_prob()
AVG_DEATH_RATE_DAILY = calculate_weighted_death_rate()

# Rates (1/Duration)
RATE_MATERNAL_LOSS = 1.0 / AVG_MATERNAL_IMMUNITY_DURATION
RATE_PREPATENT_EXIT = 1.0 / AVG_PREPATENT_DURATION
RATE_ACUTE_EXIT = 1.0 / AVG_ACUTE_DURATION
RATE_SUBCLINICAL_EXIT = 1.0 / AVG_SUBCLINICAL_DURATION
RATE_RECOVERY_LOSS = 1.0 / AVG_RECOVERY_DURATION
RATE_VACCINE_LOSS = 1.0 / AVG_VACCINE_DURATION

# Transition Probabilities
PROB_P_TO_A = PROB_ACUTE_AFTER_PREPATENT
PROB_P_TO_U = 1.0 - PROB_ACUTE_AFTER_PREPATENT

PROB_A_TO_C = AVG_CHRONIC_PROB_BASE * PROB_CHRONIC_AFTER_ACUTE
PROB_A_TO_R = 1.0 - PROB_A_TO_C

PROB_U_TO_C = AVG_CHRONIC_PROB_BASE * PROB_CHRONIC_AFTER_SUBCLINICAL
PROB_U_TO_R = 1.0 - PROB_U_TO_C

# --- Compartmental Model Class ---

class CompartmentalModel:
    def __init__(self, base_transmission_risk=None, k_half=None):
        self.population = INITIAL_POPULATION
        self.time_step = 1.0 # 1 day
        
        # Allow overriding transmission risk for tuning
        self.base_transmission_risk = base_transmission_risk if base_transmission_risk is not None else BASE_TRANSMISSION_RISK
        self.k_half = k_half if k_half is not None else K_HALF
        
        # State Variables (Number of people)
        # S: Susceptible, M: Maternally Immune, P: Prepatent, A: Acute, U: Subclinical, C: Chronic, R: Recovered, V: Vaccinated
        
        # Initialize based on standard start
        self.state = {
            'S': self.population - INITIAL_INFECTED_COUNT,
            'M': 0.0,
            'P': float(INITIAL_INFECTED_COUNT), # Seed infection here
            'A': 0.0,
            'U': 0.0,
            'C': 0.0,
            'R': 0.0,
            'V': 0.0,
            'CumInf': 0.0, # Cumulative Infections
            'CumAcute': 0.0 # Cumulative Acute Cases
        }
        
        # Environmental Variable
        self.environmental_contagion = 0.0
        
        # History
        self.sir_history = []
        self.environment_history = []
        self.population_history = [] # Will store dummy/aggregate data to match format
        
        self.vaccine_campaign_name = VAX_CAMPAIGN_NAME
        if Vaccine.is_enabled:
             self.vaccine_campaign_name=f"VAX_{Vaccine.target_group_min_age}_{Vaccine.target_group_max_age}"

    def get_seasonality_multiplier(self, day):
        """Calculates the seasonality multiplier for the given day."""
        day_of_year = (day - 1) % 365
        ramp_up_start = SEASONALITY_MAX_DAY - SEASONALITY_RAMP_DURATION
        ramp_up_end = SEASONALITY_MAX_DAY
        ramp_down_start = SEASONALITY_MAX_DAY + 45
        ramp_down_end = ramp_down_start + SEASONALITY_RAMP_DURATION
        
        # Use mean values instead of random for ODE stability
        seasonality_min = SEASONALITY_MIN_MULTIPLIER
        seasonality_peak = 0.98 # Mean of 0.97 and 0.99
        
        multiplier = seasonality_min
        
        if ramp_up_start <= day_of_year < ramp_up_end:
            multiplier = seasonality_min + (seasonality_peak - seasonality_min) * ((day_of_year - ramp_up_start) / SEASONALITY_RAMP_DURATION)
        elif ramp_up_end <= day_of_year < ramp_down_start:
            multiplier = seasonality_peak
        elif ramp_down_start <= day_of_year < ramp_down_end:
            multiplier = seasonality_peak - (seasonality_peak - seasonality_min) * ((day_of_year - ramp_down_start) / SEASONALITY_RAMP_DURATION)
            
        return multiplier

    def compute_derivatives(self, t, state):
        """Computes time derivatives for the state variables."""
        S = state['S']
        M = state['M']
        P = state['P']
        A = state['A']
        U = state['U']
        C = state['C']
        R = state['R']
        V = state['V']
        
        total_pop = S + M + P + A + U + C + R + V
        
        # --- Infection Pressure ---
        num_shedding = P + A + U + C 
        num_shedding *= 0.8 # ABM shedding factor
        
        infection_pressure = 0.0
        new_contagion_inc = 0.0
        num_environmentally_shedding = 0.0
        hazard_factor = 0.0
        seasonality_multiplier = 1.0
        
        # Note: Environmental contagion is treated as a state variable in RK4 if we want full ODE
        # But here it's stored separately in self.environmental_contagion.
        # For RK4 consistency, we should ideally include it in state, but for now we'll keep it semi-coupled
        # or just use the current value (approximation). 
        # Better: Pass environment as a parameter or assume it changes slowly within a step?
        # Let's use the current self.environmental_contagion for the derivative calculation.
        # This makes it a hybrid system, but acceptable for this level of upgrade.
        
        if ENABLE_ENVIRONMENTAL_TRANSMISSION:
            # We use the current environment state for pressure
            seasonality_multiplier = self.get_seasonality_multiplier(t)
            hazard_factor = self.environmental_contagion / (self.k_half + self.environmental_contagion) if self.environmental_contagion > 0 else 0
            infection_pressure = self.base_transmission_risk * hazard_factor * seasonality_multiplier
        else:
            if total_pop > 0:
                infection_pressure = (num_shedding / total_pop) * TRANSMISSION_RATE

        # --- Flows ---
        daily_births = (total_pop * 0.5) * FEMALE_BIRTH_RATE
        
        # Deaths
        deaths_S = S * AVG_DEATH_RATE_DAILY
        deaths_M = M * AVG_DEATH_RATE_DAILY
        deaths_P = P * AVG_DEATH_RATE_DAILY
        deaths_A = A * AVG_DEATH_RATE_DAILY
        deaths_U = U * AVG_DEATH_RATE_DAILY
        deaths_C = C * AVG_DEATH_RATE_DAILY
        deaths_R = R * AVG_DEATH_RATE_DAILY
        deaths_V = V * AVG_DEATH_RATE_DAILY
        disease_deaths_A = A * (ACUTE_MORTALITY_RATE / 365.0)
        
        # Transitions
        flow_M_to_S = M * RATE_MATERNAL_LOSS
        flow_S_to_P = S * infection_pressure
        flow_V_to_P = V * (0.05 * infection_pressure * 0.1)
        
        flow_P_out = P * RATE_PREPATENT_EXIT
        flow_P_to_A = flow_P_out * PROB_P_TO_A
        flow_P_to_U = flow_P_out * PROB_P_TO_U
        
        flow_A_out = A * RATE_ACUTE_EXIT
        flow_A_to_C = flow_A_out * PROB_A_TO_C
        flow_A_to_R = flow_A_out * PROB_A_TO_R
        
        flow_U_out = U * RATE_SUBCLINICAL_EXIT
        flow_U_to_C = flow_U_out * PROB_U_TO_C
        flow_U_to_R = flow_U_out * PROB_U_TO_R
        
        flow_R_to_S = R * RATE_RECOVERY_LOSS
        flow_V_to_S = V * RATE_VACCINE_LOSS
        
        # Derivatives
        dS = flow_M_to_S + flow_R_to_S + flow_V_to_S - flow_S_to_P - deaths_S
        dM = daily_births - flow_M_to_S - deaths_M
        dP = flow_S_to_P + flow_V_to_P - flow_P_out - deaths_P
        dA = flow_P_to_A - flow_A_out - deaths_A - disease_deaths_A
        dU = flow_P_to_U - flow_U_out - deaths_U
        dC = flow_A_to_C + flow_U_to_C - deaths_C
        dR = flow_A_to_R + flow_U_to_R - flow_R_to_S - deaths_R
        dV = -flow_V_to_S - flow_V_to_P - deaths_V
        
        dCumInf = flow_S_to_P + flow_V_to_P
        dCumAcute = flow_P_to_A
        
        return {
            'S': dS, 'M': dM, 'P': dP, 'A': dA, 'U': dU, 'C': dC, 'R': dR, 'V': dV,
            'CumInf': dCumInf, 'CumAcute': dCumAcute
        }

    def rk4_step(self, day):
        """Performs one step of RK4 integration."""
        dt = self.time_step
        y = self.state.copy()
        
        # k1
        k1 = self.compute_derivatives(day, y)
        
        # k2
        y2 = {k: y[k] + 0.5 * dt * k1[k] for k in y}
        k2 = self.compute_derivatives(day + 0.5 * dt, y2)
        
        # k3
        y3 = {k: y[k] + 0.5 * dt * k2[k] for k in y}
        k3 = self.compute_derivatives(day + 0.5 * dt, y3)
        
        # k4
        y4 = {k: y[k] + dt * k3[k] for k in y}
        k4 = self.compute_derivatives(day + dt, y4)
        
        # Update state
        for k in self.state:
            self.state[k] += (dt / 6.0) * (k1[k] + 2*k2[k] + 2*k3[k] + k4[k])
            if self.state[k] < 0: self.state[k] = 0 # Clamp to 0
            
    def step(self, day):
        # Store old cumulative values to calculate daily flows
        old_cum_inf = self.state['CumInf']
        old_cum_acute = self.state['CumAcute']
        
        # Update Population State via RK4
        self.rk4_step(day)
        
        # Calculate daily flows
        daily_new_infections = self.state['CumInf'] - old_cum_inf
        daily_acute_cases = self.state['CumAcute'] - old_cum_acute
        
        # --- Update Environment (Separate Euler Step) ---
        # We keep this separate or simple for now as it was in the original
        # Re-calculate derived vars for reporting
        S = self.state['S']
        P = self.state['P']
        A = self.state['A']
        U = self.state['U']
        C = self.state['C']
        
        num_shedding = (P + A + U + C) * 0.8
        
        infection_pressure = 0.0
        new_contagion_inc = 0.0
        num_environmentally_shedding = 0.0
        hazard_factor = 0.0
        seasonality_multiplier = 1.0
        
        if ENABLE_ENVIRONMENTAL_TRANSMISSION:
            new_contagion_inc = self.environmental_contagion * np.exp(-1.0 * ENVIRONMENTAL_CONTAGION_DECAY_RATE)
            num_environmentally_shedding = num_shedding * ENVIRONMENTAL_SHEDDING_RATE
            
            # Update Environment
            self.environmental_contagion = new_contagion_inc + num_environmentally_shedding
            
            seasonality_multiplier = self.get_seasonality_multiplier(day)
            hazard_factor = self.environmental_contagion / (self.k_half + self.environmental_contagion)
            infection_pressure = self.base_transmission_risk * hazard_factor * seasonality_multiplier
        else:
             total_pop = sum(self.state.values()) - self.state['CumInf'] - self.state['CumAcute'] # Approximate active pop
             # Actually sum(values) includes Cums, so subtract them
             active_pop = S + self.state['M'] + P + A + U + C + self.state['R'] + self.state['V']
             if active_pop > 0:
                infection_pressure = (num_shedding / active_pop) * TRANSMISSION_RATE
            
        return {
            'day': day,
            'SUSCEPTIBLE': int(self.state['S']),
            'MATERNALLY_IMMUNE': int(self.state['M']),
            'PREPATENT': int(self.state['P']),
            'ACUTE': int(self.state['A']),
            'SUBCLINICAL': int(self.state['U']),
            'CHRONIC': int(self.state['C']),
            'RECOVERED': int(self.state['R']),
            'VACCINATED': int(self.state['V']),
            'contagion': self.environmental_contagion,
            'infection_pressure': infection_pressure,
            'seasonality_multiplier': seasonality_multiplier,
            'hazard_factor': hazard_factor,
            'new_contagion_inc': new_contagion_inc,
            'num_environmentally_shedding': num_environmentally_shedding,
            'num_shedding_agents': num_shedding,
            'yearly_new_infections': daily_new_infections,
            'num_acute_cases_yearly': daily_acute_cases
        }

    def vaccinate(self, year):
        """Vaccination logic."""
        if not Vaccine.is_enabled or year < Vaccine.start_year:
            return
            
        # Target group: 9 months to 60 months.
        # In ODE, we don't have age structure.
        # We have to approximate the fraction of population in this age group.
        # And assume they are S, R, or P (but mostly S).
        
        # Calculate fraction of population in target age
        target_prob = 0
        target_min_years = Vaccine.target_group_min_age / 12.0
        target_max_years = Vaccine.target_group_max_age / 12.0
        
        for age_range, prob in AGE_DISTRIBUTION.items():
            min_age, max_age = age_range
            # Simple overlap
            overlap_min = max(min_age, target_min_years)
            overlap_max = min(max_age, target_max_years)
            
            if overlap_max > overlap_min:
                range_len = max_age - min_age + 1
                overlap_len = overlap_max - overlap_min
                target_prob += prob * (overlap_len / range_len)
                
        # Total eligible population (approximate)
        # Exclude cumulative counters
        total_pop = self.state['S'] + self.state['M'] + self.state['P'] + self.state['A'] + self.state['U'] + self.state['C'] + self.state['R'] + self.state['V']
        eligible_pop = total_pop * target_prob
        
        # Apply coverage
        num_to_vaccinate = eligible_pop * Vaccine.coverage
        
        print(f"Year {year}: Vaccinating approx {int(num_to_vaccinate)} people.")
        
        # Move from S, R, P, M to V proportionally?
        # ABM vaccinates S, R, P.
        # Let's take from S mostly.
        
        # Limit by available S
        if self.state['S'] > num_to_vaccinate:
            self.state['S'] -= num_to_vaccinate
            self.state['V'] += num_to_vaccinate
        else:
            # Take all S and some R
            remainder = num_to_vaccinate - self.state['S']
            self.state['V'] += self.state['S']
            self.state['S'] = 0
            if self.state['R'] > remainder:
                self.state['R'] -= remainder
                self.state['V'] += remainder
            else:
                self.state['V'] += self.state['R']
                self.state['R'] = 0

    def run(self):
        print(f"Running Compartmental Model for {SIMULATION_YEARS} years...")
        
        current_day = 0
        
        # Initial snapshot
        self.population_history.append({
            'year': 0,
            'male_age_counts': [0]*len(PYRAMID_AGE_BINS), # Dummy
            'female_age_counts': [0]*len(PYRAMID_AGE_BINS), # Dummy
            'vaccinated_count': 0
        })
        
        for year in range(1, SIMULATION_YEARS + 1):
            self.vaccinate(year)
            
            yearly_new_infections = 0
            yearly_acute_cases = 0
            
            for day in range(365):
                current_day += 1
                res = self.step(current_day)
                
                # Record SIR
                self.sir_history.append({
                    'day': current_day,
                    'SUSCEPTIBLE': res['SUSCEPTIBLE'],
                    'MATERNALLY_IMMUNE': res['MATERNALLY_IMMUNE'],
                    'PREPATENT': res['PREPATENT'],
                    'ACUTE': res['ACUTE'],
                    'SUBCLINICAL': res['SUBCLINICAL'],
                    'CHRONIC': res['CHRONIC'],
                    'RECOVERED': res['RECOVERED'],
                    'VACCINATED': res['VACCINATED']
                })
                
                # Record Environment
                self.environment_history.append({
                    'day': current_day,
                    'contagion': res['contagion'],
                    'infection_pressure': res['infection_pressure'],
                    'seasonality_multiplier': res['seasonality_multiplier'],
                    'hazard_factor': res['hazard_factor'],
                    'new_contagion_inc': res['new_contagion_inc'],
                    'num_environmentally_shedding': res['num_environmentally_shedding'],
                    'num_shedding_agents': res['num_shedding_agents'],
                    'yearly_new_infections': res['yearly_new_infections'], # Daily value
                    'num_acute_cases_yearly': res['num_acute_cases_yearly'] # Daily value
                })
                
                yearly_new_infections += res['yearly_new_infections']
                yearly_acute_cases += res['num_acute_cases_yearly']
                
            total_pop_current = self.state['S'] + self.state['M'] + self.state['P'] + self.state['A'] + self.state['U'] + self.state['C'] + self.state['R'] + self.state['V']
            print(f"Year {year}: Total Pop: {int(total_pop_current)}, New Infections: {int(yearly_new_infections)}")
            
            # Record Population Snapshot (Dummy for compatibility)
            self.population_history.append({
                'year': year,
                'male_age_counts': [0]*len(PYRAMID_AGE_BINS),
                'female_age_counts': [0]*len(PYRAMID_AGE_BINS),
                'vaccinated_count': int(self.state['V']),
                'yearly_new_infections': int(yearly_new_infections),
                'num_acute_cases_yearly': int(yearly_acute_cases)
            })

        # Save Files
        fname = f"{SIMULATION_YEARS}_{INITIAL_POPULATION}_{self.vaccine_campaign_name}_ODE"
        print(fname)
        with open(f'{fname}_population_history.json', 'w') as f:
            json.dump(self.population_history, f, indent=4)
            
        with open(f'{fname}_sir_history.json', 'w') as f:
            json.dump(self.sir_history, f, indent=4)
            
        with open(f'{fname}_environment_history.json', 'w') as f:
            json.dump(self.environment_history, f, indent=4)
            
        print("Simulation Complete. Files saved.")

if __name__ == "__main__":
    model = CompartmentalModel()
    model.run()
