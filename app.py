from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import requests
from io import BytesIO
from datetime import datetime, timedelta
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

def get_all_representatives():
    """
    Fetches all active representatives from SA3010 table.
    """
    conn = get_sql_server_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        query = """
        SELECT A3_COD, A3_NOME FROM SA3010 
        WHERE D_E_L_E_T_ <> '*' 
          AND A3_MSBLQL <> '1'
          AND A3_COD < '999990'
        ORDER BY A3_NOME
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        reps = []
        for row in rows:
            reps.append({'id': row[0].strip(), 'name': row[1].strip()})
        return reps
    except Exception as e:
        print(f"Error fetching representatives: {e}")
        return []

@app.context_processor
def inject_representative_context():
    active_representative = None
    all_representatives = []
    
    if current_user.is_authenticated:
        # For managers, we fetch all representatives from ERP
        all_representatives = get_all_representatives()
        
        active_id = session.get('active_representative_id')
        
        if active_id:
            # Find the active representative in the list
            for rep in all_representatives:
                if rep['id'] == active_id:
                    active_representative = rep
                    break
            
            if not active_representative and all_representatives:
                active_representative = all_representatives[0]
                session['active_representative_id'] = active_representative['id']
        else:
            if all_representatives:
                active_representative = all_representatives[0]
                session['active_representative_id'] = active_representative['id']

    return dict(active_representative=active_representative, all_representatives=all_representatives, min=min, max=max)

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
            return redirect(url_for('menu'))
        else:
            # flash('Usuário ou senha incorretos!', 'danger')
            # The frontend JS expects 401 or handled error.
            return jsonify({'error': 'Unauthorized'}), 401

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('active_representative_id', None)
    logout_user()
    return redirect(url_for('login'))

@app.route('/set_representative/<string:rep_id>')
@login_required
def set_representative(rep_id):
    # Since managers can see all, we just set the ID in session
    # In a more restricted app, we'd verify if the user has access to this rep_id
    session['active_representative_id'] = rep_id
    flash(f"Representante alterado.", "success")
    
    # Redirect back to where the user came from, or menu
    return redirect(request.referrer or url_for('menu'))

@app.route('/menu')
@login_required
def menu():
    # Context processor handles injection of active_representative
    return render_template('menu.html')


@app.route('/rastreio')
@login_required
def rastreio():
    # Get active representative from session
    active_rep_id = session.get('active_representative_id')

    if not active_rep_id:
         flash("Selecione um representante válido.", "warning")
         return redirect(url_for('menu'))
    
    # Date Filtering
    # Default to last 30 days if not provided
    today = datetime.now()
    default_start = (today - timedelta(days=60)).strftime('%Y-%m-%d')
    default_end = today.strftime('%Y-%m-%d')
    
    start_date = request.args.get('start_date', default_start)
    end_date = request.args.get('end_date', default_end)
    
    # Format dates for SQL (YYYYMMDD)
    try:
        dt_start = datetime.strptime(start_date, '%Y-%m-%d')
        dt_end = datetime.strptime(end_date, '%Y-%m-%d')
        site_start = dt_start.strftime('%Y%m%d')
        site_end = dt_end.strftime('%Y%m%d')
    except ValueError:
        flash("Formato de data inválido.", "danger")
        start_date = default_start
        end_date = default_end
        site_start = (today - timedelta(days=60)).strftime('%Y%m%d')
        site_end = today.strftime('%Y%m%d')
        
    order_number = request.args.get('order_number', '')

    print(f"DEBUG: start_date={start_date}, end_date={end_date}, order_number={order_number}")
    print(f"DEBUG: site_start={site_start}, site_end={site_end}")
    
    if start_date != default_start or end_date != default_end:
        flash(f"Filtrando de {start_date} até {end_date}", "info")

    kanban_data = {
        'Comercial': [],
        'Produção': [],
        'Separação': [],
        'Conferência': [],
        'Faturado': []
    }

    conn = get_sql_server_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Base Query
            query = """
            SELECT 
                SC5.C5_NUM AS NumeroPedido,
                SC5.C5_VEND1 AS CodRepresentante,
                SC5.C5_CLIENTE AS CodCliente, 
                RTRIM(LTRIM(SA1.A1_NOME)) AS Cliente,
                SC5.C5_EMISSAO AS Emissao,
                SC5.C5_FECENT AS PrevisaoFaturamento,
                SC5.C5_XPEDAGE AS Agendado,
                SC5.C5_EVENTO AS Evento,
                CASE 
                    WHEN SC5.C5_EVENTO IN ('1', '2') THEN 'Pedido No Comercial'
                    WHEN SC5.C5_EVENTO IN ('9', '5') AND SC5.C5_SEPARA = 'F' THEN 'Pedido Em Produção'
                    WHEN SC5.C5_EVENTO IN ('5') AND SC5.C5_SEPARA = 'T' THEN 'Pedido Em Separação'
                    WHEN SC5.C5_EVENTO IN ('6') THEN 'Pedido Em Conferência'
                    WHEN SC5.C5_EVENTO IN ('7') THEN 'Pedido Em Faturamento'
                    ELSE '' 
                END AS EventoFormatado
            FROM SC5010 SC5 WITH(NOLOCK) 
            INNER JOIN SA1010 SA1 WITH(NOLOCK) 
                ON SA1.A1_FILIAL = '' 
                AND SA1.A1_COD = SC5.C5_CLIENTE 
                AND SA1.A1_LOJA = SC5.C5_LOJACLI 
                AND SA1.D_E_L_E_T_ = ''
            WHERE SC5.C5_FILIAL = '0101'
            AND SC5.D_E_L_E_T_ = ''
            AND SC5.C5_EVENTO IN ('1', '2', '5', '6', '7', '9')
            AND SC5.C5_VEND1 = ?
            AND SC5.C5_EMISSAO BETWEEN ? AND ?
            """
            
            params = [active_rep_id, site_start, site_end]
            
            if order_number:
                query += " AND SC5.C5_NUM LIKE ? "
                params.append(f"%{order_number}%")
            
            query += " ORDER BY SC5.C5_EMISSAO DESC"
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            columns = [column[0] for column in cursor.description]
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            conn.close()
            
            # Categorize results into Kanban
            for row in results:
                evento_fmt = row.get('EventoFormatado')
                
                if 'Pedido No Comercial' in evento_fmt:
                    kanban_data['Comercial'].append(row)
                elif 'Pedido Em Produção' in evento_fmt:
                    kanban_data['Produção'].append(row)
                elif 'Pedido Em Separação' in evento_fmt:
                    kanban_data['Separação'].append(row)
                elif 'Pedido Em Conferência' in evento_fmt:
                    kanban_data['Conferência'].append(row)
                elif 'Pedido Em Faturamento' in evento_fmt:
                    kanban_data['Faturado'].append(row)
                else:
                    # Fallback
                    kanban_data.setdefault('Comercial', []).append(row)

        except Exception as e:
            flash(f"Erro ao buscar dados: {e}", "danger")
    else:
        # Mock mode with current dates
        m_today = datetime.now()
        # Mock data (unchanged)
        kanban_data['Comercial'].append({
            'NumeroPedido': 'MOCK123', 
            'Emissao': (m_today - timedelta(days=2)).strftime('%Y%m%d'), 
            'PrevisaoFaturamento': (m_today + timedelta(days=5)).strftime('%Y%m%d'), 
            'EventoFormatado': 'Pedido No Comercial',
            'Agendado': ''
        })
        kanban_data['Produção'].append({
            'NumeroPedido': 'MOCK124', 
            'Emissao': (m_today - timedelta(days=10)).strftime('%Y%m%d'), 
            'PrevisaoFaturamento': (m_today + timedelta(days=2)).strftime('%Y%m%d'), 
            'EventoFormatado': 'Pedido Em Produção',
            'Agendado': ''
        })

    return render_template('rastreio.html', kanban_data=kanban_data, start_date=start_date, end_date=end_date, order_number=order_number)



def get_customer_name(cod_cliente):
    """
    Fetches the customer name (A1_NOME) from SA1010 table for a given client code (A1_COD).
    """
    conn = get_sql_server_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        query = "SELECT A1_NOME FROM SA1010 WITH(NOLOCK) WHERE A1_COD = ? AND D_E_L_E_T_ = ''"
        cursor.execute(query, (cod_cliente,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0].strip()
        return None
    except Exception as e:
        print(f"Error fetching customer name: {e}")
        return None

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
            AND SF2.F2_VEND1 = ? 
            AND (? = '' OR SD2APP.D2_PEDIDO = ?) 
            AND (? = '' OR SF2.F2_DOC = ?) 
            AND (? = '' OR SF2.F2_CLIENTE = ?) 
            AND SF2.F2_EMISSAO >= ? 
        ORDER BY SF2.F2_EMISSAO DESC
        """
        
        cod_repres = cod_cliente # In this function, cod_cliente parameter is being reused for Vendedor
        p_pedido = pedido if pedido else ''
        p_nota = nota if nota else ''
        p_cliente = '' # Removing client filter to see all from rep
        data_minima = '20240101'
        
        params = (cod_repres, p_pedido, p_pedido, p_nota, p_nota, p_cliente, p_cliente, data_minima)
        
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

