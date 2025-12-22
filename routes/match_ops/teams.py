from flask import request, jsonify
from models import Tournament, Team, Player, Round, Match, db
from . import match_ops_bp
from sqlalchemy import func, or_, text
import uuid
import logging
import random
import string

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_team_id(tournament_id):
    """Generate a team ID in format: tournamentid_sequence"""
    try:
        # Use a transaction to handle concurrent team ID generation
        with db.session.begin_nested():
            # Get the highest sequence number for this tournament using raw SQL
            # This ensures we get the latest sequence even in concurrent scenarios
            result = db.session.execute(
                text("SELECT team_id FROM team WHERE team_id LIKE :pattern ORDER BY team_id DESC LIMIT 1 FOR UPDATE"),
                {"pattern": f"{tournament_id}_%"}
            ).fetchone()

            if result:
                try:
                    sequence = int(result[0].split('_')[1])
                    new_sequence = sequence + 1
                except (IndexError, ValueError):
                    new_sequence = 1
            else:
                new_sequence = 1

            # Verify the generated ID doesn't exist
            while True:
                new_team_id = f"{tournament_id}_{new_sequence}"
                exists = db.session.execute(
                    text("SELECT 1 FROM team WHERE team_id = :team_id"),
                    {"team_id": new_team_id}
                ).fetchone()
                
                if not exists:
                    break
                new_sequence += 1

            return new_team_id
    except Exception as e:
        logger.error(f"Error generating team ID: {str(e)}")
        db.session.rollback()
        raise

def generate_phone_number(tournament_id):
    """Generate a phone number in format: tournamentid_sequence"""
    logger.debug(f"Generating phone number for tournament {tournament_id}")
    
    try:
        # Use a transaction to handle concurrent phone number generation
        with db.session.begin_nested():
            # Get the highest sequence number directly from the player table using raw SQL
            result = db.session.execute(
                text("SELECT phone_number FROM player WHERE phone_number LIKE :pattern ORDER BY phone_number DESC LIMIT 1 FOR UPDATE"),
                {"pattern": f"{tournament_id}_%"}
            ).fetchone()

            if result:
                try:
                    sequence = int(result[0].split('_')[1])
                    new_sequence = sequence + 1
                except (IndexError, ValueError):
                    new_sequence = 1
            else:
                new_sequence = 1

            # Verify the generated phone number doesn't exist
            while True:
                phone_number = f"{tournament_id}_{new_sequence}"
                exists = db.session.execute(
                    text("SELECT 1 FROM player WHERE phone_number = :phone_number"),
                    {"phone_number": phone_number}
                ).fetchone()
                
                if not exists:
                    break
                new_sequence += 1

            logger.debug(f"Generated phone number: {phone_number}")
            return phone_number
    except Exception as e:
        logger.error(f"Error generating phone number: {str(e)}")
        db.session.rollback()
        raise

def validate_player_data(player_data, tournament_id, is_update=False):
    """Validate player data and return formatted player info"""
    if not player_data.get('name'):
        return None, 'Player name is required'
    
    # Split name into first and last name
    full_name = player_data['name'].strip()
    name_parts = full_name.split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    # For updates, only include fields that are provided
    if is_update:
        player_info = {
            'first_name': first_name,
            'last_name': last_name
        }
        # Only include optional fields if they are provided
        if 'phone_number' in player_data:
            player_info['phone_number'] = player_data['phone_number']
        if 'email' in player_data:
            player_info['email'] = player_data['email']
        if 'gender' in player_data:
            player_info['gender'] = player_data['gender']
        if 'age' in player_data:
            player_info['age'] = int(player_data['age']) if str(player_data['age']).strip().isdigit() else 0
        if 'skill_type' in player_data:
            player_info['skill_type'] = player_data['skill_type']
        if 'dupr_id' in player_data:
            player_info['dupr_id'] = player_data['dupr_id']
    else:
        # For new players, include all fields with defaults
        player_info = {
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': player_data.get('phone_number') or generate_phone_number(tournament_id),
            'email': player_data.get('email', f"{first_name.lower()}.{last_name.lower()}@example.com"),
            'gender': player_data.get('gender', 'Not Specified'),
            'age': int(player_data['age']) if player_data.get('age', '').strip().isdigit() else 0,
            'skill_type': player_data.get('skill_type', 'INTERMEDIATE'),
            'dupr_id': player_data.get('dupr_id', '')
        }

    return player_info, None

