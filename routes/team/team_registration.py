from flask import request, jsonify
from models import Team, Player, Tournament, db
from . import team_bp
import io
import csv
import random
import string

def generate_uuid():
    """Generate a 5-character alphanumeric UUID"""
    # Use uppercase letters and digits for better readability
    characters = string.ascii_uppercase + string.digits
    while True:
        new_uuid = ''.join(random.choices(characters, k=5))
        # Check if UUID already exists
        if not Player.query.filter_by(uuid=new_uuid).first():
            return new_uuid

def validate_phone_number(phone):
    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, phone))
    if not phone:
        return None
    return phone

@team_bp.route('/register-teams', methods=['POST'])
def register_teams():
    tournament_id = request.form.get('tournament_id')
    
    if not tournament_id:
        return jsonify({"error": "tournament_id is required"}), 400
    
    # Check if the tournament exists
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({"error": "Tournament not found"}), 404
        
    # Get super_tournament_id through season
    if not tournament.season or not tournament.season.super_tournament:
        return jsonify({"error": "Tournament must be part of a super tournament"}), 400
    super_tournament_id = tournament.season.super_tournament.id

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File is not a CSV"}), 400

    try:
        # Parse CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        # Verify required columns
        required_columns = {'Team ID', 'Name of Player', 'Phone Number'}
        columns = set(csv_reader.fieldnames)
        if not required_columns.issubset(columns):
            missing = required_columns - columns
            return jsonify({
                "error": f"Missing required columns: {', '.join(missing)}"
            }), 400

        for row in csv_reader:
            # Validate phone number
            phone_number = validate_phone_number(row.get('Phone Number', ''))
            if not phone_number:
                return jsonify({
                    "error": f"Invalid or missing phone number for player: {row['Name of Player']}"
                }), 400

            team_id = row['Team ID']
            team_name = row.get('Team Name', f'Team {team_id}')

            # Check if the team exists for this tournament
            existing_team = Team.query.filter_by(team_id=team_id, tournament_id=tournament_id).first()
            
            if existing_team:
                # Update existing team's details
                if team_name:
                    existing_team.name = team_name
                team = existing_team
            else:
                # Create a new team
                team = Team(
                    team_id=team_id,
                    name=team_name,
                    tournament_id=tournament_id
                )
                db.session.add(team)
                db.session.flush()

            # Process player information
            full_name = row['Name of Player'].strip()
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            # First try to find player by phone number in the super tournament
            existing_player = Player.query.filter_by(
                phone_number=phone_number,
                super_tournament_id=super_tournament_id
            ).first()

            if not existing_player:
                # If not found by phone, try by name in the super tournament
                existing_player = Player.query.filter_by(
                    first_name=first_name,
                    last_name=last_name,
                    super_tournament_id=super_tournament_id
                ).first()

            if existing_player:
                # Update existing player with any provided values
                if 'DUPR ID' in row:
                    existing_player.dupr_id = row['DUPR ID']
                if 'Email' in row:
                    existing_player.email = row['Email']
                if 'Gender' in row:
                    existing_player.gender = row['Gender']
                if 'Age' in row and row['Age'].strip().isdigit():
                    existing_player.age = int(row['Age'])
                if 'Skill Type' in row:
                    existing_player.skill_type = row['Skill Type']
                player = existing_player
            else:
                # Create new player with UUID
                player = Player(
                    first_name=first_name,
                    last_name=last_name,
                    uuid=generate_uuid(),
                    phone_number=phone_number,  # Mandatory field
                    email=row.get('Email', f"{first_name.lower()}.{last_name.lower()}@example.com"),
                    dupr_id=row.get('DUPR ID', ''),
                    gender=row.get('Gender', 'Not Specified'),
                    age=int(row['Age']) if row.get('Age', '').strip().isdigit() else 0,
                    skill_type=row.get('Skill Type', 'INTERMEDIATE'),
                    super_tournament_id=super_tournament_id  # Use super_tournament_id instead of tournament_id
                )
                db.session.add(player)
                db.session.flush()

            # Update team's player UUIDs
            if not team.player1_uuid:
                team.player1_uuid = player.uuid
            elif not team.player2_uuid and team.player1_uuid != player.uuid:
                team.player2_uuid = player.uuid

        db.session.commit()
        return jsonify({
            "message": "Teams and players registered or updated successfully for the tournament.",
            "tournament_id": tournament_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": f"An error occurred while processing the CSV file: {str(e)}",
            "tournament_id": tournament_id
        }), 500