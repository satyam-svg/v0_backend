from flask import request, jsonify
from models import Team, Player, Tournament, SuperTournament, Season, db
from sqlalchemy import or_
from sqlalchemy.sql import func
from . import team_bp

@team_bp.route('/teams/checkin', methods=['POST'])
def team_checkin():
    try:
        data = request.get_json()
        tournament_id = data.get('tournament_id')
        team_id = data.get('team_id')
        checked_in = data.get('checked_in', True)  # Default to True for backward compatibility
        
        if not tournament_id or not team_id:
            return jsonify({'error': 'tournament_id and team_id are required'}), 400
        
        # Check if the tournament exists
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            return jsonify({'error': 'Tournament not found'}), 404
        
        # Check if the team exists
        team = Team.query.filter_by(team_id=team_id, tournament_id=tournament_id).first()
        if not team:
            return jsonify({'error': 'Team not found in the specified tournament'}), 404
        
        # Mark team as checked in
        team.checked_in = checked_in
        
        # Get players using player1_uuid and player2_uuid
        team_players = []
        if team.player1_uuid:
            player1 = Player.query.filter_by(uuid=team.player1_uuid).first()
            if player1:
                player1.checked_in = checked_in
                team_players.append(player1)
        
        if team.player2_uuid:
            player2 = Player.query.filter_by(uuid=team.player2_uuid).first()
            if player2:
                player2.checked_in = checked_in
                team_players.append(player2)
        
        db.session.commit()
        
        # Maintain the exact same response format as before
        return jsonify({
            'message': f'Team {team.name} checked in successfully',
            'team': {
                'team_id': team.team_id,
                'name': team.name,
                'checked_in': team.checked_in,
                'players': [{
                    'id': player.id,
                    'first_name': player.first_name,
                    'last_name': player.last_name,
                    'checked_in': player.checked_in
                } for player in team_players]
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@team_bp.route('/player/checkin', methods=['POST'])
def player_checkin():
    try:
        data = request.get_json()
        player_id = data.get('player_id')
        tournament_id = data.get('tournament_id')  # Still needed to find the team
        checked_in = data.get('checked_in', True)
        
        if not all([player_id, tournament_id]):
            return jsonify({'error': 'player_id and tournament_id are required'}), 400
        
        # Get player
        player = Player.query.get(player_id)
        if not player:
            return jsonify({'error': 'Player not found'}), 404
            
        # Update player's check-in status for the entire super tournament
        player.checked_in = checked_in
        
        # Get all tournaments in this super tournament through seasons
        super_tournament = SuperTournament.query.get(player.super_tournament_id)
        if not super_tournament:
            return jsonify({'error': 'Super tournament not found'}), 404
            
        tournaments = []
        for season in super_tournament.seasons:
            tournaments.extend(season.tournaments)
            
        # Update team statuses in all tournaments
        updated_teams = []
        for tournament in tournaments:
            # Find team in this tournament where player is either player1 or player2
            team = Team.query.filter(
                (Team.player1_uuid == player.uuid) | (Team.player2_uuid == player.uuid),
                Team.tournament_id == tournament.id
            ).first()
            
            if team:
                # Get the other player in the team
                other_player = None
                if team.player1_uuid == player.uuid and team.player2_uuid:
                    other_player = Player.query.filter_by(uuid=team.player2_uuid).first()
                elif team.player2_uuid == player.uuid and team.player1_uuid:
                    other_player = Player.query.filter_by(uuid=team.player1_uuid).first()
                
                # Check if all players in the team are checked in
                all_players_checked_in = player.checked_in and (not other_player or other_player.checked_in)
                
                # Update team check-in status
                team.checked_in = all_players_checked_in
                
                updated_teams.append({
                    'tournament_id': tournament.id,
                    'tournament_name': tournament.tournament_name,
                    'team': {
                        'team_id': team.team_id,
                        'name': team.name,
                        'checked_in': team.checked_in,
                        'all_players_checked_in': all_players_checked_in
                    }
                })
        
        db.session.commit()
        
        return jsonify({
            'message': 'Player check-in status updated successfully across super tournament',
            'player': {
                'id': player.id,
                'first_name': player.first_name,
                'last_name': player.last_name,
                'checked_in': player.checked_in
            },
            'super_tournament': {
                'id': super_tournament.id,
                'name': super_tournament.name
            },
            'updated_teams': updated_teams
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@team_bp.route('/player/super-tournament-checkin', methods=['POST'])
def player_super_tournament_checkin():
    try:
        data = request.get_json()
        player_id = data.get('player_id')
        uuid = data.get('uuid')
        super_tournament_id = data.get('super_tournament_id')
        checked_in = data.get('checked_in', True)
        
        if not super_tournament_id:
            return jsonify({'error': 'super_tournament_id is required'}), 400
            
        if not player_id and not uuid:
            return jsonify({'error': 'Either player_id or uuid is required'}), 400
        
        # Get the player based on either player_id or uuid
        player = None
        if player_id:
            player = Player.query.get(player_id)
        elif uuid:
            player = Player.query.filter_by(uuid=uuid).first()
            
        if not player:
            return jsonify({'error': 'Player not found'}), 404
            
        # Verify player belongs to the specified super tournament
        if player.super_tournament_id != int(super_tournament_id):
            return jsonify({'error': 'Player does not belong to the specified super tournament'}), 400
            
        # Get the super tournament
        super_tournament = SuperTournament.query.get(super_tournament_id)
        if not super_tournament:
            return jsonify({'error': 'Super tournament not found'}), 404
            
        # Get all tournaments in this super tournament through seasons
        tournaments = []
        for season in super_tournament.seasons:
            tournaments.extend(season.tournaments)
            
        if not tournaments:
            return jsonify({'error': 'No tournaments found in this super tournament'}), 404
            
        # Update player's check-in status for the entire super tournament
        player.checked_in = checked_in
        
        # Update team statuses in all tournaments
        updated_tournaments = []
        for tournament in tournaments:
            # Find team in this tournament where player is either player1 or player2
            team = Team.query.filter(
                (Team.player1_uuid == player.uuid) | (Team.player2_uuid == player.uuid),
                Team.tournament_id == tournament.id
            ).first()
            
            if team:
                # Get the other player in the team
                other_player = None
                if team.player1_uuid == player.uuid and team.player2_uuid:
                    other_player = Player.query.filter_by(uuid=team.player2_uuid).first()
                elif team.player2_uuid == player.uuid and team.player1_uuid:
                    other_player = Player.query.filter_by(uuid=team.player1_uuid).first()
                
                # Check if all players in the team are checked in
                all_players_checked_in = player.checked_in and (not other_player or other_player.checked_in)
                
                # Update team check-in status
                team.checked_in = all_players_checked_in
                
                updated_tournaments.append({
                    'tournament_id': tournament.id,
                    'tournament_name': tournament.tournament_name,
                    'team': {
                        'team_id': team.team_id,
                        'name': team.name,
                        'checked_in': team.checked_in,
                        'all_players_checked_in': all_players_checked_in
                    }
                })

        db.session.commit()
        
        return jsonify({
            'message': 'Player check-in status updated successfully across super tournament',
            'player': {
                'id': player.id,
                'first_name': player.first_name,
                'last_name': player.last_name,
                'checked_in': player.checked_in
            },
            'super_tournament': {
                'id': super_tournament.id,
                'name': super_tournament.name
            },
            'updated_tournaments': updated_tournaments
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@team_bp.route('/player/lookup', methods=['GET'])
def lookup_player():
    try:
        # Get query parameters
        phone_number = request.args.get('phone')
        uuid = request.args.get('uuid')
        super_tournament_id = request.args.get('super_tournament_id')
        
        if not phone_number and not uuid:
            return jsonify({'error': 'Either phone number or uuid must be provided'}), 400
            
        # Build query based on provided parameters
        query = Player.query
        
        if phone_number:
            query = query.filter(Player.phone_number == phone_number)
        if uuid:
            query = query.filter(Player.uuid == uuid)
        if super_tournament_id:
            query = query.filter(Player.super_tournament_id == super_tournament_id)
            
        # Get the single matching player
        player = query.first()
        
        if not player:
            return jsonify({'error': 'No player found with the provided criteria'}), 404
            
        # Get super tournament info
        super_tournament = SuperTournament.query.get(player.super_tournament_id)
        if not super_tournament:
            return jsonify({'error': 'Super tournament not found'}), 404
            
        # Get all tournaments for this player through super tournament
        tournaments = []
        for season in super_tournament.seasons:
            tournaments.extend(season.tournaments)
            
        # Get all teams where player is either player1 or player2
        teams = []
        for tournament in tournaments:
            team = Team.query.filter(
                (Team.player1_uuid == player.uuid) | (Team.player2_uuid == player.uuid),
                Team.tournament_id == tournament.id
            ).first()
            
            if team:
                # Get teammate info if it exists
                teammate = None
                if team.player1_uuid == player.uuid and team.player2_uuid:
                    teammate = Player.query.filter_by(uuid=team.player2_uuid).first()
                elif team.player2_uuid == player.uuid and team.player1_uuid:
                    teammate = Player.query.filter_by(uuid=team.player1_uuid).first()
                    
                teams.append({
                    'tournament': {
                        'id': tournament.id,
                        'name': tournament.tournament_name,
                        'type': tournament.type
                    },
                    'team': {
                        'team_id': team.team_id,
                        'name': team.name,
                        'checked_in': team.checked_in,
                        'teammate': {
                            'id': teammate.id,
                            'uuid': teammate.uuid,
                            'first_name': teammate.first_name,
                            'last_name': teammate.last_name,
                            'checked_in': teammate.checked_in
                        } if teammate else None
                    }
                })
        
        response_data = {
            'player': {
                'id': player.id,
                'uuid': player.uuid,
                'first_name': player.first_name,
                'last_name': player.last_name,
                'gender': player.gender,
                'age': player.age,
                'phone_number': player.phone_number,
                'email': player.email,
                'skill_type': player.skill_type,
                'dupr_id': player.dupr_id,
                'checked_in': player.checked_in
            },
            'super_tournament': {
                'id': super_tournament.id,
                'name': super_tournament.name
            },
            'teams': teams
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@team_bp.route('/player/lookup-by-name', methods=['GET'])
def lookup_player_by_name():
    try:
        # Get query parameters
        first_name = request.args.get('first_name')
        last_name = request.args.get('last_name')
        super_tournament_id = request.args.get('super_tournament_id')
        
        if not first_name or not super_tournament_id:
            return jsonify({'error': 'first_name and super_tournament_id are required'}), 400
            
        # Build query based on provided parameters
        query = Player.query.filter(
            # Case-insensitive first name search
            func.lower(Player.first_name) == func.lower(first_name)
        )
        
        # Add last name filter if provided (case-insensitive)
        if last_name:
            query = query.filter(func.lower(Player.last_name) == func.lower(last_name))
            
        # Filter by super tournament
        query = query.filter(Player.super_tournament_id == super_tournament_id)
            
        # Get the single matching player
        player = query.first()
        
        if not player:
            return jsonify({'error': 'No player found with the provided criteria'}), 404
            
        # Get super tournament info
        super_tournament = SuperTournament.query.get(super_tournament_id)
        if not super_tournament:
            return jsonify({'error': 'Super tournament not found'}), 404
            
        # Get all tournaments for this player through super tournament
        tournaments = []
        for season in super_tournament.seasons:
            tournaments.extend(season.tournaments)
            
        # Get all teams where player is either player1 or player2
        teams = []
        for tournament in tournaments:
            team = Team.query.filter(
                (Team.player1_uuid == player.uuid) | (Team.player2_uuid == player.uuid),
                Team.tournament_id == tournament.id
            ).first()
            
            if team:
                # Get teammate info if it exists
                teammate = None
                if team.player1_uuid == player.uuid and team.player2_uuid:
                    teammate = Player.query.filter_by(uuid=team.player2_uuid).first()
                elif team.player2_uuid == player.uuid and team.player1_uuid:
                    teammate = Player.query.filter_by(uuid=team.player1_uuid).first()
                    
                teams.append({
                    'tournament': {
                        'id': tournament.id,
                        'name': tournament.tournament_name,
                        'type': tournament.type
                    },
                    'team': {
                        'team_id': team.team_id,
                        'name': team.name,
                        'checked_in': team.checked_in,
                        'teammate': {
                            'id': teammate.id,
                            'uuid': teammate.uuid,
                            'first_name': teammate.first_name,
                            'last_name': teammate.last_name,
                            'checked_in': teammate.checked_in
                        } if teammate else None
                    }
                })
        
        response_data = {
            'player': {
                'id': player.id,
                'uuid': player.uuid,
                'first_name': player.first_name,
                'last_name': player.last_name,
                'gender': player.gender,
                'age': player.age,
                'phone_number': player.phone_number,
                'email': player.email,
                'skill_type': player.skill_type,
                'dupr_id': player.dupr_id,
                'checked_in': player.checked_in
            },
            'super_tournament': {
                'id': super_tournament.id,
                'name': super_tournament.name
            },
            'teams': teams
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 