@app.route('/notas_fiscais')
@login_required
def notas_fiscais():
    active_id = session.get('active_representative_id')
    if not active_id:
         flash("Selecione um representante.", "warning")
         return redirect(url_for('menu'))

    data = fetch_commercial_data(active_id)
    
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

    return render_template('notas_fiscais.html', orders=paginated_orders, page=page, total_pages=total_pages, search=search)

@app.route('/notas_fiscais/<id>')
@login_required
def nota_fiscal_detail(id):
    active_id = session.get('active_representative_id')
    if not active_id:
         return redirect(url_for('menu'))
         
    # Fetch specific
    data = fetch_commercial_data(active_id, pedido=id)
    if data is None:
        data = [{'D2_PEDIDO': id, 'F2_EMISSAO': '20251101', 'F2_VALBRUT': 1500.00, 'StatusPedido': 'Faturado', 'NUM_NOTA': '000101', 'A1_NOME': 'Cliente Teste', 'A3_NOME': 'Vendedor Teste', 'F2_CHVNFE': '352511...0001'}]

    return render_template('nota_fiscal_detail.html', pedido=data[0] if data else None, items=data)

@app.route('/notas_fiscais/download_nfe/<path:nfe_key>')
@login_required
def download_nfe(nfe_key):
    """
    Proxy to download NFE PDF from internal server.
    """
    # 1. Fetch JSON with PDF URL
    # https://192.168.117.11:8015/rest/GetDANFE/{chave}
    json_url = f"https://192.168.117.11:8015/rest/GetDANFE/{nfe_key}"
    
    try:
        # Verify=False because internal self-signed certs might issue warnings
        resp = requests.get(json_url, verify=False, timeout=10)
        
        if resp.status_code != 200:
            flash(f"Erro ao consultar DANFE: Status {resp.status_code}", "danger")
            return redirect(request.referrer or url_for('notas_fiscais'))
            
        data = resp.json()
        
        # Structure: {"RETORNOS": {"DANFE": "url...", "XML": "url..."}}
        pdf_url = data.get('RETORNOS', {}).get('DANFE')
        
        if not pdf_url:
             flash("URL do PDF não encontrada na resposta do servidor.", "warning")
             return redirect(request.referrer or url_for('notas_fiscais'))
             
        # 2. Download the PDF
        # The URL in JSON might be http usually.
        pdf_resp = requests.get(pdf_url, verify=False, timeout=30)
        
        if pdf_resp.status_code == 200:
            filename = f"{nfe_key}.pdf"
            return send_file(
                BytesIO(pdf_resp.content),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        else:
             flash(f"Erro ao baixar arquivo PDF: Status {pdf_resp.status_code}", "danger")
             return redirect(request.referrer or url_for('notas_fiscais'))

    except Exception as e:
        print(f"Exception in download_nfe: {e}")
        flash("Erro interno ao tentar baixar a nota.", "danger")
        return redirect(request.referrer or url_for('notas_fiscais')) 


@app.route('/insights')
@login_required
def insights():
    active_id = session.get('active_representative_id')
    if not active_id:
         flash("Selecione um representante.", "warning")
         return redirect(url_for('menu'))

    data = fetch_commercial_data(active_id)
    
    # Process data for chart: Total Sales by Month/Year
    # Data structure expected: 'F2_EMISSAO': 'YYYYMMDD', 'F2_VALBRUT': float
    
    chart_labels = []
    chart_values = []
    
    if data:
        from collections import defaultdict
        
        # Aggregate by Year-Month
        monthly_sales = defaultdict(float)
        
        for row in data:
            emissao = str(row.get('F2_EMISSAO', ''))
            val = float(row.get('F2_VALBRUT', 0))
            
            if len(emissao) >= 6:
                ym = emissao[:6] # YYYYMM
                monthly_sales[ym] += val
        
        # Sort by date
        sorted_keys = sorted(monthly_sales.keys())
        
        # Format labels and values
        for key in sorted_keys:
            # Format YYYYMM to MM/YYYY
            label = f"{key[4:6]}/{key[:4]}"
            chart_labels.append(label)
            chart_values.append(monthly_sales[key])
            
    else:
        # Mock data if no DB result
        chart_labels = ['01/2025', '02/2025', '03/2025', '04/2025', '05/2025', '06/2025']
        chart_values = [15000.0, 22000.0, 18500.0, 31000.0, 28000.0, 35000.0]

    return render_template('insights.html', labels=chart_labels, values=chart_values)


@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/api/chat/send', methods=['POST'])
@login_required
def chat_send():
    import requests
    data = request.json
    message = data.get('message')
    
    if not message:
         return jsonify({'error': 'No message provided'}), 400
         
    # Generate or retrieve session ID (simplification: user ID)
    session_id = str(current_user.id)
    
    # N8N Webhook URL (Ideally from Config)
    # Using the IP user provided recently, but with the path from the JSON file
    # Webhook ID: 3d061473-a4b8-4ee9-9796-848e05a5596e
    # Path: chat
    n8n_url = "http://localhost:5678/webhook/3d061473-a4b8-4ee9-9796-848e05a5596e/chat"
    # Or if user is running n8n in docker/LAN:
    # n8n_url = "http://192.168.117.53:5678/webhook/3d061473-a4b8-4ee9-9796-848e05a5596e/chat" 
    # I will use a fallback or try the localhost first. Since the user context showed failure on localhost:5000 accessing 192..., 
    # it implies the server runs locally.
    # Let's use a Config variable in a real app, but for now hardcode with comment.
    
    n8n_url = Config.N8N_WEBHOOK_URL if hasattr(Config, 'N8N_WEBHOOK_URL') else "http://localhost:5678/webhook/3d061473-a4b8-4ee9-9796-848e05a5596e/chat"
    
    try:
        # Get active company to find the client name
        active_id = session.get('active_representative_id')
        
        client_name = "Gestor"
        if active_id:
             # For the chat, we can say "Gestor visualizando Rep X" or just "Gestor"
             pass

        # Payload for n8n Webhook
        payload = {
            "chatInput": message,
            "sessionId": session_id,
            "A1_NOME": client_name
        }
        
        print(f"DEBUG: Sending POST to {n8n_url}")
        print(f"DEBUG: Payload: {payload}")
        
        response = requests.post(n8n_url, json=payload, timeout=30)
        
        print(f"DEBUG: Status Code: {response.status_code}")
        print(f"DEBUG: Response Text: {response.text}")
        
        if response.status_code == 200:
            # We expect n8n to return JSON. Our script ensured 'Set' node output has 'text'
            # If n8n returns a list of items, we take the first.
            try:
                res_data = response.json()
                if isinstance(res_data, list) and len(res_data) > 0:
                     return jsonify(res_data[0]) # Start with first item
                elif isinstance(res_data, dict):
                     return jsonify(res_data)
                else:
                     return jsonify({'text': str(response.text)})
            except ValueError:
                 return jsonify({'text': response.text}) # Plain text response?
        else:
            print(f"ERROR: n8n returned {response.status_code}")
            return jsonify({'error': f"N8N Error: {response.status_code}", 'details': response.text}), 502
            
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
