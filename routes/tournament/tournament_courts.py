from flask import request, jsonify, current_app
from models import Tournament, Match, Team, Player, db
from sqlalchemy import or_
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from . import tournament_bp
import time
import json

@tournament_bp.route('/tournaments/<int:tournament_id>/courts', methods=['GET', 'PUT'])
def manage_tournament_courts(tournament_id):
    """Manage number of courts for a tournament"""
    if request.method == 'GET':
        tournament = Tournament.query.get_or_404(tournament_id)
        return jsonify({
            'tournament_id': tournament_id,
            'num_courts': tournament.num_courts
        })
        
    else:  # PUT method
        try:
            # Parse JSON data properly
            if not request.is_json:
                return jsonify({
                    'error': 'Content-Type must be application/json'
                }), 400

            data = request.get_json(force=True)  # Force JSON parsing
            if not isinstance(data, dict):
                return jsonify({
                    'error': 'Invalid JSON data'
                }), 400

            num_courts = int(data.get('num_courts', 0))  # Convert to int
            
            if num_courts < 1:
                return jsonify({
                    'error': 'num_courts must be a positive integer'
                }), 400
                
            tournament = Tournament.query.get_or_404(tournament_id)
            tournament.num_courts = num_courts
            db.session.commit()
            
            return jsonify({
                'message': 'Number of courts updated successfully',
                'tournament_id': tournament_id,
                'num_courts': num_courts
            })
            
        except ValueError as e:
            return jsonify({
                'error': 'num_courts must be a valid integer'
            }), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating courts: {str(e)}")
            return jsonify({
                'error': 'Internal server error while updating courts'
            }), 500

