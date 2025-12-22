from flask import request, jsonify
from models import Tournament, Round, Match, Score, Team, Player, db
from . import match_ops_bp

@match_ops_bp.route('/pools', methods=['POST'])
def create_pool():
    """Create a new pool in the round robin round"""
    data = request.json
    tournament_id = data.get('tournament_id')
    pool_name = data.get('pool_name')
    
    if not all([tournament_id, pool_name]):
        return jsonify({
            'error': 'tournament_id and pool_name are required'
        }), 400

    # Validate pool name (no spaces allowed)
    if ' ' in pool_name:
        return jsonify({
            'error': 'Pool name cannot contain spaces'
        }), 400

    # Check if tournament exists
    tournament = Tournament.query.filter_by(id=tournament_id).first()
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    # Check if pool already exists in round robin
    existing_pool = Round.query.filter_by(
        tournament_id=tournament_id,
        round_id=1,  # Round Robin is always round 1
        pool=pool_name
    ).first()

    if existing_pool:
        return jsonify({
            'error': f'Pool {pool_name} already exists in round robin'
        }), 409

    try:
        # Create a placeholder round entry for the pool
        round_entry = Round(
            tournament_id=tournament_id,
            round_id=1,  # Round Robin is always round 1
            pool=pool_name,
            name='Round Robin'  # Default round name
        )
        db.session.add(round_entry)
        db.session.commit()

        return jsonify({
            'message': f'Pool {pool_name} created successfully',
            'pool': {
                'name': pool_name,
                'tournament_id': tournament_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@match_ops_bp.route('/pools', methods=['GET'])
def list_pools():
    """List all pools in round robin with their teams and fixture status"""
    tournament_id = request.args.get('tournament_id')

    if not tournament_id:
        return jsonify({
            'error': 'tournament_id is required query parameter'
        }), 400

    try:
        # Get all pools in round robin
        pools = db.session.query(Round.pool).filter_by(
            tournament_id=tournament_id,
            round_id=1  # Round Robin is always round 1
        ).distinct().all()
        
        pool_list = []
        for (pool_name,) in pools:
            # Get teams in this pool
            teams_in_pool = Round.query.filter_by(
                tournament_id=tournament_id,
                round_id=1,
                pool=pool_name
            ).all()
            
            # Get matches in this pool
            matches = Match.query.filter_by(
                tournament_id=tournament_id,
                round_id='1',
                pool=pool_name
            ).all()

            # Get detailed team information
            teams = []
            for pool_entry in teams_in_pool:
                if not pool_entry.team_id:
                    continue
                    
                team = Team.query.filter_by(
                    team_id=pool_entry.team_id,
                    tournament_id=tournament_id
                ).first()
                
                if team:
                    # Get player information
                    player1 = Player.query.filter_by(uuid=team.player1_uuid).first()
                    player2 = Player.query.filter_by(uuid=team.player2_uuid).first()
                    
                    team_data = {
                        'team_id': team.team_id,
                        'team_name': team.name,
                        'player1': {
                            'name': f"{player1.first_name} {player1.last_name}".strip(),
                            'phone_number': player1.phone_number,
                            'email': player1.email,
                            'gender': player1.gender,
                            'age': player1.age,
                            'skill_type': player1.skill_type,
                            'dupr_id': player1.dupr_id
                        } if player1 else None,
                        'player2': {
                            'name': f"{player2.first_name} {player2.last_name}".strip(),
                            'phone_number': player2.phone_number,
                            'email': player2.email,
                            'gender': player2.gender,
                            'age': player2.age,
                            'skill_type': player2.skill_type,
                            'dupr_id': player2.dupr_id
                        } if player2 else None
                    }
                    teams.append(team_data)

            pool_data = {
                'name': pool_name,
                'teams': teams,
                'has_fixtures': len(matches) > 0,
                'match_count': len(matches)
            }
            pool_list.append(pool_data)

        return jsonify({
            'tournament_id': tournament_id,
            'pools': pool_list
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@match_ops_bp.route('/pools/<pool_name>', methods=['DELETE'])
def delete_pool():
    """Delete a pool and all its matches"""
    tournament_id = request.args.get('tournament_id')

    if not tournament_id:
        return jsonify({
            'error': 'tournament_id is required query parameter'
        }), 400

    try:
        # Get all matches in the pool
        matches = Match.query.filter_by(
            tournament_id=tournament_id,
            round_id='1',  # Round Robin is always round 1
            pool=pool_name
        ).all()

        # Delete scores first
        for match in matches:
            Score.query.filter_by(match_id=match.id).delete()

        # Delete matches
        for match in matches:
            db.session.delete(match)

        # Delete round entries for this pool
        Round.query.filter_by(
            tournament_id=tournament_id,
            round_id=1,
            pool=pool_name
        ).delete()

        db.session.commit()

        return jsonify({
            'message': f'Pool {pool_name} and all its matches deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 