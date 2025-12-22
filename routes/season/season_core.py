from flask import Blueprint, request, jsonify
from models import db, Season, SuperTournament

season_bp = Blueprint('season', __name__)

@season_bp.route('/seasons', methods=['GET'])
def get_all_seasons():
    try:
        seasons = Season.query.all()
        return jsonify({
            'seasons': [{
                'id': s.id,
                'name': s.name,
                'super_tournament_id': s.super_tournament_id,
                'super_tournament_name': s.super_tournament.name
            } for s in seasons]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@season_bp.route('/seasons', methods=['POST'])
def create_season():
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ['name', 'super_tournament_id']):
        return jsonify({"error": "Name and super_tournament_id are required"}), 400
        
    # Verify super tournament exists
    super_tournament = SuperTournament.query.get_or_404(data['super_tournament_id'])
    
    # Create new season
    season = Season(
        name=data['name'],
        super_tournament_id=super_tournament.id
    )
    
    try:
        db.session.add(season)
        db.session.commit()
        return jsonify({
            "message": "Season created successfully",
            "season_id": season.id,
            "season_name": season.name,
            "super_tournament": {
                "id": super_tournament.id,
                "name": super_tournament.name
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@season_bp.route('/super-tournaments/<int:super_tournament_id>/seasons', methods=['POST'])
def create_season_in_super_tournament(super_tournament_id):
    data = request.get_json()
    
    # Validate required fields
    if 'name' not in data:
        return jsonify({"error": "Name is required"}), 400
        
    # Verify super tournament exists
    super_tournament = SuperTournament.query.get_or_404(super_tournament_id)
    
    # Create new season
    season = Season(
        name=data['name'],
        super_tournament_id=super_tournament_id
    )
    
    try:
        db.session.add(season)
        db.session.commit()
        return jsonify({
            "message": "Season created successfully",
            "season_id": season.id,
            "season_name": season.name,
            "super_tournament": {
                "id": super_tournament.id,
                "name": super_tournament.name
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500