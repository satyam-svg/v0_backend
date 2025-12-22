from flask import request, jsonify
from models import Team, Player, Tournament, Round, db, SuperTournament
from . import team_bp
import uuid

def generate_uuid():
    return str(uuid.uuid4())

@team_bp.route('/player/register', methods=['POST'])
def register_player():
    data = request.json
    required_fields = ['tournament_id', 'match_type', 'first_name', 'last_name', 
                      'gender', 'age', 'mobile_number', 'email', 'skill_type']
    
    # Validate required fields
    if not all(field in data for field in required_fields):
        return jsonify({'error': f'Missing required fields. Required: {", ".join(required_fields)}'}), 400
    
    # Validate match type
    valid_match_types = ['singles', 'doubles']
    match_type = data['match_type'].lower()
    if match_type not in valid_match_types:
        return jsonify({'error': 'Invalid match type. Must be either singles or doubles'}), 400
    
    # Validate skill type
    valid_skill_types = ['beginner', 'intermediate', 'advanced', 'professional']
    skill_type = data['skill_type'].lower()
    if skill_type not in valid_skill_types:
        return jsonify({'error': f'Invalid skill type. Must be one of: {", ".join(valid_skill_types)}'}), 400
    
    # Check if tournament exists and get super_tournament_id
    tournament = Tournament.query.get(data['tournament_id'])
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404
    
    if not tournament.season or not tournament.season.super_tournament:
        return jsonify({'error': 'Tournament must be part of a super tournament'}), 400
    
    super_tournament_id = tournament.season.super_tournament.id
    
    try:
        # Check if player already exists in this super tournament by phone number
        existing_player = Player.query.filter_by(
            phone_number=data['mobile_number'],
            super_tournament_id=super_tournament_id
        ).first()
        
        if existing_player:
            player1 = existing_player
            # Update player details if provided
            if 'dupr_id' in data:
                player1.dupr_id = data['dupr_id']
        else:
            # Create first player with UUID
            player1 = Player(
                first_name=data['first_name'],
                last_name=data['last_name'],
                gender=data['gender'],
                age=data['age'],
                phone_number=data['mobile_number'],
                email=data['email'],
                skill_type=skill_type,
                dupr_id=data.get('dupr_id'),  # Optional field
                super_tournament_id=super_tournament_id,
                uuid=generate_uuid()
            )
            db.session.add(player1)
        
        # Generate team_id
        team_count = Team.query.filter_by(tournament_id=data['tournament_id']).count()
        new_team_id = f"{data['tournament_id']}_{team_count + 1}"
        
        # Create new team
        team = Team(
            team_id=new_team_id,
            name=f"Team {team_count + 1}",
            tournament_id=data['tournament_id'],
            player1_uuid=player1.uuid
        )
        db.session.add(team)
        
        # Initialize response data
        response_data = {
            'message': 'Registration successful',
            'team_id': team.team_id,
            'players': [player1.id]
        }
        
        if match_type == 'doubles':
            if 'player2' not in data:
                db.session.rollback()
                return jsonify({'error': 'Second player details required for doubles'}), 400

            player2_data = data['player2']
            required_player2_fields = ['first_name', 'last_name', 'gender', 'age',
                                     'mobile_number', 'email', 'skill_type']
            
            if not all(field in player2_data for field in required_player2_fields):
                db.session.rollback()
                return jsonify({'error': f'Missing required fields for player 2. Required: {", ".join(required_player2_fields)}'}), 400
            
            # Validate player2 skill type
            skill_type2 = player2_data['skill_type'].lower()
            if skill_type2 not in valid_skill_types:
                db.session.rollback()
                return jsonify({'error': f'Invalid skill type for player 2. Must be one of: {", ".join(valid_skill_types)}'}), 400
            
            # Check if player2 already exists in this super tournament
            existing_player2 = Player.query.filter_by(
                phone_number=player2_data['mobile_number'],
                super_tournament_id=super_tournament_id
            ).first()
            
            if existing_player2:
                player2 = existing_player2
                # Update player2 details if provided
                if 'dupr_id' in player2_data:
                    player2.dupr_id = player2_data['dupr_id']
            else:
                # Create second player with UUID
                player2 = Player(
                    first_name=player2_data['first_name'],
                    last_name=player2_data['last_name'],
                    gender=player2_data['gender'],
                    age=player2_data['age'],
                    phone_number=player2_data['mobile_number'],
                    email=player2_data['email'],
                    skill_type=skill_type2,
                    dupr_id=player2_data.get('dupr_id'),  # Optional field
                    super_tournament_id=super_tournament_id,
                    uuid=generate_uuid()
                )
                db.session.add(player2)
            
            # Set player2_uuid in team
            team.player2_uuid = player2.uuid
            
            # Add player2 ID to response
            response_data['players'].append(player2.id)
        
        db.session.commit()
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@team_bp.route('/teams', methods=['GET'])
def get_all_teams():
    pool = request.args.get('pool')
    round_id = request.args.get('round_id')
    tournament_id = request.args.get('tournament_id')

    # Validate that pool, round_id, and tournament_id are present
    if not pool or not round_id or not tournament_id:
        return jsonify({'error': 'pool, round_id, and tournament_id are required'}), 400

    if not round_id.isdigit() or not tournament_id.isdigit():
        return jsonify({'error': 'Round ID and Tournament ID must be numbers'}), 400

    try:
        # Convert round_id and tournament_id to integers
        round_id = int(round_id)
        tournament_id = int(tournament_id)

        # Check if the tournament exists
        tournament = Tournament.query.filter_by(id=tournament_id).first()
        if not tournament:
            return jsonify({'error': 'Tournament not found'}), 404

        # Query the Round model to get teams in the specified pool, round, and tournament
        rounds = Round.query.filter_by(pool=pool, round_id=round_id, tournament_id=tournament_id).all()

        if not rounds:
            return jsonify({'error': 'No teams found for the provided pool, round, and tournament'}), 404

        # Retrieve team names and IDs for the matched entries
        teams = []
        for round_entry in rounds:
            team = Team.query.get(round_entry.team_id)
            if team:
                team_data = {
                    'team_id': team.team_id,
                    'name': team.name,
                    'player1': None,
                    'player2': None
                }
                
                # Add player1 info if exists
                if team.player1_uuid:
                    player1 = Player.query.filter_by(uuid=team.player1_uuid).first()
                    if player1:
                        team_data['player1'] = {
                            'id': player1.id,
                            'uuid': player1.uuid,
                            'name': f"{player1.first_name} {player1.last_name}".strip()
                        }
                
                # Add player2 info if exists
                if team.player2_uuid:
                    player2 = Player.query.filter_by(uuid=team.player2_uuid).first()
                    if player2:
                        team_data['player2'] = {
                            'id': player2.id,
                            'uuid': player2.uuid,
                            'name': f"{player2.first_name} {player2.last_name}".strip()
                        }
                
                teams.append(team_data)

        return jsonify({
            'round_id': round_id,
            'pool': pool,
            'tournament_id': tournament_id,
            'teams': teams
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@team_bp.route('/player/update', methods=['PUT'])
def update_player():
    data = request.get_json()
    
    if 'uuid' not in data:
        return jsonify({"error": "Player UUID is required"}), 400
        
    # Get the player
    player = Player.query.filter_by(uuid=data['uuid']).first()
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    # Remove super_tournament_id if it's in the request data to prevent any changes
    if 'super_tournament_id' in data:
        return jsonify({"error": "Changing super tournament is not allowed"}), 400
    
    # Update player fields if provided
    if 'first_name' in data:
        player.first_name = data['first_name']
    if 'last_name' in data:
        player.last_name = data['last_name']
    if 'gender' in data:
        player.gender = data['gender']
    if 'age' in data:
        player.age = data['age']
    if 'phone_number' in data:
        # Check if phone number is already used by another player in the same super tournament
        existing_player = Player.query.filter(
            Player.phone_number == data['phone_number'],
            Player.super_tournament_id == player.super_tournament_id,
            Player.uuid != player.uuid
        ).first()
        if existing_player:
            return jsonify({
                "error": "Phone number already registered to another player in this super tournament"
            }), 400
        player.phone_number = data['phone_number']
    if 'email' in data:
        player.email = data['email']
    if 'skill_type' in data:
        player.skill_type = data['skill_type']
    if 'dupr_id' in data:
        player.dupr_id = data['dupr_id']
        
    try:
        db.session.commit()
        
        # Get super tournament info
        super_tournament = SuperTournament.query.get(player.super_tournament_id)
        
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
        
        return jsonify({
            "message": "Player updated successfully",
            "player": {
                "uuid": player.uuid,
                "first_name": player.first_name,
                "last_name": player.last_name,
                "gender": player.gender,
                "age": player.age,
                "phone_number": player.phone_number,
                "email": player.email,
                "skill_type": player.skill_type,
                "dupr_id": player.dupr_id,
                "checked_in": player.checked_in
            },
            "super_tournament": {
                "id": super_tournament.id,
                "name": super_tournament.name
            },
            "teams": teams
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500