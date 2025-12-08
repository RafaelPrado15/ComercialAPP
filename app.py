from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from database import db, get_sql_server_connection
from models import User, Company, UserCompany

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables on startup (for dev simplicity)
with app.app_context():
    db.create_all()

@app.context_processor
def inject_company_context():
    active_company = None
    user_companies = []
    
    if current_user.is_authenticated:
        user_companies = current_user.companies
        active_id = session.get('active_company_id')
        
        if active_id:
            active_company = Company.query.get(active_id)
            # Verify user owns this company
            if active_company not in user_companies:
                 active_company = user_companies[0] if user_companies else None
                 if active_company:
                    session['active_company_id'] = active_company.id
        else:
            if user_companies:
                active_company = user_companies[0]
                session['active_company_id'] = active_company.id

    return dict(active_company=active_company, user_companies=user_companies, min=min, max=max)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('menu'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('menu'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            # Set default company on login
            if user.companies:
                session['active_company_id'] = user.companies[0].id
            else:
                 session.pop('active_company_id', None)
            return redirect(url_for('menu'))
        else:
            # flash('Usuário ou senha incorretos!', 'danger')
            # The frontend JS expects 401 or handled error.
            return jsonify({'error': 'Unauthorized'}), 401

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('active_company_id', None)
    logout_user()
    return redirect(url_for('login'))

@app.route('/set_company/<int:company_id>')
@login_required
def set_company(company_id):
    company = Company.query.get_or_404(company_id)
    if company in current_user.companies:
        session['active_company_id'] = company.id
        flash(f"Empresa alterada para {company.name}", "success")
    else:
        flash("Acesso negado a esta empresa.", "danger")
    
    # Redirect back to where the user came from, or menu
    return redirect(request.referrer or url_for('menu'))

@app.route('/menu')
@login_required
def menu():
    # Context processor handles injection, but we can verify here if needed
    active_company = None
    if current_user.companies:
        active_id = session.get('active_company_id')
        if active_id:
             active_company = Company.query.get(active_id)
        else:
             active_company = current_user.companies[0]
             session['active_company_id'] = active_company.id

    return render_template('menu.html', user_company=active_company)


@app.route('/rastreio')
@login_required
def rastreio():
    # Get active company from session (or context)
    active_id = session.get('active_company_id')
    user_company = Company.query.get(active_id) if active_id else None

    # Validate ownership just in case
    if not user_company or user_company not in current_user.companies:
         flash("Selecione uma empresa válida.", "warning")
         return redirect(url_for('menu'))
    
    # Mock data for when SQL Server is not available
    kanban_data = {
        'Pendentes': [],
        'Em Fábrica': [],
        'Faturado': []
    }

    conn = get_sql_server_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Select relevant columns
            query = "SELECT NumeroPedido, Vendedor, StatusPedido, Emissao, PrevisaoFaturamento, Cliente FROM N8N_InformacoesPedidos()"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            columns = [column[0] for column in cursor.description]
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            cod_cliente = user_company.cod_cliente
            
            for row in results:
                if str(row.get('Cliente')).strip() == str(cod_cliente).strip():
                    status = row.get('StatusPedido')
                    if status in kanban_data:
                        kanban_data[status].append(row)
                    else:
                        kanban_data.setdefault('Pendentes', []).append(row)

            conn.close()
        except Exception as e:
            flash(f"Erro ao buscar dados: {e}", "danger")
    else:
        # Mock mode
        kanban_data['Pendentes'].append({'NumeroPedido': '123', 'StatusPedido': 'Pendentes', 'Emissao': '20250101', 'PrevisaoFaturamento': '20250110'})
        kanban_data['Em Fábrica'].append({'NumeroPedido': '124', 'StatusPedido': 'Em Fábrica', 'Emissao': '20250102', 'PrevisaoFaturamento': '20250112'})
        kanban_data['Faturado'].append({'NumeroPedido': '125', 'StatusPedido': 'Faturado', 'Emissao': '20241220', 'PrevisaoFaturamento': '20241225'})

    return render_template('rastreio.html', kanban_data=kanban_data)


def fetch_commercial_data(cod_cliente, pedido=None, nota=None):
    """
    Helper to fetch commercial data using the provided complex query.
    """
    conn = get_sql_server_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        query = """
        SELECT
            F2_DOC AS NUM_NOTA,
            F2_VEND1,
            A3_NOME,
            F2_EMISSAO,
            F2_CLIENTE,
            A1_NOME,
            F2_VALBRUT,
            SD2APP.D2_PEDIDO,
            INFO_PED.StatusPedido,
            F2_CHVNFE
        FROM SF2010 AS SF2 WITH(NOLOCK)
        INNER JOIN SA3010 AS SA3 WITH(NOLOCK)
            ON SA3.A3_COD = SF2.F2_VEND1
            AND SA3.D_E_L_E_T_ = ''
            AND SA3.A3_MSBLQL <> '1'
        INNER JOIN SA1010 AS SA1 WITH(NOLOCK)
            ON SA1.A1_COD = SF2.F2_CLIENTE
            AND SA1.D_E_L_E_T_ = ''
            AND SA1.A1_MSBLQL <> '1'
        INNER JOIN (
            SELECT
            DISTINCT(D2_PEDIDO) AS D2_PEDIDO,
            D2_DOC,
            D2_LOJA,
            D2_SERIE,
            D2_CLIENTE
            FROM SD2010 AS SD2 WITH(NOLOCK)
            WHERE SD2.D_E_L_E_T_ = ''
            AND SD2.D2_PEDIDO <> ''
            ) AS SD2APP
            ON SD2APP.D2_DOC =  SF2.F2_DOC
            AND SD2APP.D2_SERIE = SF2.F2_SERIE
            AND SD2APP.D2_LOJA = SF2.F2_LOJA
            AND SD2APP.D2_CLIENTE = SF2.F2_CLIENTE
        LEFT JOIN N8N_InformacoesPedidos() AS INFO_PED
            ON INFO_PED.NumeroPedido = SD2APP.D2_PEDIDO
            AND INFO_PED.Vendedor = SF2.F2_VEND1
        WHERE SF2.D_E_L_E_T_ = ''
            AND (? = '' OR SF2.F2_VEND1 = ?) 
            AND (? = '' OR SD2APP.D2_PEDIDO = ?) 
            AND (? = '' OR SF2.F2_DOC = ?) 
            AND (? = '' OR SF2.F2_CLIENTE = ?) 
            AND SF2.F2_EMISSAO >= ? 
        ORDER BY SF2.F2_EMISSAO DESC
        """
        
        cod_repres = '' 
        p_pedido = pedido if pedido else ''
        p_nota = nota if nota else ''
        p_cliente = cod_cliente
        data_minima = '20240101'
        
        params = (cod_repres, cod_repres, p_pedido, p_pedido, p_nota, p_nota, p_cliente, p_cliente, data_minima)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [column[0] for column in cursor.description]
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
            
        conn.close()
        return results
        
    except Exception as e:
        print(f"Error fetching commercial data: {e}")
        return None

@app.route('/pedidos')
@login_required
def pedidos():
    active_id = session.get('active_company_id')
    user_company = Company.query.get(active_id) if active_id else None

    if not user_company or user_company not in current_user.companies:
         flash("Selecione uma empresa válida.", "warning")
         return redirect(url_for('menu'))

    data = fetch_commercial_data(user_company.cod_cliente)
    
    # Process for Unique Pedidos
    orders_list = []
    if data:
        seen = set()
        for row in data:
            pid = row['D2_PEDIDO']
            if pid not in seen:
                seen.add(pid)
                orders_list.append(row)
    
    # Mock data fallback
    if data is None:
        orders_list = [
            {'D2_PEDIDO': '123456', 'F2_EMISSAO': '20251101', 'F2_VALBRUT': 1500.00, 'StatusPedido': 'Faturado', 'NUM_NOTA': '000101'},
            {'D2_PEDIDO': '789012', 'F2_EMISSAO': '20251115', 'F2_VALBRUT': 2350.50, 'StatusPedido': 'Em Fábrica', 'NUM_NOTA': '-'}
        ]
        # Generate more mock data for pagination testing
        for i in range(1, 25):
             orders_list.append({'D2_PEDIDO': f'999{i:03d}', 'F2_EMISSAO': '20251201', 'F2_VALBRUT': 100.00 * i, 'StatusPedido': 'Pendente', 'NUM_NOTA': '-'})

    # Filtering
    search = request.args.get('search', '').lower()
    if search:
        orders_list = [o for o in orders_list if search in str(o.get('D2_PEDIDO', '')).lower() or search in str(o.get('StatusPedido', '')).lower()]

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_items = len(orders_list)
    total_pages = (total_items + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated_orders = orders_list[start:end]

    return render_template('pedidos.html', orders=paginated_orders, page=page, total_pages=total_pages, search=search)

@app.route('/pedidos/<id>')
@login_required
def pedido_detail(id):
    active_id = session.get('active_company_id')
    user_company = Company.query.get(active_id) if active_id else None

    if not user_company or user_company not in current_user.companies:
         return redirect(url_for('menu'))
         
    # Fetch specific
    data = fetch_commercial_data(user_company.cod_cliente, pedido=id)
    if data is None:
        data = [{'D2_PEDIDO': id, 'F2_EMISSAO': '20251101', 'F2_VALBRUT': 1500.00, 'StatusPedido': 'Faturado', 'NUM_NOTA': '000101', 'A1_NOME': 'Cliente Teste', 'A3_NOME': 'Vendedor Teste', 'F2_CHVNFE': '352511...0001'}]

    return render_template('pedido_detail.html', pedido=data[0] if data else None, items=data) 

@app.route('/notas')
@login_required
def notas():
    active_id = session.get('active_company_id')
    user_company = Company.query.get(active_id) if active_id else None

    if not user_company or user_company not in current_user.companies:
         flash("Selecione uma empresa válida.", "warning")
         return redirect(url_for('menu'))

    data = fetch_commercial_data(user_company.cod_cliente)
    
    # Process for Unique Notas
    invoices_list = []
    if data:
        seen = set()
        for row in data:
            nid = row['NUM_NOTA']
            if nid not in seen:
                seen.add(nid)
                invoices_list.append(row)
    
    if data is None:
        invoices_list = [
            {'NUM_NOTA': '000101', 'D2_PEDIDO': '123456', 'F2_EMISSAO': '20251101', 'F2_VALBRUT': 1500.00, 'F2_CHVNFE': '352511...'}
        ]
        for i in range(1, 15):
             invoices_list.append({'NUM_NOTA': f'00{i:04d}', 'D2_PEDIDO': f'99{i:04d}', 'F2_EMISSAO': '20251201', 'F2_VALBRUT': 500.00 * i, 'F2_CHVNFE': f'Key{i}'})

    # Filtering
    search = request.args.get('search', '').lower()
    if search:
        invoices_list = [n for n in invoices_list if search in str(n.get('NUM_NOTA', '')).lower() or search in str(n.get('D2_PEDIDO', '')).lower()]

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_items = len(invoices_list)
    total_pages = (total_items + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated_invoices = invoices_list[start:end]

    return render_template('notas.html', invoices=paginated_invoices, page=page, total_pages=total_pages, search=search)

@app.route('/notas/<id>')
@login_required
def nota_detail(id):
    active_id = session.get('active_company_id')
    user_company = Company.query.get(active_id) if active_id else None

    if not user_company or user_company not in current_user.companies:
         return redirect(url_for('menu'))
         
    # Fetch specific
    data = fetch_commercial_data(user_company.cod_cliente, nota=id)
    if data is None:
        data = [{'NUM_NOTA': id, 'D2_PEDIDO': '123456', 'F2_EMISSAO': '20251101', 'F2_VALBRUT': 1500.00, 'F2_CHVNFE': '352511...', 'A1_NOME': 'Cliente Teste'}]

    return render_template('nota_detail.html', nota=data[0] if data else None, items=data)


if __name__ == '__main__':
    # app.run(debug=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
