import subprocess
import time
import requests
import sys
import json

def test_flask_parameters():
    print("Starting Flask app...")
    # Start Flask app in background as a module
    process = subprocess.Popen([sys.executable, "-m", "Typhmesa.app"], 
                               stdout=subprocess.PIPE, 
                               stderr=sys.stderr)
    
    try:
        # Wait for app to start
        time.sleep(5)
        
        base_url = "http://127.0.0.1:5000"
        
        # Test Reset with Parameters
        print("\nTesting /reset with initial_population=5000 ...")
        payload = {'initial_population': 5000}
        response = requests.post(base_url + "/reset", json=payload)
        assert response.status_code == 200
        data = response.json()
        pop = data['population']
        print(f"Population: {pop}")
        # Population should be close to 5000 (due to rounding in age distribution)
        assert 4900 < pop < 5100
        print("OK")
        
        # Test Run Duration
        print("\nTesting /run_duration with years=2 ...")
        payload = {'years': 2}
        response = requests.post(base_url + "/run_duration", json=payload)
        assert response.status_code == 200
        data = response.json()
        date = data['date']
        print(f"Date: {date}")
        # Start date is 2020-01-01. 2 years later should be 2022-01-01 (approx, ignoring leap years logic in simple timedelta if any, but datetime handles it)
        # 2020 is a leap year (366 days). 2021 is 365. Total 731 days?
        # Our logic: days = years * 365. So 2 * 365 = 730 days.
        # 2020-01-01 + 730 days.
        # 2020 has 366 days. So 2021-01-01 is +366.
        # We add 730. So it will be slightly off true calendar years if leap years involved, but that's expected with *365 logic.
        # Let's just check it advanced significantly.
        assert "2021" in date or "2022" in date
        print("OK")
        
        print("\nAll parameter tests passed!")
        
    except Exception as e:
        print(f"Test failed: {repr(e)}")
        sys.exit(1)
    finally:
        print("Stopping Flask app...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_flask_parameters()