@tournament_bp.route('/tournaments/<int:tournament_id>/court-assignments', methods=['GET', 'POST'])
def handle_court_assignments(tournament_id):
    # Handles both getting and assigning courts
    if request.method == 'GET':
        # Get optional filter parameters
        pool = request.args.get('pool')
        search = request.args.get('search')
        
        # Base query for matches with checked-in players only
        query = Match.query.join(Team, or_(
            Match.team1_id == Team.team_id,
            Match.team2_id == Team.team_id
        )).filter(
            Match.tournament_id == tournament_id,
            Team.checked_in == True
        )
        
        # Apply pool filter if provided
        if pool:
            query = query.filter(Match.pool == pool)
            
        # Apply search filter if provided
        if search:
            query = query.join(Team.players).filter(or_(
                Player.first_name.ilike(f'%{search}%'),
                Player.last_name.ilike(f'%{search}%'),
                Team.name.ilike(f'%{search}%')
            ))
        
        matches = query.all()
        
        # Format response
        assignments = {}
        for i in range(1, Tournament.query.get(tournament_id).num_courts + 1):
            assignments[f"court_{i}"] = []
            
        for match in matches:
            match_data = {
                'match_id': match.id,
                'team1': {
                    'id': match.team1_id,
                    'name': Team.query.get(match.team1_id).name,
                    'checked_in': Team.query.get(match.team1_id).checked_in
                },
                'team2': {
                    'id': match.team2_id,
                    'name': Team.query.get(match.team2_id).name,
                    'checked_in': Team.query.get(match.team2_id).checked_in
                },
                'pool': match.pool,
                'round_id': match.round_id,
                'court_number': match.court_number,
                'court_order': match.court_order
            }
            
            if match.court_number:
                assignments[f"court_{match.court_number}"].append(match_data)
                
        return jsonify(assignments)
    else:  # POST method
        print("=== Debug Logs ===")  # Using print for immediate output
        print(f"Headers: {dict(request.headers)}")
        print(f"Content-Type: {request.content_type}")
        print(f"Raw Data: {request.get_data(as_text=True)}")
        
        try:
            # Detailed request logging
            current_app.logger.info("=== Request Details ===")
            current_app.logger.info(f"Headers: {dict(request.headers)}")
            current_app.logger.info(f"Content-Type: {request.content_type}")
            current_app.logger.info(f"Mimetype: {request.mimetype}")
            current_app.logger.info(f"Is JSON: {request.is_json}")
            
            raw_data = request.get_data(as_text=True)
            current_app.logger.info(f"Raw data: {raw_data}")
            current_app.logger.info(f"Raw data type: {type(raw_data)}")
            
            # Try direct JSON loads
            try:
                parsed_data = json.loads(raw_data)
                current_app.logger.info(f"Direct JSON parse result: {parsed_data}")
                current_app.logger.info(f"Direct JSON parse type: {type(parsed_data)}")
            except json.JSONDecodeError as e:
                current_app.logger.error(f"JSON decode error: {str(e)}")
            
            # Validate JSON content type
            if not request.is_json:
                current_app.logger.error("Request Content-Type is not application/json")
                return jsonify({
                    'error': 'Content-Type must be application/json'
                }), 400

            # Try parsing JSON
            try:
                data = request.get_json(force=True)
                current_app.logger.info(f"Parsed JSON data: {data}")
            except Exception as e:
                current_app.logger.error(f"JSON parsing error: {str(e)}")
                return jsonify({
                    'error': 'Failed to parse JSON data'
                }), 400

            if not isinstance(data, dict):
                current_app.logger.error(f"Invalid data type. Expected dict, got {type(data)}")
                return jsonify({
                    'error': 'Invalid JSON data'
                }), 400
            
            # Log data validation
            current_app.logger.info("Validating required fields...")
            current_app.logger.info(f"match_id: {data.get('match_id')}")
            current_app.logger.info(f"court_number: {data.get('court_number')}")
            current_app.logger.info(f"court_order: {data.get('court_order')}")
            
            # Extract and validate required fields
            try:
                match_id = int(data.get('match_id', 0))
                court_number = int(data.get('court_number', 0))
                court_order = int(data.get('court_order', 0))
                
                current_app.logger.info(f"Converted values - match_id: {match_id}, court_number: {court_number}, court_order: {court_order}")
            except ValueError as e:
                current_app.logger.error(f"Value conversion error: {str(e)}")
                return jsonify({
                    'error': 'All numeric fields must be valid integers'
                }), 400

            # Get match and verify it belongs to this tournament
            match = Match.query.filter_by(
                id=match_id, 
                tournament_id=tournament_id
            ).first()
            
            if not match:
                return jsonify({
                    "error": "Match not found or does not belong to this tournament"
                }), 404
            
            # Verify all players are checked in
            team1 = Team.query.get(match.team1_id)
            team2 = Team.query.get(match.team2_id)
            
            if not (team1 and team2):
                return jsonify({
                    "error": "One or both teams not found"
                }), 404
            
            if not (team1.checked_in and team2.checked_in):
                return jsonify({
                    "error": "Cannot assign court - all players must be checked in"
                }), 400
            
            # Update court assignment
            match.court_number = court_number
            match.court_order = court_order
            
            db.session.commit()
            
            return jsonify({
                "message": "Court assigned successfully",
                "match": {
                    "id": match.id,
                    "match_name": match.match_name,
                    "court_number": match.court_number,
                    "court_order": match.court_order,
                    "pool": match.pool,
                    "team1_id": match.team1_id,
                    "team2_id": match.team2_id
                }
            })
            
        except Exception as e:
            current_app.logger.error(f"Unexpected error in court assignment: {str(e)}")
            current_app.logger.error(f"Error type: {type(e)}")
            db.session.rollback()
            return jsonify({
                "error": "Internal server error while assigning court"
            }), 500

