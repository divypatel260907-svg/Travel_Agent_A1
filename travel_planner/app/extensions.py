"""
Shared Flask extensions — created here, initialised in the app factory.

Importing from here (not from app) avoids circular imports.
"""
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db            = SQLAlchemy()
login_manager = LoginManager()
bcrypt        = Bcrypt()
limiter       = Limiter(key_func=get_remote_address)
