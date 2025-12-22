from flask import Blueprint

team_bp = Blueprint('team', __name__)

# Import views after creating blueprint
from .team_core import *
from .team_registration import *
from .team_checkin import * 