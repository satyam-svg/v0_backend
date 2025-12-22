from flask import jsonify
from models import Match, Score, Team, db

def get_cumulative_points_for_round(tournament_id):
    try:
        # Get all matches for the tournament
        matches = Match.query.filter_by(tournament_id=tournament_id).all()
        if not matches:
            return jsonify({'error': 'No matches found for this tournament'}), 404

        # Get all scores for these matches
        match_ids = [match.id for match in matches]
        scores = Score.query.filter(Score.match_id.in_(match_ids)).all()

        # Create a dictionary to store cumulative points and points difference for each team
        team_stats = {}
        for match in matches:
            # Get scores for this match
            match_scores = [s for s in scores if s.match_id == match.id]
            
            # Skip if we don't have both scores
            if len(match_scores) != 2:
                continue

            # Calculate points and points difference for both teams
            team1_score = next(s for s in match_scores if s.team_id == match.team1_id)
            team2_score = next(s for s in match_scores if s.team_id == match.team2_id)

            # Initialize team stats if not already done
            for team_id in [match.team1_id, match.team2_id]:
                if team_id not in team_stats:
                    team_stats[team_id] = {
                        'total_points': 0,
                        'points_difference': 0
                    }

            # Update team1 stats
            team_stats[match.team1_id]['total_points'] += team1_score.score
            team_stats[match.team1_id]['points_difference'] += (team1_score.score - team2_score.score)

            # Update team2 stats
            team_stats[match.team2_id]['total_points'] += team2_score.score
            team_stats[match.team2_id]['points_difference'] += (team2_score.score - team1_score.score)

        # Convert to list format for response
        standings = []
        for team_id, stats in team_stats.items():
            team = Team.query.get(team_id)
            if team:
                standings.append({
                    'team_id': team_id,
                    'team_name': team.name,
                    'total_points': stats['total_points'],
                    'points_difference': stats['points_difference']
                })

        return jsonify({
            'tournament_id': tournament_id,
            'standings': standings
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500 