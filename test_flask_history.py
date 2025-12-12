import subprocess
import time
import requests
import sys
import json

def test_flask_history():
    print("Starting Flask app...")
    # Start Flask app in background as a module
    process = subprocess.Popen([sys.executable, "-m", "Typhmesa.app"], 
                               stdout=subprocess.PIPE, 
                               stderr=sys.stderr)
    
    try:
        # Wait for app to start
        time.sleep(5)
        
        base_url = "http://127.0.0.1:5000"
        
        # Test Run Duration with History
        print("\nTesting /run_duration with years=3 ...")
        payload = {'years': 3}
        response = requests.post(base_url + "/run_duration", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Check History
        assert 'history' in data
        history = data['history']
        print(f"History Length: {len(history)}")
        # Should have Year 0, 1, 2, 3 (4 frames)
        assert len(history) == 4
        
        for i, frame in enumerate(history):
            print(f"Frame {i}: Year {frame['year']}, Date {frame['date']}, Pop {frame['population']}")
            assert frame['year'] == i
            assert 'graph' in frame
            
        print("OK")
        
        print("\nAll history tests passed!")
        
    except Exception as e:
        print(f"Test failed: {repr(e)}")
        sys.exit(1)
    finally:
        print("Stopping Flask app...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_flask_history()
