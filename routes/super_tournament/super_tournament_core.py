from flask import Blueprint, request, jsonify
from models import db, SuperTournament, Season, Tournament
from sqlalchemy.orm import joinedload

super_tournament_bp = Blueprint('super_tournament', __name__)

@super_tournament_bp.route('/super-tournaments', methods=['POST'])
def create_super_tournament():
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ['name', 'seasons']):
        return jsonify({"error": "Name and seasons are required"}), 400
    
    # Validate seasons data
    if not isinstance(data['seasons'], list) or len(data['seasons']) == 0:
        return jsonify({"error": "At least one season is required"}), 400
    
    # Validate each season has a name
    for season in data['seasons']:
        if not isinstance(season, dict) or 'name' not in season:
            return jsonify({"error": "Each season must have a name"}), 400
    
    try:
        # Create new super tournament
        super_tournament = SuperTournament(
            name=data['name'],
            description=data.get('description', '')
        )
        
        db.session.add(super_tournament)
        db.session.flush()  # Get the super_tournament.id without committing
        
        # Create seasons
        created_seasons = []
        for season_data in data['seasons']:
            season = Season(
                name=season_data['name'],
                super_tournament_id=super_tournament.id
            )
            db.session.add(season)
            created_seasons.append(season)
        
        db.session.commit()
        
        return jsonify({
            "message": "Super tournament created successfully",
            "super_tournament": {
                "id": super_tournament.id,
                "name": super_tournament.name,
                "description": super_tournament.description,
                "seasons": [{
                    "id": season.id,
                    "name": season.name
                } for season in created_seasons]
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@super_tournament_bp.route('/super-tournaments/<int:super_tournament_id>', methods=['GET'])
def get_super_tournament_details(super_tournament_id):
    try:
        # Query with eager loading of relationships
        super_tournament = SuperTournament.query.options(
            joinedload(SuperTournament.seasons).joinedload(Season.tournaments)
        ).get_or_404(super_tournament_id)
        
        # Build response data
        response_data = {
            'id': super_tournament.id,
            'name': super_tournament.name,
            'description': super_tournament.description,
            'seasons': []
        }
        
        for season in super_tournament.seasons:
            season_data = {
                'id': season.id,
                'name': season.name,
                'tournaments': []
            }
            
            for tournament in season.tournaments:
                tournament_data = {
                    'id': tournament.id,
                    'name': tournament.tournament_name,
                    'type': tournament.type,
                    'num_courts': tournament.num_courts
                }
                season_data['tournaments'].append(tournament_data)
                
            response_data['seasons'].append(season_data)
            
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500 

@super_tournament_bp.route('/super-tournaments', methods=['GET'])
def get_all_super_tournaments():
    try:
        super_tournaments = SuperTournament.query.all()
        return jsonify({
            'super_tournaments': [{
                'id': st.id,
                'name': st.name,
                'description': st.description
            } for st in super_tournaments]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500 