import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from collections import defaultdict

# Add the parent directory to the path so we can import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import (
    SuperTournament, Season, Tournament, Team, Player, Match, Round, Score
)
from typing import Dict, List, Any
import json

# Load environment variables
load_dotenv()

# Database connection
DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

def get_tournament_data(super_tournament_id: int) -> Dict[str, Any]:
    session = Session()
    try:
        # Get super tournament
        super_tournament = session.query(SuperTournament).filter_by(id=super_tournament_id).first()
        if not super_tournament:
            raise ValueError(f"Super tournament with ID {super_tournament_id} not found")

        # Get all seasons for this super tournament
        seasons = session.query(Season).filter_by(super_tournament_id=super_tournament_id).all()
        
        # Get all tournaments for all seasons
        tournament_ids = []
        for season in seasons:
            tournament_ids.extend([t.id for t in season.tournaments])
        
        # Get all teams for these tournaments
        teams = session.query(Team).filter(Team.tournament_id.in_(tournament_ids)).all()
        team_dict = {team.team_id: {
            'id': team.team_id,
            'name': team.name,
            'player1uuid': team.player1_uuid,
            'player2uuid': team.player2_uuid
        } for team in teams}

        # Get all players for this super tournament
        players = session.query(Player).filter_by(super_tournament_id=super_tournament_id).all()
        player_dict = {player.uuid: {
            'uuid': player.uuid,
            'firstName': player.first_name,
            'lastName': player.last_name,
            'gender': player.gender,
            'age': player.age,
            'phoneNo': player.phone_number,
            'email': player.email,
            'skill': player.skill_type,
            'duprId': player.dupr_id
        } for player in players}

        # Get all matches and organize by tournament and round
        matches = session.query(Match).filter(Match.tournament_id.in_(tournament_ids)).all()
        
        # Get all rounds and create a dictionary of round names by tournament_id and round_id
        rounds = session.query(Round).filter(Round.tournament_id.in_(tournament_ids)).all()
        
        # Group rounds by tournament_id and round_id
        round_names = defaultdict(lambda: defaultdict(set))
        for round_entry in rounds:
            round_names[round_entry.tournament_id][round_entry.round_id].add(round_entry.name)
        
        # Create a dictionary of round names
        round_dict = {}
        for tournament_id, rounds_data in round_names.items():
            round_dict[tournament_id] = {}
            for round_id, names in rounds_data.items():
                # Use the first name if there are multiple (should be the same)
                round_dict[tournament_id][str(round_id)] = next(iter(names)) if names else f"Round {round_id}"

        # Organize matches by tournament and round
        tournament_data = {}
        for match in matches:
            tournament = session.query(Tournament).get(match.tournament_id)
            if tournament.tournament_name not in tournament_data:
                tournament_data[tournament.tournament_name] = {
                    'name': tournament.tournament_name,
                    'rounds': {},
                    'teams': []
                }

            # Add round if not exists
            if match.round_id not in tournament_data[tournament.tournament_name]['rounds']:
                # Get round name from the round_dict
                round_name = round_dict.get(match.tournament_id, {}).get(match.round_id, f"Round {match.round_id}")
                
                tournament_data[tournament.tournament_name]['rounds'][match.round_id] = {
                    'name': round_name,
                    'id': match.round_id,
                    'pools': {}
                }

            # Add pool if not exists
            if match.pool not in tournament_data[tournament.tournament_name]['rounds'][match.round_id]['pools']:
                tournament_data[tournament.tournament_name]['rounds'][match.round_id]['pools'][match.pool] = {
                    'poolName': match.pool,
                    'matches': []
                }

            # Add match
            match_data = {
                'name': match.match_name,
                'teamId1': match.team1_id,
                'teamId2': match.team2_id,
                'winnerTeamId': match.winner_team_id,
                'isFinal': match.is_final,
                'status': match.status,
                'predecessor1': match.predecessor_1,
                'predecessor2': match.predecessor_2,
                'successor': match.successor,
                'bracketPosition': match.bracket_position
            }
            tournament_data[tournament.tournament_name]['rounds'][match.round_id]['pools'][match.pool]['matches'].append(match_data)

        # Convert rounds dict to list
        for tournament_name in tournament_data:
            tournament_data[tournament_name]['rounds'] = [
                {
                    'name': round_data['name'],
                    'id': round_id,
                    'pools': list(round_data['pools'].values())
                }
                for round_id, round_data in tournament_data[tournament.tournament_name]['rounds'].items()
            ]

        # Add teams to each tournament
        for tournament_name in tournament_data:
            tournament_data[tournament_name]['teams'] = list(team_dict.values())

        return {
            'name': super_tournament.name,
            'categories': list(tournament_data.values()),
            'players': list(player_dict.values())  # Players at the SuperTournament level
        }

    finally:
        session.close()

def main():
    # Example usage
    super_tournament_id = int(input("Enter super tournament ID: "))
    try:
        data = get_tournament_data(super_tournament_id)
        
        # Save to JSON file
        output_file = f"tournament_{super_tournament_id}.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Data saved to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 