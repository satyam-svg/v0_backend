from flask import Blueprint
super_tournament_bp = Blueprint('super_tournament', __name__)

# Import views after creating blueprint
from .super_tournament_core import * 