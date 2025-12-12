from Typhmesa.model import TyphoidModel
import numpy as np

def run_demographics():
    print("Initializing model...")
    model = TyphoidModel(N=10000)
    
    print(f"Initial Population: {model.schedule.get_agent_count()}")
    
    # Check initial age distribution
    ages = [a.age/365.0 for a in model.schedule.agents]
    print(f"Initial Mean Age: {np.mean(ages):.2f}")
    
    print("\nRunning simulation for 5 years...")
    for i in range(5 * 365):
        model.step()
        if i % 365 == 0:
            print(f"Year {i//365}: Population = {model.schedule.get_agent_count()}")
            
    print(f"\nFinal Population: {model.schedule.get_agent_count()}")
    final_ages = [a.age/365.0 for a in model.schedule.agents]
    print(f"Final Mean Age: {np.mean(final_ages):.2f}")

if __name__ == "__main__":
    run_demographics()