@tournament_bp.route('/tournaments/<int:tournament_id>/court-assignments/reorder', methods=['PUT'])
def reorder_courts(tournament_id):
    data = request.get_json()
    
    if not all(key in data for key in ['court_number', 'match_orders']):
        return jsonify({"error": "court_number and match_orders are required"}), 400
        
    try:
        # match_orders should be a list of {match_id: new_order} pairs
        for match_order in data['match_orders']:
            match = Match.query.filter_by(
                id=match_order['match_id'],
                tournament_id=tournament_id,
                court_number=data['court_number']
            ).first()
            
            if match:
                match.court_order = match_order['new_order']
            
        db.session.commit()
        
        return jsonify({
            "message": "Match order updated successfully",
            "court_number": data['court_number']
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def verify_player_checkins(match):
    """Helper function to verify all players are checked in"""
    team1 = Team.query.get(match.team1_id)
    team2 = Team.query.get(match.team2_id)
    
    if not (team1 and team2):
        return False, "One or both teams not found"
        
    if not (team1.checked_in and team2.checked_in):
        return False, "Cannot assign court - all players must be checked in"
        
    return True, None

@tournament_bp.route('/tournaments/<int:tournament_id>/pool-matches', methods=['GET'])
def get_pool_matches():
    """Get matches for a specific pool"""
    tournament_id = request.args.get('tournament_id')
    pool = request.args.get('pool')
    
    if not pool:
        return jsonify({'error': 'pool parameter is required'}), 400
        
    matches = Match.query.filter_by(
        tournament_id=tournament_id,
        pool=pool
    ).order_by(Match.court_order).all()
    
    matches_data = []
    for match in matches:
        team1 = Team.query.get(match.team1_id)
        team2 = Team.query.get(match.team2_id)
        
        matches_data.append({
            'match_id': match.id,
            'match_name': match.match_name,
            'team1': {
                'id': team1.team_id,
                'name': team1.name
            },
            'team2': {
                'id': team2.team_id,
                'name': team2.name
            },
            'court_number': match.court_number,
            'court_order': match.court_order,
            'status': match.status
        })
    
    return jsonify({
        'pool': pool,
        'matches': matches_data
    })

@tournament_bp.route('/tournaments/<int:tournament_id>/reorder-matches', methods=['PUT'])
def reorder_matches():
    """Reorder matches within a pool or court"""
    data = request.get_json()
    
    if not all(key in data for key in ['matches', 'type']):
        return jsonify({"error": "matches and type are required"}), 400
    
    # type can be either 'pool' or 'court'
    if data['type'] not in ['pool', 'court']:
        return jsonify({"error": "type must be either 'pool' or 'court'"}), 400
        
    try:
        # matches should be a list of {match_id: order} pairs
        for match_data in data['matches']:
            match = Match.query.get_or_404(match_data['match_id'])
            match.court_order = match_data['order']
            
        db.session.commit()
        
        return jsonify({
            "message": "Match order updated successfully",
            "type": data['type']
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/tournaments/<int:tournament_id>/court-matches', methods=['GET'])
def get_court_matches(tournament_id):
    """Get all matches assigned to a specific court"""
    court_number = request.args.get('court_number')
    
    if not court_number:
        return jsonify({'error': 'court_number parameter is required'}), 400
        
    matches = Match.query.filter_by(
        tournament_id=tournament_id,
        court_number=court_number
    ).order_by(Match.court_order).all()
    
    matches_data = []
    for match in matches:
        team1 = Team.query.get(match.team1_id)
        team2 = Team.query.get(match.team2_id)
        
        matches_data.append({
            'match_id': match.id,
            'match_name': match.match_name,
            'team1': {
                'id': team1.team_id,
                'name': team1.name
            },
            'team2': {
                'id': team2.team_id,
                'name': team2.name
            },
            'court_number': match.court_number,
            'court_order': match.court_order,
            'status': match.status
        })
    
    return jsonify({
        'court_number': court_number,
        'matches': matches_data
    })

@tournament_bp.route('/tournaments/<int:tournament_id>/assign-to-court', methods=['POST'])
def assign_match_to_court():
    """Assign a match to a court with an order"""
    data = request.get_json()
    
    required_fields = ['match_id', 'court_number', 'court_order']
    if not all(field in data for field in required_fields):
        return jsonify({'error': f'Required fields: {", ".join(required_fields)}'}), 400
        
    try:
        match = Match.query.filter_by(
            id=data['match_id'], 
            tournament_id=tournament_id
        ).first()
        
        if not match:
            return jsonify({'error': 'Match not found'}), 404
            
        # Verify tournament has enough courts
        tournament = Tournament.query.get(tournament_id)
        if not tournament or data['court_number'] > tournament.num_courts:
            return jsonify({'error': 'Invalid court number for this tournament'}), 400
            
        # Verify players are checked in
        is_valid, error_message = verify_player_checkins(match)
        if not is_valid:
            return jsonify({'error': error_message}), 400
            
        match.court_number = data['court_number']
        match.court_order = data['court_order']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Match assigned to court successfully',
            'match_id': match.id,
            'court_number': match.court_number,
            'court_order': match.court_order
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/tournaments/<int:tournament_id>/reorder-court', methods=['PUT'])
def reorder_court_matches():
    """Reorder matches within a court"""
    data = request.get_json()
    
    if not all(key in data for key in ['court_number', 'match_orders']):
        return jsonify({"error": "court_number and match_orders are required"}), 400
        
    try:
        # match_orders should be a list of {match_id: new_order} pairs
        for match_order in data['match_orders']:
            match = Match.query.filter_by(
                id=match_order['match_id'],
                tournament_id=tournament_id,
                court_number=data['court_number']
            ).first()
            
            if match:
                match.court_order = match_order['new_order']
            
        db.session.commit()
        
        return jsonify({
            "message": "Court match order updated successfully",
            "court_number": data['court_number']
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500