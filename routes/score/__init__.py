from flask import Blueprint

score_bp = Blueprint('score', __name__)

from . import score_core
from . import score_socket

# Import views after creating blueprint
from .score_core import *
from .score_points import *
from .score_reports import * 