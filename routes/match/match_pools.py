from flask import request, jsonify
from models import Match, Team, Tournament, Round, Score, db
from sqlalchemy import text
import csv
import io
from . import match_bp

@match_bp.route('/pools', methods=['GET'])
def get_pools():
    # Get round_id and tournament_id from query parameters
    round_id = request.args.get('round_id')
    tournament_id = request.args.get('tournament_id')

    # Validate round_id and tournament_id presence
    if not round_id or not tournament_id:
        return jsonify({'error': 'Both round_id and tournament_id are required'}), 400

    try:
        # Convert round_id and tournament_id to integers
        round_id = int(round_id)
        tournament_id = int(tournament_id)

        # Check if the tournament exists
        tournament = Tournament.query.filter_by(id=tournament_id).first()
        if not tournament:
            return jsonify({'error': 'Tournament not found'}), 404

        # Query for distinct pools in the given round and tournament
        unique_pools = db.session.query(Round.pool).filter_by(round_id=round_id, tournament_id=tournament_id).distinct().all()
        pool_list = [pool[0] for pool in unique_pools]

        # If no pools are found, return a 404 error
        if not pool_list:
            return jsonify({'error': 'No pools found for the provided round and tournament'}), 404

        # Return the pools
        return jsonify({
            'round_id': round_id,
            'tournament_id': tournament_id,
            'pools': pool_list
        }), 200

    except ValueError:
        return jsonify({'error': 'Round ID and Tournament ID must be integers'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@match_bp.route('/update-pools', methods=['POST'])
def update_pools():
    print("\n=== Starting /update-pools endpoint ===")
    tournament_id = request.form.get('tournament_id')
    round_name = request.form.get('round_name')
    
    print(f"Received request - Tournament ID: {tournament_id}, Round Name: {round_name}")
    
    if not tournament_id:
        return jsonify({"error": "tournament_id is required"}), 400
    
    # Check if the tournament exists
    tournament = Tournament.query.filter_by(id=tournament_id).first()
    if not tournament:
        return jsonify({"error": "Tournament not found"}), 404
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    round_id = request.form.get('round_id')

    if not round_id or not round_id.isdigit():
        return jsonify({'error': 'Round ID is required and should be a number'}), 400

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        round_id = int(round_id)
        pools = []
        stream = file.stream.read().decode('utf-8').splitlines()
        csv_reader = csv.DictReader(stream)

        # Keep track of teams that don't exist
        missing_teams = []
        valid_teams = []

        print(f"\nProcessing round {round_id} for tournament {tournament_id}")

        # Create or update round name if provided
        if round_name:
            print(f"Updating round name to: {round_name}")
            db.session.query(Round).filter_by(
                round_id=round_id,
                tournament_id=tournament_id
            ).update({
                'name': round_name
            })

        # First, delete existing round entries for this round_id and tournament
        existing_entries = Round.query.filter_by(
            round_id=round_id,
            tournament_id=tournament_id
        ).delete()
        print(f"Deleted {existing_entries} existing round entries")

        # Parse each row in the CSV file
        for row in csv_reader:
            team_id = row['Team ID']
            pool = row['Pool']

            # Check if team exists in the tournament
            team = Team.query.filter_by(
                team_id=team_id,
                tournament_id=tournament_id
            ).first()

            print(f"Checking team {team_id} in tournament {tournament_id}: {'Found' if team else 'Not found'}")

            if team:
                valid_teams.append(team_id)
                round_entry = Round(
                    round_id=round_id,
                    team_id=team_id,
                    pool=pool,
                    tournament_id=tournament_id,
                    name=round_name if round_name else None
                )
                pools.append(round_entry)
            else:
                missing_teams.append(team_id)

        if missing_teams:
            return jsonify({
                'error': 'Some teams were not found in the tournament',
                'missing_teams': missing_teams,
                'tournament_id': tournament_id
            }), 404

        if not pools:
            return jsonify({
                'error': 'No valid teams found in the CSV file',
                'tournament_id': tournament_id
            }), 400
        
        # Bulk insert to the database
        db.session.bulk_save_objects(pools)
        db.session.commit()

        # Fetch all unique pools for the given round_id
        unique_pools = db.session.query(Round.pool)\
            .filter_by(round_id=round_id, tournament_id=tournament_id)\
            .distinct().all()
        pool_list = [pool[0] for pool in unique_pools]

        print(f"\nFound {len(pool_list)} pools: {pool_list}")

        # Delete existing matches for this round
        existing_matches = Match.query.filter_by(
            round_id=str(round_id),
            tournament_id=tournament_id
        ).all()
        
        # Delete associated scores first
        for match in existing_matches:
            Score.query.filter_by(match_id=match.id).delete()
        
        # Then delete the matches
        for match in existing_matches:
            db.session.delete(match)
        
        db.session.commit()
        print(f"Deleted {len(existing_matches)} existing matches and their scores")

        # Generate matches for each pool
        matches = []
        match_objects = []  # Store all match objects
        score_objects = []  # Store all score objects
        
        for pool in pool_list:
            # Get all teams in the current pool
            teams_in_pool = Round.query.filter_by(
                pool=pool, 
                round_id=round_id, 
                tournament_id=tournament_id
            ).all()
            
            team_ids = [team.team_id for team in teams_in_pool]

            # Get all team details in one query instead of multiple queries
            teams_dict = {
                team.team_id: team for team in Team.query.filter(
                    Team.team_id.in_(team_ids),
                    Team.tournament_id == tournament_id
                ).all()
            }

            print(f"\nGenerating matches for pool {pool} with {len(team_ids)} teams")
            
            # Keep track of matches to avoid duplicates
            pool_matches = set()
            
            # Generate matchups between the teams (round-robin style)
            for i in range(len(team_ids)):
                for j in range(i + 1, len(team_ids)):
                    team1_id = team_ids[i]
                    team2_id = team_ids[j]
                    
                    if team1_id == team2_id:  # Skip if same team
                        continue
                    
                    # Create a unique match identifier
                    match_key = tuple(sorted([team1_id, team2_id]))
                    if match_key in pool_matches:
                        print(f"Skipping duplicate match between teams {team1_id} and {team2_id}")
                        continue
                        
                    pool_matches.add(match_key)
                    
                    team1 = teams_dict.get(team1_id)
                    team2 = teams_dict.get(team2_id)

                    if not team1 or not team2:
                        print(f"Warning: Team not found. Team1: {team1}, Team2: {team2}")
                        continue

                    match_name = f"Round {round_id} Pool {pool} - {team1.name} vs {team2.name}"
                    print(f"Creating match: {match_name}")

                    # Create match object
                    match = Match(
                        round_id=str(round_id),
                        pool=pool,
                        team1_id=team1_id,
                        team2_id=team2_id,
                        match_name=match_name,
                        tournament_id=tournament_id
                    )
                    match_objects.append(match)
                    
                    # Store match data for response
                    matches.append({
                        'pool': pool,
                        'round_id': round_id,
                        'team1_id': team1_id,
                        'team1_name': team1.name,
                        'team2_id': team2_id,
                        'team2_name': team2.name,
                        'match_name': match_name
                    })

        try:
            print(f"\nSaving {len(match_objects)} new matches to database")
            # Insert matches using normal unit-of-work so IDs are populated
            db.session.add_all(match_objects)
            db.session.flush()  # ensure match.id values are assigned

            # Create score objects for all matches (using integer match_id)
            for match in match_objects:
                score_objects.extend([
                    Score(
                        match_id=match.id,
                        team_id=match.team1_id,
                        score=0,
                        tournament_id=tournament_id
                    ),
                    Score(
                        match_id=match.id,
                        team_id=match.team2_id,
                        score=0,
                        tournament_id=tournament_id
                    )
                ])

            print(f"Creating {len(score_objects)} score entries")
            # Insert all scores
            db.session.add_all(score_objects)
            db.session.commit()

            # Update match IDs in the response
            for i, match in enumerate(match_objects):
                matches[i]['match_id'] = match.id

        except Exception as e:
            print(f"Error in bulk operations: {str(e)}")
            db.session.rollback()
            raise

        print("\n=== Completed /update-pools endpoint successfully ===")
        return jsonify({
            'message': 'Pools and matches created successfully',
            'matches': matches,
            'pools': pool_list,
            'teams_processed': valid_teams,
            'debug_info': {
                'valid_teams': valid_teams,
                'missing_teams': missing_teams,
                'pool_list': pool_list,
                'match_count': len(matches),
                'teams_per_pool': {pool: len([t for t in valid_teams if t in team_ids]) for pool in pool_list}
            }
        }), 201

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': f'An error occurred: {str(e)}',
            'tournament_id': tournament_id
        }), 500