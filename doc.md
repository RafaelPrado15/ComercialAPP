Setup instructions
Install Dependencies: The dependencies are listed in 
requirements.txt
.

pip install -r requirements.txt
Environment Configuration: Configure your SQL Server credentials in 
config.py
 or .env file if they differ from the defaults provided.

SQL_SERVER_HOST: Host address of your SQL Server.
SQL_SERVER_DB: Database name.
SQL_SERVER_USER / SQL_SERVER_PASSWORD: Credentials (defaults set).
Initialize Data: Run the helper script to create the initial admin user.

python create_user.py
This creates a user:

Username: 
admin
Password: admin123
Company: Linked to client code 000189 (Pradolux default in prompt).
Run the Application:

python app.py
Access the portal at http://127.0.0.1:5000.

Verification Steps
1. Login
Navigate to /. You should be redirected to /login.
Enter 
admin
 / admin123.
Verify you are redirected to the Menu.
2. Menu Dashboard
Verify buttons for "Rastreio", "Pedidos", and "Notas" are visible (since the user is linked to a company).
3. Rastreio (Tracking)
Click "Rastreio".
Verify the Kanban board loads.
Note: If your SQL Server is reachable, you will see real data. If not, you will see Mock Data (Sample orders in Pendentes/Em Fábrica/Faturado).
4. Pedidos (Orders)
Click "Pedidos".
Verify the list of orders.
Click "Detalhes" on an order to see the detail view.
5. Notas (Invoices)
Click "Notas".
Verify the list of invoices.
Click "Detalhes" on an invoice to see the detail view.
Notes on Implementation
Data Integration: The app attempts to connect to the SQL Server first. If the connection fails, it falls back to Mock Data so you can verify the UI and flow without a live database.
Security: Passwords are hashed. Access to internal pages is protected by @login_required.
Assets: The logo is loaded from static/img/logoPradolux.png.