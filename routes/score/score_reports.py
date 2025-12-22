from flask import request, jsonify, render_template
from models import Score, Match, Team, db
from sqlalchemy import func
from . import score_bp

@score_bp.route('/points/rounds/all', methods=['GET'])
def get_all_round_points():
    tournament_id = request.args.get('tournament_id')
    if not tournament_id:
        return jsonify({"error": "Tournament ID is required"}), 400
        
    # Get all rounds in the tournament
    rounds = db.session.query(Match.round_id).filter_by(tournament_id=tournament_id).distinct().all()
    round_points = {}
    
    for round_id in [r[0] for r in rounds]:
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
            
        round_points[round_id] = team_points
        
    return jsonify(round_points), 200

@score_bp.route('/points/cumulative/html', methods=['GET'])
def get_cumulative_points_html():
    tournament_id = request.args.get('tournament_id')
    if not tournament_id:
        return jsonify({"error": "Tournament ID is required"}), 400
        
    # Get all teams and their total points
    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    team_points = []
    
    for team in teams:
        total_points = db.session.query(func.sum(Score.score)).filter_by(team_id=team.team_id).scalar() or 0
        team_points.append({
            'team_name': team.name,
            'total_points': total_points
        })
        
    # Sort by points in descending order
    team_points.sort(key=lambda x: x['total_points'], reverse=True)
    
    return render_template('points.html', team_points=team_points)

@score_bp.route('/points/cumulative/<int:tournament_id>', methods=['GET'])
def get_cumulative_points(tournament_id):
    # Get all teams and their total points
    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    team_points = []
    
    for team in teams:
        total_points = db.session.query(func.sum(Score.score)).filter_by(team_id=team.team_id).scalar() or 0
        team_points.append({
            'team_id': team.team_id,
            'team_name': team.name,
            'total_points': total_points
        })
        
    # Sort by points in descending order
    team_points.sort(key=lambda x: x['total_points'], reverse=True)
    
    return jsonify(team_points), 200 