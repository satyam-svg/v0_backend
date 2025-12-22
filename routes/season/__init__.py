from flask import Blueprint
season_bp = Blueprint('season', __name__)

# Import views after creating blueprint
from .season_core import * 