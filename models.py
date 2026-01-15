from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

# Association Table for User-Company Many-to-Many relationship (optional, or One-to-Many logic)
# Requirement: "Gostaria de vincular o usuario a empresa."
# A user might be linked to one company or multiple. I'll use a simple table for now.

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    full_name = db.Column(db.String(128))
    password_hash = db.Column(db.String(128))
    
    # Relationship to companies
    companies = db.relationship('Company', secondary='user_companies', backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    cod_cliente = db.Column(db.String(6), unique=True) # Linked to SQL Server

class UserCompany(db.Model):
    __tablename__ = 'user_companies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
