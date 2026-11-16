"""Flask entry point — run this file to start the server."""
import os
from app import create_app

env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = env == "development" and os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true")
    app.run(debug=debug, port=port, host="0.0.0.0")
