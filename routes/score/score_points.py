from flask import request, jsonify
from models import Score, Match, Team, db
from sqlalchemy import func
from . import score_bp

@score_bp.route('/points', methods=['GET'])
def get_points():
    tournament_id = request.args.get('tournament_id')
    if not tournament_id:
        return jsonify({"error": "Tournament ID is required"}), 400
        
    # Get all teams in the tournament
    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    points_data = []
    
    for team in teams:
        total_points = db.session.query(func.sum(Score.score)).filter_by(team_id=team.team_id).scalar() or 0
        points_data.append({
            'team_id': team.team_id,
            'team_name': team.name,
            'total_points': total_points
        })
        
    return jsonify(points_data), 200

@score_bp.route('/points/pool', methods=['GET'])
def get_pool_points():
    tournament_id = request.args.get('tournament_id')
    pool = request.args.get('pool')
    
    if not tournament_id or not pool:
        return jsonify({"error": "Tournament ID and pool are required"}), 400
        
    # Get matches in the pool
    matches = Match.query.filter_by(tournament_id=tournament_id, pool=pool).all()
    match_ids = [match.id for match in matches]
    
    # Get scores for these matches
    scores = Score.query.filter(Score.match_id.in_(match_ids)).all()
    
    # Organize points by team
    team_points = {}
    for score in scores:
        if score.team_id not in team_points:
            team = Team.query.get(score.team_id)
            team_points[score.team_id] = {
                'team_name': team.name,
                'total_points': 0
            }
        team_points[score.team_id]['total_points'] += score.score
        
    return jsonify(team_points), 200

@score_bp.route('/points/round', methods=['GET'])
def get_round_points():
    tournament_id = request.args.get('tournament_id')
    round_id = request.args.get('round_id')
    
    if not tournament_id or not round_id:
        return jsonify({"error": "Tournament ID and round ID are required"}), 400
        
    # Get matches in the round
    matches = Match.query.filter_by(tournament_id=tournament_id, round_id=round_id).all()
    match_ids = [match.id for match in matches]
    
    # Get scores for these matches
    scores = Score.query.filter(Score.match_id.in_(match_ids)).all()
    
    # Organize points by team
    team_points = {}
    for score in scores:
        if score.team_id not in team_points:
            team = Team.query.get(score.team_id)
            team_points[score.team_id] = {
                'team_name': team.name,
                'total_points': 0
            }
        team_points[score.team_id]['total_points'] += score.score
        
    return jsonify(team_points), 200 