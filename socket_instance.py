from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

socketio = SocketIO(
    cors_allowed_origins="*", 
    async_mode='gevent',
    logger=True,
    engineio_logger=True,
    path='/socket.io',
    manage_session=False,
    websocket=True,
    ping_timeout=5,
    ping_interval=10,
    always_connect=True,
    async_handlers=True,
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1
)

def init_socketio(app):
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,     
        x_proto=1,    
        x_host=1,     
        x_prefix=1   
    )
    socketio.init_app(app)
    return socketio 