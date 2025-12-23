import requests
import json

BASE_URL = 'http://localhost:5001'

def test_walkover():
    print("Testing Walkover Functionality...")
    
    # 1. Create a match (or find one)
    # For simplicity, let's use an existing match or create one if possible.
    # We'll try to find a pending match first.
    
    # Get matches
    # We need a tournament ID first.
    # Let's assume tournament ID 1 exists from previous steps.
    tournament_id = 1
    
    print("Fetching matches...")
    try:
        response = requests.get(f'{BASE_URL}/score?tournament_id={tournament_id}')
        if response.status_code != 200:
            print(f"Failed to fetch matches: {response.text}")
            return
            
        matches = response.json()
        if not matches:
            print("No matches found.")
            return
            
        # Find a match to update
        # We need the match ID. The /score endpoint returns score objects, not match objects directly in the list.
        # Wait, get_scores returns a list of score objects.
        # Let's use /score/match endpoint if we have an ID, or just pick one from the DB check.
        
        # Let's use the generate_matches.py logic to pick a match.
        # Or better, let's just create a new match to be safe.
        
        # Create a match
        print("Creating a test match...")
        create_payload = {
            "tournament_id": 1,
            "team1_id": "T001",
            "team2_id": "T002",
            "round_id": "TestRound",
            "pool": "TestPool"
        }
        response = requests.post(f'{BASE_URL}/create-match', json=create_payload)
        if response.status_code != 201:
             print(f"Failed to create match: {response.text}")
             # If it fails (maybe teams don't exist in tourney 1?), try to use an existing match ID.
             # Let's assume match ID 1 exists.
             match_id = 1
             print(f"Using existing match ID: {match_id}")
        else:
            match_id = response.json()['match_id']
            print(f"Created match with ID: {match_id}")

        # 2. Update score with Walkover
        print(f"Updating match {match_id} as Walkover for Team T001...")
        update_payload = {
            "match_id": match_id,
            "score": "0-0", # Score doesn't matter for walkover
            "tournament_id": 1,
            "final": True,
            "outcome": "walkover",
            "winner_team_id": "T001"
        }
        
        response = requests.post(f'{BASE_URL}/update-score', json=update_payload)
        print(f"Update response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            print("Walkover update successful.")
            
            # 3. Verify status
            print("Verifying match status...")
            response = requests.get(f'{BASE_URL}/score/match?match_id={match_id}&tournament_id=1')
            match_data = response.json()
            
            print(f"Match Status: {match_data.get('status')}")
            print(f"Is Final: {match_data.get('is_final')}")
            print(f"Winner: {match_data.get('winner_team_id')}")
            print(f"Outcome: {match_data.get('outcome')}")
            
            if match_data.get('status') == 'completed' and match_data.get('is_final') and match_data.get('winner_team_id') == 'T001' and match_data.get('outcome') == 'walkover':
                print("VERIFICATION PASSED: Match correctly marked as walkover.")
            else:
                print("VERIFICATION FAILED: Match state incorrect.")
        else:
            print("VERIFICATION FAILED: Update request failed.")

    except Exception as e:
        print(f"Test failed with exception: {e}")

if __name__ == "__main__":
    test_walkover()
