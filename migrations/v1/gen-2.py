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

def get_season_data(season: Season, all_players_dict: Dict[str, Dict]) -> Dict[str, Any]:
    """Generate data for a specific season"""
    session = Session()
    try:
        # Get all tournaments for this season
        tournament_ids = [t.id for t in season.tournaments]
        
        # Get all teams for these tournaments
        teams = session.query(Team).filter(Team.tournament_id.in_(tournament_ids)).all()
        team_dict = {team.team_id: {
            'id': team.team_id,
            'name': team.name,
            'player1uuid': team.player1_uuid,
            'player2uuid': team.player2_uuid
        } for team in teams}
        
        # Collect player UUIDs from teams
        player_uuids = set()
        for team in teams:
            if team.player1_uuid and team.player1_uuid.strip():
                player_uuids.add(team.player1_uuid)
                print(f"  - Team {team.team_id} has player1: {team.player1_uuid}")
            if team.player2_uuid and team.player2_uuid.strip():
                player_uuids.add(team.player2_uuid)
                print(f"  - Team {team.team_id} has player2: {team.player2_uuid}")
        
        # Filter players to only include those in teams
        players_dict = {}
        missing_uuids = []
        
        for uuid in player_uuids:
            if uuid in all_players_dict:
                players_dict[uuid] = all_players_dict[uuid]
            else:
                missing_uuids.append(uuid)
        
        # Look up missing players directly in the Player table
        if missing_uuids:
            print(f"  - Looking up {len(missing_uuids)} missing players directly in the Player table")
            missing_players = session.query(Player).filter(Player.uuid.in_(missing_uuids)).all()
            
            for player in missing_players:
                players_dict[player.uuid] = {
                    'uuid': player.uuid,
                    'firstName': player.first_name,
                    'lastName': player.last_name,
                    'gender': player.gender,
                    'age': player.age,
                    'phoneNo': player.phone_number,
                    'email': player.email,
                    'skill': player.skill_type,
                    'duprId': player.dupr_id
                }
                print(f"  - Found player {player.uuid} ({player.first_name} {player.last_name}) in Player table")
            
            # Check if there are still missing players
            still_missing = [uuid for uuid in missing_uuids if uuid not in players_dict]
            if still_missing:
                print(f"  - WARNING: {len(still_missing)} players still not found in Player table: {still_missing[:5]}...")
        
        # Debug output
        print(f"Season {season.id}: Found {len(teams)} teams with {len(player_uuids)} unique players, {len(players_dict)} players found in database")

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

            # Query scores for this match
            match_scores = session.query(Score).filter_by(match_id=str(match.id), tournament_id=match.tournament_id).all()
            
            # Validate scores
            if len(match_scores) > 2:
                raise ValueError(f"Error: Match ID {match.id} ({match.match_name}) in tournament {match.tournament_id} has {len(match_scores)} score entries, expected 2 or fewer.")
            
            # Check if team IDs match
            score_team_ids = [score.team_id for score in match_scores]
            expected_team_ids = [match.team1_id, match.team2_id]
            unexpected_team_ids = [team_id for team_id in score_team_ids if team_id not in expected_team_ids]
            
            if unexpected_team_ids:
                raise ValueError(f"Error: Match ID {match.id} ({match.match_name}) in tournament {match.tournament_id} has scores for unexpected team IDs: {unexpected_team_ids}. Expected team IDs: {expected_team_ids}")
            
            # Get scores for team1 and team2
            team1_score = None
            team2_score = None
            
            for score in match_scores:
                if score.team_id == match.team1_id:
                    team1_score = score.score
                elif score.team_id == match.team2_id:
                    team2_score = score.score

            # Add match
            match_data = {
                'name': match.match_name,
                'teamId1': match.team1_id,
                'teamId2': match.team2_id,
                'teamId1_score': team1_score,
                'teamId2_score': team2_score,
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
                for round_id, round_data in tournament_data[tournament_name]['rounds'].items()
            ]

        # Add teams to each tournament
        for tournament_name in tournament_data:
            tournament_data[tournament_name]['teams'] = list(team_dict.values())

        return {
            'name': f"{season.super_tournament.name} - {season.name}",
            'categories': list(tournament_data.values()),
            'players': list(players_dict.values())  # Only players who are part of teams
        }

    finally:
        session.close()

def get_tournament_data(super_tournament_id: int) -> Dict[str, Any]:
    """Generate data for a super tournament, with separate data for each season"""
    session = Session()
    try:
        # Get super tournament
        super_tournament = session.query(SuperTournament).filter_by(id=super_tournament_id).first()
        if not super_tournament:
            raise ValueError(f"Super tournament with ID {super_tournament_id} not found")

        # Get all seasons for this super tournament
        seasons = session.query(Season).filter_by(super_tournament_id=super_tournament_id).all()
        
        # Get all players for this super tournament (we'll filter per season later)
        players = session.query(Player).filter_by(super_tournament_id=super_tournament_id).all()
        all_players_dict = {player.uuid: {
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
        
        print(f"Super tournament {super_tournament_id}: Found {len(players)} total players")
        print(f"Player UUIDs: {list(all_players_dict.keys())[:5]}...")

        # Create a folder for this super tournament
        folder_name = f"tournament_{super_tournament_id}"
        os.makedirs(folder_name, exist_ok=True)
        
        # Generate data for each season
        season_data = {}
        for season in seasons:
            print(f"\nProcessing season {season.id}: {season.name}")
            season_data[season.id] = get_season_data(season, all_players_dict)
            
            # Save season data to a separate file
            output_file = os.path.join(folder_name, f"season_{season.id}.json")
            with open(output_file, 'w') as f:
                json.dump(season_data[season.id], f, indent=2)
            print(f"Data for season {season.id} saved to {output_file}")
        
        # If there's only one season, also save it as the main file
        if len(seasons) == 1:
            output_file = f"tournament_{super_tournament_id}.json"
            with open(output_file, 'w') as f:
                json.dump(list(season_data.values())[0], f, indent=2)
            print(f"Data saved to {output_file}")
        else:
            # For combined file, collect all players from all seasons
            all_season_players = {}
            for season_id, season_data_obj in season_data.items():
                for player in season_data_obj['players']:
                    all_season_players[player['uuid']] = player
            
            print(f"Combined file: Found {len(all_season_players)} unique players across all seasons")
            
            # Create a combined file with all seasons
            combined_data = {
                'name': super_tournament.name,
                'seasons': list(season_data.values()),
                'players': list(all_season_players.values())  # All unique players across all seasons
            }
            output_file = f"tournament_{super_tournament_id}_all_seasons.json"
            with open(output_file, 'w') as f:
                json.dump(combined_data, f, indent=2)
            print(f"Combined data for all seasons saved to {output_file}")
        
        return season_data

    finally:
        session.close()

def main():
    # Example usage
    super_tournament_id = int(input("Enter super tournament ID: "))
    try:
        get_tournament_data(super_tournament_id)
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()