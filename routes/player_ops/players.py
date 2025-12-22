from flask import request, jsonify
from models import Player, Team, Tournament, SuperTournament, db
from . import player_ops_bp
from sqlalchemy import func, or_, text
import logging
from ..match_ops.teams import generate_phone_number, generate_uuid

logger = logging.getLogger(__name__)

def find_player_by_phone(phone_number, super_tournament_id):
    """Find existing player by phone number in the super tournament"""
    return Player.query.filter(
        Player.phone_number == phone_number,
        Player.super_tournament_id == super_tournament_id
    ).first()

@player_ops_bp.route('/players', methods=['GET'])
def get_players():
    """Get all players in a super tournament with optional checked_in filter"""
    super_tournament_id = request.args.get('super_tournament_id')
    checked_in = request.args.get('checked_in', type=lambda v: v.lower() == 'true')

    if not super_tournament_id:
        return jsonify({
            'error': 'super_tournament_id is required'
        }), 400

    try:
        # Build base query
        query = Player.query.filter_by(super_tournament_id=super_tournament_id)

        # Apply checked_in filter if provided
        if checked_in is not None:
            query = query.filter_by(checked_in=checked_in)

        # Get all players
        players = query.all()

        # Get all teams for these players
        player_uuids = [p.uuid for p in players]
        teams = Team.query.filter(
            or_(
                Team.player1_uuid.in_(player_uuids),
                Team.player2_uuid.in_(player_uuids)
            )
        ).all()

        # Create a mapping of player UUID to their teams
        player_teams = {}
        for team in teams:
            if team.player1_uuid:
                if team.player1_uuid not in player_teams:
                    player_teams[team.player1_uuid] = []
                player_teams[team.player1_uuid].append({
                    'team_id': team.team_id,
                    'tournament_id': team.tournament_id
                })
            if team.player2_uuid:
                if team.player2_uuid not in player_teams:
                    player_teams[team.player2_uuid] = []
                player_teams[team.player2_uuid].append({
                    'team_id': team.team_id,
                    'tournament_id': team.tournament_id
                })

        # Build response
        response = []
        for player in players:
            player_data = {
                'uuid': player.uuid,
                'first_name': player.first_name,
                'last_name': player.last_name,
                'phone_number': player.phone_number,
                'email': player.email,
                'gender': player.gender,
                'age': player.age,
                'skill_type': player.skill_type,
                'dupr_id': player.dupr_id,
                'checked_in': player.checked_in,
                'super_tournament_id': player.super_tournament_id,
                'teams': player_teams.get(player.uuid, [])
            }
            response.append(player_data)

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error fetching players: {str(e)}")
        return jsonify({'error': str(e)}), 500

