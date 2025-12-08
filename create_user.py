import sys
from app import app, db
from models import User, Company, UserCompany

def create_admin_user():
    with app.app_context():
        db.create_all()
        
        # Check if user exists
        if User.query.filter_by(username='admin').first():
            print("User 'admin' already exists.")
            return

        # Create Company
        # Using a dummy code linked to the SQL Server logic
        # You can change '000189' to a valid client code if you have one
        company = Company(name='Empresa Exemplo', cod_cliente='000189')
        db.session.add(company)
        db.session.commit()
        
        # Create User
        user = User(username='admin')
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        
        # Link
        link = UserCompany(user_id=user.id, company_id=company.id)
        db.session.add(link)
        db.session.commit()
        
        print("User 'admin' created with password 'admin123' and linked to 'Empresa Exemplo'.")

if __name__ == '__main__':
    create_admin_user()
