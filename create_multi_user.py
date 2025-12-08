from app import app, db
from models import User, Company, UserCompany

def create_multicompany_user():
    with app.app_context():
        # Ensure companies exist
        c1_code = '006964'
        c2_code = '004274'
        
        c1 = Company.query.filter_by(cod_cliente=c1_code).first()
        if not c1:
            c1 = Company(name='FW DISTRIBUIDORA LTDA.', cod_cliente=c1_code)
            db.session.add(c1)
            
        c2 = Company.query.filter_by(cod_cliente=c2_code).first()
        if not c2:
            c2 = Company(name='CAPITAL DISTRIBUIDORA DE PECAS', cod_cliente=c2_code)
            db.session.add(c2)
            
        db.session.commit()
        
        # Create user
        username = 'weverton'
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            user.set_password('123456')
            db.session.add(user)
            db.session.commit()
            print(f"User {username} created.")
        else:
            print(f"User {username} already exists.")
            
        # Link companies if not already linked
        # Refresh from session
        user = User.query.filter_by(username=username).first()
        c1 = Company.query.filter_by(cod_cliente=c1_code).first()
        c2 = Company.query.filter_by(cod_cliente=c2_code).first()
        
        if c1 not in user.companies:
            user.companies.append(c1)
        if c2 not in user.companies:
            user.companies.append(c2)
            
        db.session.commit()
        print(f"User {username} linked to companies {c1.name} and {c2.name}.")

if __name__ == '__main__':
    create_multicompany_user()