def generate_uuid():
    """Generate a 5-character alphanumeric UUID"""
    # Use uppercase letters and digits for better readability
    characters = string.ascii_uppercase + string.digits
    while True:
        new_uuid = ''.join(random.choices(characters, k=5))
        # Check if UUID already exists
        if not Player.query.filter_by(uuid=new_uuid).first():
            return new_uuid

def find_existing_player(first_name, last_name, super_tournament_id):
    """Find existing player by name in the super tournament"""
    return Player.query.filter(
        func.lower(Player.first_name) == func.lower(first_name),
        func.lower(Player.last_name) == func.lower(last_name),
        Player.super_tournament_id == super_tournament_id
    ).first()

def check_player_in_tournament(player_uuid, tournament_id):
    """Check if player is already in any team in the tournament"""
    existing_team = Team.query.filter(
        Team.tournament_id == tournament_id,
        or_(Team.player1_uuid == player_uuid, Team.player2_uuid == player_uuid)
    ).first()
    return existing_team is not None

@match_ops_bp.route('/pools/<pool_name>/teams', methods=['POST'])
def add_teams_to_pool(pool_name):
    """Add teams to a pool"""
    logger.debug(f"Adding teams to pool {pool_name}")
    data = request.json
    tournament_id = data.get('tournament_id')
    teams_data = data.get('teams', [])

    if not tournament_id:
        return jsonify({
            'error': 'tournament_id is required'
        }), 400

    if not teams_data:
        return jsonify({
            'error': 'At least one team is required'
        }), 400

    # Check if tournament exists
    tournament = Tournament.query.filter_by(id=tournament_id).first()
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    # Check if pool exists
    pool_exists = Round.query.filter_by(
        tournament_id=tournament_id,
        round_id=1,
        pool=pool_name
    ).first()
    if not pool_exists:
        return jsonify({'error': f'Pool {pool_name} not found'}), 404

    # Check if fixtures exist
    fixtures_exist = Match.query.filter_by(
        tournament_id=tournament_id,
        round_id='1',
        pool=pool_name
    ).first()

    if fixtures_exist:
        return jsonify({
            'error': 'Cannot add teams to pool with existing fixtures. Use the wildcard endpoint instead.'
        }), 409

    try:
        added_teams = []
        for team_data in teams_data:
            logger.debug(f"Processing team: {team_data.get('team_name')}")
            
            # Generate team_id
            team_id = generate_team_id(tournament_id)
            logger.debug(f"Generated team_id: {team_id}")
            
            team_name = team_data.get('team_name', f'Team {team_id}')
            player1_data = team_data.get('player1')
            player2_data = team_data.get('player2')  # Now optional

            # Process player1 (mandatory)
            logger.debug("Processing player1")
            player1_info, error = validate_player_data(player1_data, tournament_id)
            if error:
                return jsonify({'error': f'Player 1: {error}'}), 400

            # Check for existing player1
            existing_player1 = find_existing_player(
                player1_info['first_name'],
                player1_info['last_name'],
                tournament.season.super_tournament.id
            )

            if existing_player1:
                # Check if player is already in this tournament
                if check_player_in_tournament(existing_player1.uuid, tournament_id):
                    return jsonify({
                        'error': f"Player '{player1_info['first_name']} {player1_info['last_name']}' is already in another team in this tournament"
                    }), 409
                player1 = existing_player1
                logger.debug(f"Found existing player1: {player1.uuid}")
            else:
                # Create new player1
                player1 = Player(
                    uuid=generate_uuid(),
                    first_name=player1_info['first_name'],
                    last_name=player1_info['last_name'],
                    phone_number=generate_phone_number(tournament_id),
                    email=player1_info['email'],
                    gender=player1_info['gender'],
                    age=player1_info['age'],
                    skill_type=player1_info['skill_type'],
                    dupr_id=player1_info['dupr_id'],
                    super_tournament_id=tournament.season.super_tournament.id
                )
                db.session.add(player1)
                db.session.flush()
                logger.debug(f"Created new player1 with UUID: {player1.uuid}")

            # Process player2 (optional)
            player2 = None
            existing_player2 = None
            if player2_data:
                logger.debug("Processing player2")
                player2_info, error = validate_player_data(player2_data, tournament_id)
                if error:
                    return jsonify({'error': f'Player 2: {error}'}), 400

                # Check for existing player2
                existing_player2 = find_existing_player(
                    player2_info['first_name'],
                    player2_info['last_name'],
                    tournament.season.super_tournament.id
                )

                if existing_player2:
                    # Check if player is already in this tournament
                    if check_player_in_tournament(existing_player2.uuid, tournament_id):
                        return jsonify({
                            'error': f"Player '{player2_info['first_name']} {player2_info['last_name']}' is already in another team in this tournament"
                        }), 409
                    player2 = existing_player2
                    logger.debug(f"Found existing player2: {player2.uuid}")
                else:
                    # Create new player2
                    player2 = Player(
                        uuid=generate_uuid(),
                        first_name=player2_info['first_name'],
                        last_name=player2_info['last_name'],
                        phone_number=generate_phone_number(tournament_id),
                        email=player2_info['email'],
                        gender=player2_info['gender'],
                        age=player2_info['age'],
                        skill_type=player2_info['skill_type'],
                        dupr_id=player2_info['dupr_id'],
                        super_tournament_id=tournament.season.super_tournament.id
                    )
                    db.session.add(player2)
                    db.session.flush()
                    logger.debug(f"Created new player2 with UUID: {player2.uuid}")

                # Prevent same player being added as both player1 and player2
                if player2 and player1.uuid == player2.uuid:
                    return jsonify({
                        'error': f"Cannot add the same player '{player1_info['first_name']} {player1_info['last_name']}' twice in the same team"
                    }), 400

            # Create team
            logger.debug("Creating team")
            team = Team(
                team_id=team_id,
                name=team_name,
                tournament_id=tournament_id,
                player1_uuid=player1.uuid,
                player2_uuid=player2.uuid if player2 else None
            )
            db.session.add(team)
            logger.debug(f"Created team with ID: {team_id}")

            # Add team to pool
            round_entry = Round(
                tournament_id=tournament_id,
                round_id=1,
                team_id=team_id,
                pool=pool_name,
                name='Round Robin'
            )
            db.session.add(round_entry)
            logger.debug(f"Added team to pool: {pool_name}")

            team_info = {
                'team_id': team_id,
                'team_name': team_name,
                'player1': {
                    'name': f"{player1.first_name} {player1.last_name}".strip(),
                    'phone_number': player1.phone_number,
                    'skill_type': player1.skill_type,
                    'is_existing': existing_player1 is not None
                }
            }

            # Only add player2 info if it exists
            if player2:
                team_info['player2'] = {
                    'name': f"{player2.first_name} {player2.last_name}".strip(),
                    'phone_number': player2.phone_number,
                    'skill_type': player2.skill_type,
                    'is_existing': existing_player2 is not None
                }

            added_teams.append(team_info)

        logger.debug("Committing transaction")
        db.session.commit()
        logger.debug("Transaction committed successfully")

        return jsonify({
            'message': 'Teams added successfully',
            'added_teams': added_teams,
            'pool': pool_name
        }), 201

    except Exception as e:
        logger.error(f"Error adding teams: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@match_ops_bp.route('/pools/<pool_name>/teams/<team_id>', methods=['PUT'])
def update_team_in_pool(pool_name, team_id):
    """Update team information in a pool"""
    logger.debug(f"Updating team {team_id} in pool {pool_name}")
    data = request.json
    tournament_id = data.get('tournament_id')

    if not tournament_id:
        return jsonify({
            'error': 'tournament_id is required'
        }), 400

    try:
        # Check if team exists in pool
        team_in_pool = Round.query.filter_by(
            tournament_id=tournament_id,
            round_id=1,
            pool=pool_name,
            team_id=team_id
        ).first()

        if not team_in_pool:
            return jsonify({'error': 'Team not found in pool'}), 404

        # Get team with player relationships
        team = Team.query.filter_by(
            team_id=team_id,
            tournament_id=tournament_id
        ).first()

        if not team:
            return jsonify({'error': 'Team not found'}), 404

        # Get existing players using the correct query
        player1 = Player.query.filter_by(uuid=team.player1_uuid).first()
        if not player1:
            logger.error(f"Player1 not found. UUID: {team.player1_uuid}")
            return jsonify({'error': 'Team player1 not found'}), 404

        # Get player2 if it exists
        player2 = None
        if team.player2_uuid:
            player2 = Player.query.filter_by(uuid=team.player2_uuid).first()

        old_team_name = team.name
        # Update team name if provided
        if 'team_name' in data:
            team.name = data['team_name']
            logger.debug(f"Updated team name from {old_team_name} to {team.name}")
            
            # Update match names that contain this team
            matches = Match.query.filter(
                Match.tournament_id == tournament_id,
                Match.pool == pool_name,
                or_(Match.team1_id == team_id, Match.team2_id == team_id)
            ).all()
            
            for match in matches:
                old_match_name = match.match_name
                if match.team1_id == team_id:
                    match.match_name = match.match_name.replace(old_team_name, team.name)
                elif match.team2_id == team_id:
                    match.match_name = match.match_name.replace(old_team_name, team.name)
                logger.debug(f"Updated match name from {old_match_name} to: {match.match_name}")

        # Update player1 information if provided
        if 'player1' in data:
            player1_info, error = validate_player_data(data['player1'], tournament_id, is_update=True)
            if error:
                return jsonify({'error': f'Player 1: {error}'}), 400

            logger.debug(f"Updating player1 {player1.uuid} with info: {player1_info}")
            for key, value in player1_info.items():
                if hasattr(player1, key):  # Only update if the attribute exists
                    setattr(player1, key, value)
                    logger.debug(f"Updated player1 {key} to {value}")

        # Update player2 information if provided and exists
        if 'player2' in data and player2:
            player2_info, error = validate_player_data(data['player2'], tournament_id, is_update=True)
            if error:
                return jsonify({'error': f'Player 2: {error}'}), 400

            logger.debug(f"Updating player2 {player2.uuid} with info: {player2_info}")
            for key, value in player2_info.items():
                if hasattr(player2, key):  # Only update if the attribute exists
                    setattr(player2, key, value)
                    logger.debug(f"Updated player2 {key} to {value}")

        try:
            db.session.commit()
            logger.debug("Successfully committed all updates")
        except Exception as e:
            logger.error(f"Error committing updates: {str(e)}")
            db.session.rollback()
            raise

        # Build response with updated information
        response = {
            'message': 'Team information updated successfully',
            'team_id': team_id,
            'team': {
                'name': team.name,
                'player1': {
                    'name': f"{player1.first_name} {player1.last_name}".strip(),
                    'phone_number': player1.phone_number,
                    'email': player1.email,
                    'gender': player1.gender,
                    'age': player1.age,
                    'skill_type': player1.skill_type,
                    'dupr_id': player1.dupr_id
                }
            }
        }

        # Only include player2 in response if it exists
        if player2:
            response['team']['player2'] = {
                'name': f"{player2.first_name} {player2.last_name}".strip(),
                'phone_number': player2.phone_number,
                'email': player2.email,
                'gender': player2.gender,
                'age': player2.age,
                'skill_type': player2.skill_type,
                'dupr_id': player2.dupr_id
            }
        
        logger.debug(f"Returning updated team info: {response}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error updating team: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@match_ops_bp.route('/pools/<pool_name>/teams/by-uuid', methods=['POST'])
def add_team_by_uuid(pool_name):
    """Add a team to a pool using player UUIDs"""
    logger.debug(f"Adding team to pool {pool_name} using player UUIDs")
    data = request.json
    tournament_id = data.get('tournament_id')
    player1_uuid = data.get('player1_uuid')
    player2_uuid = data.get('player2_uuid')  # Optional
    team_name = data.get('team_name')

    if not tournament_id:
        return jsonify({
            'error': 'tournament_id is required'
        }), 400

    if not player1_uuid:
        return jsonify({
            'error': 'player1_uuid is required'
        }), 400

    # Check if tournament exists
    tournament = Tournament.query.filter_by(id=tournament_id).first()
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    # Check if pool exists
    pool_exists = Round.query.filter_by(
        tournament_id=tournament_id,
        round_id=1,
        pool=pool_name
    ).first()
    if not pool_exists:
        return jsonify({'error': f'Pool {pool_name} not found'}), 404

    # Check if fixtures exist
    fixtures_exist = Match.query.filter_by(
        tournament_id=tournament_id,
        round_id='1',
        pool=pool_name
    ).first()

    if fixtures_exist:
        return jsonify({
            'error': 'Cannot add teams to pool with existing fixtures. Use the wildcard endpoint instead.'
        }), 409

    try:
        # Check if player1 exists and belongs to the super tournament
        player1 = Player.query.filter_by(
            uuid=player1_uuid,
            super_tournament_id=tournament.season.super_tournament.id
        ).first()
        if not player1:
            return jsonify({
                'error': f"Player with UUID '{player1_uuid}' not found in this super tournament"
            }), 404

        # Check if player1 is already in a team in this tournament
        if check_player_in_tournament(player1_uuid, tournament_id):
            return jsonify({
                'error': f"Player '{player1.first_name} {player1.last_name}' is already in another team in this tournament"
            }), 409

        # Check player2 if provided
        player2 = None
        if player2_uuid:
            if player2_uuid == player1_uuid:
                return jsonify({
                    'error': "Cannot add the same player twice in a team"
                }), 400

            player2 = Player.query.filter_by(
                uuid=player2_uuid,
                super_tournament_id=tournament.season.super_tournament.id
            ).first()
            if not player2:
                return jsonify({
                    'error': f"Player with UUID '{player2_uuid}' not found in this super tournament"
                }), 404

            # Check if player2 is already in a team in this tournament
            if check_player_in_tournament(player2_uuid, tournament_id):
                return jsonify({
                    'error': f"Player '{player2.first_name} {player2.last_name}' is already in another team in this tournament"
                }), 409

        # Generate team_id
        team_id = generate_team_id(tournament_id)
        logger.debug(f"Generated team_id: {team_id}")

        # Create team name if not provided
        if not team_name:
            team_name = f"Team {team_id}"

        # Create team
        team = Team(
            team_id=team_id,
            name=team_name,
            tournament_id=tournament_id,
            player1_uuid=player1_uuid,
            player2_uuid=player2_uuid
        )
        db.session.add(team)
        logger.debug(f"Created team with ID: {team_id}")

        # Add team to pool
        round_entry = Round(
            tournament_id=tournament_id,
            round_id=1,
            team_id=team_id,
            pool=pool_name,
            name='Round Robin'
        )
        db.session.add(round_entry)
        logger.debug(f"Added team to pool: {pool_name}")

        # Build response data
        team_info = {
            'team_id': team_id,
            'team_name': team_name,
            'player1': {
                'uuid': player1.uuid,
                'name': f"{player1.first_name} {player1.last_name}".strip(),
                'phone_number': player1.phone_number,
                'skill_type': player1.skill_type
            }
        }

        if player2:
            team_info['player2'] = {
                'uuid': player2.uuid,
                'name': f"{player2.first_name} {player2.last_name}".strip(),
                'phone_number': player2.phone_number,
                'skill_type': player2.skill_type
            }

        db.session.commit()
        logger.debug("Successfully added team by UUID")

        return jsonify({
            'message': 'Team added successfully',
            'team': team_info,
            'pool': pool_name
        }), 201

    except Exception as e:
        logger.error(f"Error adding team by UUID: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@match_ops_bp.route('/pools/<pool_name>/teams/<team_id>', methods=['DELETE'])
def delete_team_from_pool(pool_name, team_id):
    """Delete a team from a pool if no fixtures exist"""
    logger.debug(f"Attempting to delete team {team_id} from pool {pool_name}")
    
    # Get tournament_id from query params
    tournament_id = request.args.get('tournament_id')
    if not tournament_id:
        return jsonify({
            'error': 'tournament_id is required as a query parameter'
        }), 400

    try:
        # Check if team exists in pool
        team_in_pool = Round.query.filter_by(
            tournament_id=tournament_id,
            round_id=1,
            pool=pool_name,
            team_id=team_id
        ).first()

        if not team_in_pool:
            return jsonify({'error': 'Team not found in pool'}), 404

        # Check if fixtures exist for this pool
        fixtures_exist = Match.query.filter_by(
            tournament_id=tournament_id,
            round_id='1',
            pool=pool_name
        ).first()

        if fixtures_exist:
            return jsonify({
                'error': 'Cannot delete team from pool with existing fixtures'
            }), 409

        # Get the team to be deleted
        team = Team.query.filter_by(
            team_id=team_id,
            tournament_id=tournament_id
        ).first()

        if not team:
            return jsonify({'error': 'Team not found'}), 404

        # Delete team from Round table
        Round.query.filter_by(
            tournament_id=tournament_id,
            round_id=1,
            pool=pool_name,
            team_id=team_id
        ).delete()

        # Delete the team
        db.session.delete(team)
        
        # Commit the changes
        db.session.commit()
        logger.debug(f"Successfully deleted team {team_id} from pool {pool_name}")

        return jsonify({
            'message': 'Team successfully deleted from pool',
            'team_id': team_id,
            'pool': pool_name
        }), 200

    except Exception as e:
        logger.error(f"Error deleting team from pool: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 