from flask import request, jsonify
from models import SuperTournament, Season, db
from . import super_tournament_bp

@super_tournament_bp.route('/super-tournaments/<int:super_tournament_id>/seasons', methods=['GET'])
def get_super_tournament_seasons(super_tournament_id):
    try:
        super_tournament = SuperTournament.query.get_or_404(super_tournament_id)
        seasons = Season.query.filter_by(super_tournament_id=super_tournament_id).all()
        
        return jsonify({
            'super_tournament_id': super_tournament_id,
            'super_tournament_name': super_tournament.name,
            'seasons': [{
                'id': s.id,
                'name': s.name
            } for s in seasons]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500 