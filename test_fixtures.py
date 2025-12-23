import requests
import json

BASE_URL = 'http://localhost:5001'

def test_fixtures():
    print("Testing Fixtures Endpoint...")
    
    # Get fixtures for tournament 1
    try:
        response = requests.get(f'{BASE_URL}/get-match-fixtures?tournament_id=1')
        if response.status_code != 200:
            print(f"Failed to fetch fixtures: {response.text}")
            return
            
        data = response.json()
        matches = data.get('matches', [])
        
        if not matches:
            print("No matches found.")
            return
            
        print(f"Found {len(matches)} matches.")
        
        # Check for outcome field
        found_outcome = False
        for match in matches:
            status = match.get('match_status', {})
            outcome = status.get('outcome')
            
            if 'outcome' in status:
                found_outcome = True
                print(f"Match {match['match_id']} outcome: {outcome}")
                
                if outcome == 'walkover':
                    print("Found walkover match!")
            
        if found_outcome:
            print("VERIFICATION PASSED: 'outcome' field present in fixtures.")
        else:
            print("VERIFICATION FAILED: 'outcome' field missing from fixtures.")

    except Exception as e:
        print(f"Test failed with exception: {e}")

if __name__ == "__main__":
    test_fixtures()
