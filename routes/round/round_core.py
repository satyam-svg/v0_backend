from flask import request, jsonify
from models import Tournament, Team, Player, Match, Score, Round, db
from . import round_bp

@round_bp.route('/create-round', methods=['POST'])
def create_round():
    data = request.json
    
    # Extract data from request
    tournament_id = data.get('tournament_id')
    round_id = data.get('round_id')
    number_of_pools = data.get('number_of_pools')
    round_name = data.get('round_name', f'Round {round_id}')  # Default to round ID if no name provided
    num_of_top_teams_to_promote = data.get('num_of_top_teams_to_promote')  # Optional
    teams = data.get('teams')  # Optional, array of team_ids

    if not all([tournament_id, round_id, number_of_pools]):
        return jsonify({
            'error': 'tournament_id, round_id, and number_of_pools are required',
            'tournament_id': tournament_id,
            'round_id': round_id,
            'number_of_pools': number_of_pools
        }), 400

    try:
        number_of_pools = int(number_of_pools)
        if number_of_pools <= 0:
            return jsonify({'error': 'number_of_pools must be a positive integer'}), 400
    except ValueError:
        return jsonify({'error': 'number_of_pools must be a valid integer'}), 400

    tournament = Tournament.query.filter_by(id=tournament_id).first()
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    # Check if round already exists in this tournament with same round_id
    existing_round = Round.query.filter_by(
        tournament_id=tournament_id,
        round_id=round_id
    ).first()

    if existing_round:
        return jsonify({
            'error': 'Round already exists in this tournament with the same round_id'
        }), 409

    if num_of_top_teams_to_promote:
        # Call the cumulative points API to get the top teams
        standings_response = get_cumulative_points_for_round(tournament_id)
        standings_data = standings_response.get_json()

        # Get the top `num_of_top_teams_to_promote` teams
        sorted_teams = sorted(standings_data['standings'], key=lambda x: (x['total_points'], x['points_difference']), reverse=True)
        top_teams = sorted_teams[:int(num_of_top_teams_to_promote)]

        # Extract team_ids
        team_ids_to_use = [team['team_id'] for team in top_teams]
    elif teams:
        # Use the provided team IDs
        team_ids_to_use = teams
    else:
        # Use all teams in the tournament
        team_ids_to_use = [team.team_id for team in tournament.teams]

    # Step 2: Create the rounds
    try:
        created_pools = []
        teams_per_pool = len(team_ids_to_use) // number_of_pools
        remaining_teams = len(team_ids_to_use) % number_of_pools

        # Distribute teams into pools
        pool_teams = []
        index = 0
        for pool_number in range(1, number_of_pools + 1):
            pool_size = teams_per_pool + (1 if pool_number <= remaining_teams else 0)
            pool_teams.append(team_ids_to_use[index:index + pool_size])
            index += pool_size

        # Create round entries for each pool
        for pool_number, pool_teams_in_pool in enumerate(pool_teams, start=1):
            for team_id in pool_teams_in_pool:
                new_round = Round(
                    tournament_id=tournament_id,
                    round_id=round_id,
                    pool=str(pool_number),
                    team_id=team_id,
                    name=round_name
                )
                db.session.add(new_round)

            created_pools.append({
                'pool': str(pool_number),
                'teams': pool_teams_in_pool
            })

        db.session.commit()

        return jsonify({
            'message': 'Round created successfully with multiple pools',
            'round_details': {
                'tournament_id': tournament_id,
                'round_id': round_id,
                'round_name': round_name,
                'number_of_pools': number_of_pools,
                'pools': created_pools
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@round_bp.route('/delete-round', methods=['DELETE'])
def delete_round():
    round_id = request.args.get('round_id')
    tournament_id = request.args.get('tournament_id')
    pool = request.args.get('pool')  # Optional parameter

    if not round_id:
        return jsonify({'error': 'Round ID is required'}), 400

    try:
        # Define the query to find matches based on round_id and pool if specified
        query = Match.query.filter_by(round_id=round_id, tournament_id=tournament_id)
        if pool:
            query = Match.query.filter_by(round_id=round_id, tournament_id=tournament_id,pool=pool)

        matches = query.all()

        if not matches:
            return jsonify({'error': 'No matches found for the provided round and pool combination'}), 404

        # Loop through each match and delete related records
        for match in matches:
            # Delete associated scores for the match
            Score.query.filter_by(match_id=match.id).delete()

            db.session.delete(match)
        
        Round.query.filter_by(round_id=round_id).delete()

        # Commit the changes to the database
        db.session.commit()

        return jsonify({'message': 'Data for the specified round and pool combination deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 