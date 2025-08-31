from app import create_app
from models import db
import os
app = create_app()

print("FLASK_ENV:", os.getenv("FLASK_ENV"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
#Last one!