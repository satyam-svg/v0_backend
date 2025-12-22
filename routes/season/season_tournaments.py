from flask import request, jsonify
from models import Season, Tournament, db
from . import season_bp

@season_bp.route('/seasons/<int:season_id>/tournaments', methods=['GET'])
def get_season_tournaments(season_id):
    try:
        season = Season.query.get_or_404(season_id)
        tournaments = Tournament.query.filter_by(season_id=season_id).all()
        
        return jsonify({
            'season_id': season_id,
            'season_name': season.name,
            'tournaments': [{
                'id': t.id,
                'name': t.tournament_name,
                'type': t.type,
                'num_courts': t.num_courts
            } for t in tournaments]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500 