import sys
from app import app, db
from models import User, Company, UserCompany

def create_admin_user():
    with app.app_context():
        db.create_all()
        
        # Migração manual simples: Adicionar coluna full_name se não existir
        try:
            db.session.execute(db.text('ALTER TABLE users ADD COLUMN full_name TEXT'))
            db.session.commit()
            print("Column 'full_name' added to 'users' table.")
        except Exception:
            # Column already exists or other error we can ignore for now
            db.session.rollback()

        # Check if user exists
        username = 'weverton'
        full_name = 'Weverton Luis'
        user = User.query.filter_by(username=username).first()
        
        if user:
            user.full_name = full_name
            db.session.commit()
            print(f"User '{username}' updated with full name '{full_name}'.")
        else:
            # Create User
            user = User(username=username, full_name=full_name)
            user.set_password('17231723')
            db.session.add(user)
            db.session.commit()
            print(f"User '{username}' created with full name '{full_name}'.")

if __name__ == '__main__':
    create_admin_user()
