import numpy as np
from initialparaandconst import (
    AGE_DISTRIBUTION,
    PREPATENT_DURATION,
    ACUTE_DURATION_UNDER_30, ACUTE_DURATION_OVER_30,
    SUBCLINICAL_DURATION_UNDER_30, SUBCLINICAL_DURATION_OVER_30,
    PROB_ACUTE_AFTER_PREPATENT,
    PROB_CHRONIC_MALE, PROB_CHRONIC_FEMALE, CHRONIC_PROB_AGE_BINS,
    PROB_CHRONIC_AFTER_ACUTE, PROB_CHRONIC_AFTER_SUBCLINICAL,
    ENVIRONMENTAL_SHEDDING_RATE, ENVIRONMENTAL_CONTAGION_DECAY_RATE,
    K_HALF, INITIAL_POPULATION, TRANSMISSION_RATE,
    ENABLE_ENVIRONMENTAL_TRANSMISSION, SEASONALITY_MIN_MULTIPLIER
)

def calculate_weighted_duration(duration_under_30, duration_over_30):
    """Calculates the weighted average duration based on age distribution."""
    prob_under_30 = 0.0
    prob_over_30 = 0.0
    
    for age_range, prob in AGE_DISTRIBUTION.items():
        # Simplified: if the range starts < 30, we count it as under 30 for this rough calc
        # A more precise way would be to split the range, but this is sufficient for R0 estimation
        if age_range[0] < 30:
            prob_under_30 += prob
        else:
            prob_over_30 += prob
            
    # Normalize in case they don't sum exactly to 1 (though they should)
    total_prob = prob_under_30 + prob_over_30
    prob_under_30 /= total_prob
    prob_over_30 /= total_prob
    
    avg_duration = (prob_under_30 * duration_under_30[0]) + (prob_over_30 * duration_over_30[0])
    return avg_duration

def get_chronic_prob_for_age(age_years, gender_probs):
    """Finds the chronic probability for a specific age."""
    # CHRONIC_PROB_AGE_BINS = [10, 20, 30, 40, 50, 60, np.inf]
    # np.searchsorted finds the index where age_years would be inserted
    idx = np.searchsorted(CHRONIC_PROB_AGE_BINS, age_years)
    # Clamp index to bounds of probability array
    idx = min(idx, len(gender_probs) - 1)
    return gender_probs[idx]

def calculate_weighted_chronic_prob():
    """Calculates the population-wide weighted average probability of becoming chronic."""
    weighted_prob_sum = 0.0
    
    for age_range, prob in AGE_DISTRIBUTION.items():
        # Use the midpoint of the age range to lookup the probability
        mid_age = (age_range[0] + age_range[1]) / 2
        
        # Average male and female probabilities (assuming 50/50 gender split)
        prob_male = get_chronic_prob_for_age(mid_age, PROB_CHRONIC_MALE)
        prob_female = get_chronic_prob_for_age(mid_age, PROB_CHRONIC_FEMALE)
        avg_prob_age = (prob_male + prob_female) / 2
        
        weighted_prob_sum += prob * avg_prob_age
        
    return weighted_prob_sum

def calculate_r0():
    print("--- Typhoid R0 Calculation ---")
    
    # 1. Calculate Expected Infectious Durations
    d_pre = PREPATENT_DURATION[0]
    d_acute = calculate_weighted_duration(ACUTE_DURATION_UNDER_30, ACUTE_DURATION_OVER_30)
    d_sub = calculate_weighted_duration(SUBCLINICAL_DURATION_UNDER_30, SUBCLINICAL_DURATION_OVER_30)
    
    # Chronic Duration: This is tricky. It's life expectancy - current age.
    # Let's assume an average remaining life expectancy for a chronic carrier.
    # If average age of infection is ~20, and life expectancy is 65, then duration is 45 years.
    # For a conservative estimate, let's use 20 years (7300 days).
    d_chronic = 20 * 365 
    
    print(f"Average Durations (Days):")
    print(f"  Prepatent: {d_pre:.2f}")
    print(f"  Acute:     {d_acute:.2f}")
    print(f"  Subclin:   {d_sub:.2f}")
    print(f"  Chronic:   {d_chronic:.2f} (Assumed 20 years)")

    # 2. Calculate Transition Probabilities
    p_acute = PROB_ACUTE_AFTER_PREPATENT
    p_sub = 1.0 - p_acute
    
    base_chronic_prob = calculate_weighted_chronic_prob()
    p_chronic_given_acute = PROB_CHRONIC_AFTER_ACUTE * base_chronic_prob
    p_chronic_given_sub = PROB_CHRONIC_AFTER_SUBCLINICAL * base_chronic_prob
    
    print(f"\nProbabilities:")
    print(f"  Acute: {p_acute:.2f}")
    print(f"  Subclinical: {p_sub:.2f}")
    print(f"  Base Chronic Prob: {base_chronic_prob:.4f}")
    print(f"  Chronic | Acute: {p_chronic_given_acute:.4f}")
    print(f"  Chronic | Subclin: {p_chronic_given_sub:.4f}")

    # 3. Calculate Total Expected Infectious Duration (D_total)
    # Path 1: Pre -> Acute -> (Chronic or Recovered)
    path_acute_duration = d_acute + (p_chronic_given_acute * d_chronic)
    
    # Path 2: Pre -> Subclinical -> (Chronic or Recovered)
    path_sub_duration = d_sub + (p_chronic_given_sub * d_chronic)
    
    d_total = d_pre + (p_acute * path_acute_duration) + (p_sub * path_sub_duration)
    
    print(f"\nTotal Expected Infectious Duration (D_total): {d_total:.2f} days")
    
    # 4. Calculate R0
    if ENABLE_ENVIRONMENTAL_TRANSMISSION:
        print("\n--- Environmental R0 ---")
        # R0_env = N * (lambda * D_total) / (delta * K_half) * Seasonality
        # Note: In the model, infection_pressure = hazard_factor * seasonality
        # hazard_factor = E / (K + E) approx E / K for small E
        # E_steady_state_for_one_person = (Shedding_Rate * D_total) / Decay_Rate (integrated over time)
        # Actually, it's simpler: Total Shedding Q = Shedding_Rate * D_total
        # Total Hazard Integral = Q / (Decay_Rate * K_half)
        # Expected Infections = Population * Total Hazard Integral
        
        lambda_shed = ENVIRONMENTAL_SHEDDING_RATE
        delta = ENVIRONMENTAL_CONTAGION_DECAY_RATE
        k_half = K_HALF
        N = INITIAL_POPULATION
        
        # Seasonality: Taking the average multiplier (approx 1.0 if peak is high enough, or min otherwise)
        # Let's use 1.0 as a baseline
        seasonality = 1.0 
        
        r0_env = N * (lambda_shed * d_total) / (delta * k_half) * seasonality
        
        print(f"Parameters:")
        print(f"  Population (N): {N}")
        print(f"  Shedding Rate: {lambda_shed}")
        print(f"  Decay Rate: {delta:.4f}")
        print(f"  K_half: {k_half}")
        print(f"  Seasonality: {seasonality}")
        print(f"\nCalculated R0 (Environmental): {r0_env:.4f}")
        
    else:
        print("\n--- Direct R0 ---")
        beta = TRANSMISSION_RATE
        r0_direct = beta * d_total
        print(f"Transmission Rate (beta): {beta}")
        print(f"Calculated R0 (Direct): {r0_direct:.4f}")

if __name__ == "__main__":
    calculate_r0()
