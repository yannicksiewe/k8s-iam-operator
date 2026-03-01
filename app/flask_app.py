"""Legacy Flask app module.

This module is kept for backwards compatibility.
Use app.api instead.
"""

from app.api import create_app

# Create app instance for backwards compatibility
app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