@player_ops_bp.route('/players', methods=['POST'])
def add_players():
    """Add multiple players to a super tournament"""
    data = request.json
    super_tournament_id = data.get('super_tournament_id')
    players_data = data.get('players', [])

    if not super_tournament_id:
        return jsonify({
            'error': 'super_tournament_id is required'
        }), 400

    if not players_data:
        return jsonify({
            'error': 'At least one player is required'
        }), 400

    # Check if super tournament exists
    super_tournament = SuperTournament.query.get(super_tournament_id)
    if not super_tournament:
        return jsonify({'error': 'Super tournament not found'}), 404

    try:
        added_players = []
        for player_data in players_data:
            # Check for required fields
            if not player_data.get('first_name'):
                return jsonify({
                    'error': 'first_name is required for all players'
                }), 400

            # Get last name (optional)
            last_name = player_data.get('last_name', '')

            # Check for duplicate names in the same super tournament
            existing_player = Player.query.filter(
                func.lower(Player.first_name) == func.lower(player_data['first_name']),
                func.lower(Player.last_name) == func.lower(last_name),
                Player.super_tournament_id == super_tournament_id
            ).first()

            if existing_player:
                full_name = f"{player_data['first_name']} {last_name}".strip()
                return jsonify({
                    'error': f"Player '{full_name}' already exists in this super tournament"
                }), 409

            # Handle phone number
            phone_number = player_data.get('phone_number')
            if phone_number:
                # Check if phone number is already in use
                existing_phone = find_player_by_phone(phone_number, super_tournament_id)
                if existing_phone:
                    return jsonify({
                        'error': f"Phone number '{phone_number}' is already registered to another player"
                    }), 409
            else:
                # Generate a unique phone number
                phone_number = generate_phone_number(super_tournament_id)

            # Create new player
            player = Player(
                uuid=generate_uuid(),
                first_name=player_data['first_name'],
                last_name=last_name,
                phone_number=phone_number,
                email=player_data.get('email'),  # Keep email as null if not provided
                gender=player_data.get('gender', 'Not Specified'),
                age=int(player_data.get('age', 0)),
                skill_type=player_data.get('skill_type', 'INTERMEDIATE'),
                dupr_id=player_data.get('dupr_id', ''),
                super_tournament_id=super_tournament_id,
                checked_in=player_data.get('checked_in', False)
            )
            db.session.add(player)
            db.session.flush()

            added_players.append({
                'uuid': player.uuid,
                'first_name': player.first_name,
                'last_name': player.last_name,
                'phone_number': player.phone_number,
                'email': player.email,
                'gender': player.gender,
                'age': player.age,
                'skill_type': player.skill_type,
                'dupr_id': player.dupr_id,
                'checked_in': player.checked_in,
                'super_tournament_id': player.super_tournament_id
            })

        db.session.commit()
        return jsonify({
            'message': 'Players added successfully',
            'players': added_players
        }), 201

    except Exception as e:
        logger.error(f"Error adding players: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@player_ops_bp.route('/players/<uuid>', methods=['PUT'])
def update_player(uuid):
    """Update a player's information"""
    data = request.json
    super_tournament_id = data.get('super_tournament_id')

    if not super_tournament_id:
        return jsonify({
            'error': 'super_tournament_id is required'
        }), 400

    try:
        # Get player
        player = Player.query.filter_by(
            uuid=uuid,
            super_tournament_id=super_tournament_id
        ).first()

        if not player:
            return jsonify({'error': 'Player not found'}), 404

        # Check for name uniqueness if name is being updated
        if ('first_name' in data or 'last_name' in data) and \
           (data.get('first_name', player.first_name) != player.first_name or \
            data.get('last_name', player.last_name) != player.last_name):
            existing_player = Player.query.filter(
                func.lower(Player.first_name) == func.lower(data.get('first_name', player.first_name)),
                func.lower(Player.last_name) == func.lower(data.get('last_name', player.last_name)),
                Player.super_tournament_id == super_tournament_id,
                Player.uuid != uuid
            ).first()

            if existing_player:
                return jsonify({
                    'error': f"Player '{data.get('first_name', player.first_name)} {data.get('last_name', player.last_name)}' already exists in this super tournament"
                }), 409

        # Update fields
        for field in ['first_name', 'last_name', 'phone_number', 'email', 'gender', 'age', 'skill_type', 'dupr_id', 'checked_in']:
            if field in data:
                setattr(player, field, data[field])

        db.session.commit()

        # Get player's teams
        teams = Team.query.filter(
            or_(
                Team.player1_uuid == player.uuid,
                Team.player2_uuid == player.uuid
            )
        ).all()

        teams_data = [{
            'team_id': team.team_id,
            'tournament_id': team.tournament_id
        } for team in teams]

        return jsonify({
            'message': 'Player updated successfully',
            'player': {
                'uuid': player.uuid,
                'first_name': player.first_name,
                'last_name': player.last_name,
                'phone_number': player.phone_number,
                'email': player.email,
                'gender': player.gender,
                'age': player.age,
                'skill_type': player.skill_type,
                'dupr_id': player.dupr_id,
                'checked_in': player.checked_in,
                'super_tournament_id': player.super_tournament_id,
                'teams': teams_data
            }
        }), 200

    except Exception as e:
        logger.error(f"Error updating player: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@player_ops_bp.route('/players/<uuid>', methods=['DELETE'])
def delete_player(uuid):
    """Delete a player"""
    super_tournament_id = request.args.get('super_tournament_id')

    if not super_tournament_id:
        return jsonify({
            'error': 'super_tournament_id is required'
        }), 400

    try:
        # Get player
        player = Player.query.filter_by(
            uuid=uuid,
            super_tournament_id=super_tournament_id
        ).first()

        if not player:
            return jsonify({'error': 'Player not found'}), 404

        # Check if player is part of any teams
        teams = Team.query.filter(
            or_(
                Team.player1_uuid == uuid,
                Team.player2_uuid == uuid
            )
        ).first()

        if teams:
            return jsonify({
                'error': 'Cannot delete player as they are part of one or more teams'
            }), 409

        # Delete player
        db.session.delete(player)
        db.session.commit()

        return jsonify({
            'message': 'Player deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting player: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 