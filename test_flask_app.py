import subprocess
import time
import requests
import sys

def test_flask_app():
    print("Starting Flask app...")
    # Start Flask app in background as a module
    process = subprocess.Popen([sys.executable, "-m", "Typhmesa.app"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
    
    try:
        # Wait for app to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            print("Flask app died early!")
            outs, errs = process.communicate()
            print("STDOUT:", outs.decode())
            print("STDERR:", errs.decode())
            sys.exit(1)
            
        base_url = "http://127.0.0.1:5000"
        
        print("Testing / ...")
        response = requests.get(base_url + "/")
        assert response.status_code == 200
        print("OK")
        
        print("Testing /state ...")
        try:
            response = requests.get(base_url + "/state")
            if response.status_code != 200:
                print(f"Status Code: {response.status_code}")
                print(f"Response Text: {response.text}")
            assert response.status_code == 200
            data = response.json()
            assert "graph" in data
            assert "date" in data
            assert "population" in data
            print(f"Initial Date: {data['date']}, Population: {data['population']}")
            print("OK")
        except Exception as e:
            print(f"Request failed: {repr(e)}")
            raise

        print("Testing /step ...")
        response = requests.post(base_url + "/step")
        assert response.status_code == 200
        data = response.json()
        print(f"New Date: {data['date']}, Population: {data['population']}")
        # Date should be one day later
        # We initialized with 2020-01-01, so step 1 should be 2020-01-02
        assert data['date'] == "2020-01-02"
        print("OK")
        
        print("Testing /reset ...")
        response = requests.post(base_url + "/reset")
        assert response.status_code == 200
        data = response.json()
        print(f"Reset Date: {data['date']}, Population: {data['population']}")
        assert data['date'] == "2020-01-01"
        print("OK")
        
        print("All tests passed!")
        
    except Exception as e:
        print(f"Test failed: {repr(e)}")
        sys.exit(1)
    finally:
        print("Stopping Flask app...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_flask_app()
