from flask_socketio import emit
from socket_instance import socketio

@socketio.on('connect', namespace='/scores')
def handle_connect():
    print('Client connected to score updates')
    emit('connection_response', {'data': 'Connected to score updates'})

@socketio.on('disconnect', namespace='/scores')
def handle_disconnect():
    print('Client disconnected from score updates')

# Optional: Add subscription to specific tournaments/matches
@socketio.on('subscribe', namespace='/scores')
def handle_subscribe(data):
    tournament_id = data.get('tournament_id')
    match_id = data.get('match_id')
    
    if tournament_id:
        print(f'Client subscribed to tournament {tournament_id}')
        emit('subscription_response', {
            'status': 'subscribed',
            'tournament_id': tournament_id,
            'match_id': match_id
        }) 