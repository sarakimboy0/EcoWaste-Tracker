from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
from flask_cors import CORS
import sqlite3
import os
import hashlib
import datetime
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
CORS(app)
DATABASE = 'ecowaste.db'

# ========================
# TEMPLATE DEFINITIONS
# ========================

KATEGORI_SAMPAH = [
    "Organik", "Plastik", "Kertas", "Logam", "Kaca", "Elektronik", "B3", "Lainnya"
]

KATEGORI_COLORS = {
    "Organik": "#228B22",         # Emerald green
    "Plastik": "#2ec4b6",
    "Kertas": "#f4d35e",
    "Logam": "#a1c181",
    "Kaca": "#43aa8b",
    "Elektronik": "#457b9d",
    "B3": "#e63946",
    "Lainnya": "#6d6875"
}

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>EcoWaste Tracker - Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background: linear-gradient(120deg,#f4f7f6 60%,#e3fcec 100%); }
        .sidebar {
            width: 220px; background: #263238; min-height: 100vh; color: #fff; position: fixed;
            box-shadow: 2px 0 10px rgba(44,62,80,0.04);
        }
        .sidebar .nav-link { color: #fff; border-radius: 8px; margin-bottom: 4px;}
        .sidebar .nav-link.active, .sidebar .nav-link:hover { background: #228B22; color: #fff;}
        .main { margin-left: 240px; padding: 32px 32px 32px 32px;}
        .circle-chart { width: 90px; height: 90px; margin: 0 auto; }
        .big-pie { width: 180px !important; height: 180px !important;}
        .stat-label { text-align: center; margin-top: 8px; font-weight: 500;}
        .card { border-radius: 18px; box-shadow: 0 2px 14px rgba(44,62,80,0.05);}
        .table td, .table th { vertical-align: middle; }
        .delete-btn { color: #e63946; cursor: pointer; }
        .dashboard-header { display: flex; align-items: center; gap: 12px;}
        .dashboard-header i { font-size: 1.5rem;}
        .summary-charts { display: flex; gap: 32px; align-items: center; justify-content: center;}
        .mini-charts { display: flex; gap: 18px; flex-wrap: wrap; justify-content: center;}
        .filter-form input, .filter-form select { border-radius: 8px;}
        @media (max-width:900px) {
            .main { margin-left: 0; padding: 16px;}
            .sidebar { position: relative; width: 100%; min-height: unset;}
            .summary-charts { flex-direction: column;}
        }
    </style>
</head>
<body>
    <div class="sidebar d-flex flex-column p-3">
        <div class="mb-4 text-center">
            <i class="fa fa-user-circle fa-3x"></i>
            <div style="font-weight:600;">{{ user['name'] }}</div>
        </div>
        <ul class="nav nav-pills flex-column mb-auto">
            <li><a href="/dashboard" class="nav-link active"><i class="fa fa-chart-pie"></i> Dashboard</a></li>
            <li><a href="/input-sampah" class="nav-link"><i class="fa fa-plus-circle"></i> Input Sampah</a></li>
            <li><a href="/chatbot" class="nav-link"><i class="fa fa-robot"></i> Chatbot</a></li>
            <li><a href="/analytics" class="nav-link"><i class="fa fa-chart-bar"></i> Analisis</a></li>
            <li><a href="/logout" class="nav-link"><i class="fa fa-sign-out"></i> Logout</a></li>
        </ul>
    </div>
    <div class="main">
        <div class="dashboard-header mb-4">
            <h2 style="margin-bottom:0;">Dashboard</h2>
            <span style="color:#228B22;"><i class="fa fa-recycle"></i></span>
        </div>
        <p>Selamat datang, <b>{{ user['name'] }}</b>! Berikut ringkasan data sampah Anda:</p>
        <div class="summary-charts mb-4">
            <div>
                <canvas id="bigPie" class="big-pie"></canvas>
                <div class="stat-label mt-3" style="font-size:1.2rem;">Total Sampah</div>
                <div class="text-center" style="font-size:1.5rem;font-weight:600;">{{ total_sampah }} kg</div>
            </div>
            <div class="mini-charts">
                {% for jenis, total in summary.items() %}
                <div>
                    <canvas id="chart{{ loop.index0 }}" class="circle-chart"></canvas>
                    <div class="stat-label" style="color:{{ kategori_colors[jenis] }};">{{jenis}}</div>
                    <div class="text-center"><b>{{total}}</b> kg</div>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="card p-3 mb-4">
            <h5>Riwayat Sampah</h5>
            <form method="get" class="mb-2 filter-form d-flex gap-2 flex-wrap">
                <input type="text" name="search" placeholder="Cari lokasi/deskripsi..." value="{{search or ''}}" class="form-control" style="max-width:200px;">
                <select name="filter_jenis" class="form-select" style="max-width:180px;">
                    <option value="">Semua Kategori</option>
                    {% for kategori in kategori_sampah %}
                    <option value="{{kategori}}" {% if filter_jenis==kategori %}selected{% endif %}>{{kategori}}</option>
                    {% endfor %}
                </select>
                <button class="btn btn-sm btn-success">Filter</button>
            </form>
            <div class="table-responsive">
            <table class="table table-striped align-middle">
                <thead style="background:#f4f7f6;">
                    <tr>
                        <th>Tanggal</th><th>Jenis</th><th>Berat (kg)</th><th>Lokasi</th><th>Deskripsi</th><th>Aksi</th>
                    </tr>
                </thead>
                <tbody>
                {% for waste in waste_history %}
                    <tr>
                        <td>{{waste['tanggal']}}</td>
                        <td><span class="badge" style="background:{{ kategori_colors[waste['jenis']] }};color:#fff;">{{waste['jenis']}}</span></td>
                        <td>{{waste['berat']}}</td>
                        <td>{{waste['lokasi']}}</td>
                        <td>{{waste['deskripsi']}}</td>
                        <td>
                            <form method="post" action="/dashboard" style="display:inline;">
                                <input type="hidden" name="waste_id" value="{{waste['id']}}">
                                <button class="btn btn-sm btn-outline-danger" onclick="return confirm('Hapus data ini?')"><i class="fa fa-trash"></i></button>
                            </form>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
            </div>
        </div>
    </div>
    <script>
        // Pie chart besar
        const bigPieCtx = document.getElementById('bigPie').getContext('2d');
        new Chart(bigPieCtx, {
            type: 'doughnut',
            data: {
                labels: {{ summary.keys()|list|safe }},
                datasets: [{
                    data: {{ summary.values()|list|safe }},
                    backgroundColor: {{ kategori_colors.values()|list|safe }},
                    borderWidth: 2
                }]
            },
            options: {
                cutout: '70%',
                plugins: { legend: { display: false } }
            }
        });
        // Pie chart kecil per kategori
        const summary = {{ summary_json|safe }};
        const kategoriColors = {{ kategori_colors|tojson }};
        let idx = 0;
        Object.keys(summary).forEach(function(jenis, i) {
            new Chart(document.getElementById('chart'+i), {
                type: 'doughnut',
                data: {
                    labels: [jenis, 'Lainnya'],
                    datasets: [{
                        data: [summary[jenis], Math.max(1, {{ total_sampah }}-summary[jenis])],
                        backgroundColor: [kategoriColors[jenis], '#e0e0e0']
                    }]
                },
                options: {
                    cutout: '75%',
                    plugins: { legend: { display: false } }
                }
            });
        });
    </script>
</body>
</html>
'''

INPUT_SAMPAH_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Input Sampah</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: linear-gradient(120deg,#f4f7f6 60%,#e3fcec 100%); }
        .input-card { max-width: 430px; margin: 50px auto; border-radius: 18px; box-shadow: 0 2px 16px rgba(44,62,80,0.07);}
        .input-card label { font-weight: 500;}
    </style>
</head>
<body>
    <div class="input-card bg-white p-4">
        <h2 class="mb-3" style="color:#228B22;"><i class="fa fa-plus-circle"></i> Input Data Sampah</h2>
        {% if message %}
        <div class="alert alert-success">{{ message }}</div>
        {% endif %}
        <form action="/input-sampah" method="post" class="mb-3">
            <div class="mb-2">
                <label>Jenis Sampah</label>
                <select name="jenis" required class="form-select">
                    {% for kategori in kategori_sampah %}
                    <option value="{{kategori}}">{{kategori}}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="mb-2">
                <label>Berat (kg)</label>
                <input type="number" step="0.01" name="berat" required class="form-control">
            </div>
            <div class="mb-2">
                <label>Lokasi</label>
                <input type="text" name="lokasi" class="form-control">
            </div>
            <div class="mb-2">
                <label>Deskripsi</label>
                <textarea name="deskripsi" class="form-control"></textarea>
            </div>
            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-success flex-fill">Simpan</button>
                <a href="/dashboard" class="btn btn-outline-secondary flex-fill">Kembali</a>
            </div>
        </form>
    </div>
</body>
</html>
'''

CHATBOT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>EcoBot</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: linear-gradient(120deg,#f4f7f6 60%,#e3fcec 100%); }
        #chat-container {
            border-radius: 18px; border: 1px solid #e0e0e0;
            height: 400px; overflow-y: auto; padding: 18px;
            background: #fff; box-shadow: 0 2px 14px rgba(44,62,80,0.04);
            max-width: 550px; margin: 0 auto 18px auto;
        }
        .bubble { max-width: 80%; padding: 10px 18px; border-radius: 18px; margin-bottom: 8px; font-size:1rem;}
        .bubble.user { background: #228B22; color: #fff; margin-left: auto; border-bottom-right-radius: 6px;}
        .bubble.bot { background: #e3fcec; color: #263238; margin-right: auto; border-bottom-left-radius: 6px;}
        .chatbox-form { max-width: 550px; margin: 0 auto;}
    </style>
</head>
<body>
    <div class="container mt-5">
        <h2 class="mb-3 text-center" style="color:#228B22;"><i class="fa fa-robot"></i> EcoBot - Asisten Daur Ulang</h2>
        <div id="chat-container">
            {% for chat in chat_history %}
                <div class="bubble user">Anda: {{ chat['user'] }}</div>
                <div class="bubble bot">EcoBot: {{ chat['bot'] }}</div>
            {% endfor %}
        </div>
        <form action="/chatbot" method="post" class="chatbox-form d-flex gap-2 mt-3">
            <input type="text" name="message" placeholder="Ketik pesan Anda..." class="form-control" required autocomplete="off">
            <button type="submit" class="btn btn-success">Kirim</button>
        </form>
        <div class="text-center mt-3">
            <a href="/dashboard" class="btn btn-outline-secondary">Kembali ke Dashboard</a>
        </div>
    </div>
    <script>
        var chatDiv = document.getElementById('chat-container');
        chatDiv.scrollTop = chatDiv.scrollHeight;
    </script>
</body>
</html>
'''

ANALYTICS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Analisis Sampah</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background: linear-gradient(120deg,#f4f7f6 60%,#e3fcec 100%);}
        .analytics-card { border-radius: 18px; box-shadow: 0 2px 16px rgba(44,62,80,0.07); background:#fff;}
    </style>
</head>
<body>
    <div class="container mt-5">
        <div class="analytics-card p-4">
        <h2 style="color:#228B22;"><i class="fa fa-chart-bar"></i> Analisis Data Sampah</h2>
        <div class="row mt-4">
            <div class="col-md-6 mb-3">
                <canvas id="pieChart"></canvas>
            </div>
            <div class="col-md-6 mb-3">
                <canvas id="barChart"></canvas>
            </div>
        </div>
        <a href="/dashboard" class="btn btn-outline-secondary mt-3">Kembali ke Dashboard</a>
        </div>
    </div>
    <script>
        const labels = {{ labels|safe }};
        const values = {{ values|safe }};
        const colors = {{ colors|safe }};
        new Chart(document.getElementById('pieChart'), {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors
                }]
            },
            options: { plugins: { legend: { position: 'bottom' } }, cutout:'65%' }
        });
        new Chart(document.getElementById('barChart'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Sampah (kg)',
                    data: values,
                    backgroundColor: colors
                }]
            },
            options: { scales: { y: { beginAtZero: true } }, plugins:{ legend:{display:false}} }
        });
    </script>
</body>
</html>
'''

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>EcoWaste Tracker</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(120deg,#f4f7f6 60%,#e3fcec 100%);}
        .centered {
            max-width: 420px; margin: 100px auto; text-align: center;
            background: #fff; border-radius: 18px; box-shadow: 0 2px 16px rgba(44,62,80,0.07);
            padding: 40px 30px;
        }
        .brand { color:#228B22; font-weight: 700;}
    </style>
</head>
<body>
    <div class="centered">
        <h1>Selamat Datang di <span class="brand">EcoWaste Tracker!</span></h1>
        <p>Aplikasi manajemen dan analisis sampah modern.</p>
        <div class="d-flex gap-2 justify-content-center mt-4">
            <a href="/login" class="btn btn-success px-4">Login</a>
            <a href="/register" class="btn btn-outline-success px-4">Register</a>
        </div>
    </div>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: linear-gradient(120deg,#f4f7f6 60%,#e3fcec 100%);}
        .login-card { max-width: 400px; margin: 60px auto; border-radius: 18px; box-shadow: 0 2px 16px rgba(44,62,80,0.07);}
    </style>
</head>
<body>
    <div class="login-card bg-white p-4">
        <h2 class="mb-3" style="color:#228B22;"><i class="fa fa-sign-in-alt"></i> Login</h2>
        {% if error %}
        <div class="alert alert-danger">{{ error }}</div>
        {% endif %}
        <form action="/login" method="post" autocomplete="off">
            <div class="mb-2">
                <label>Email</label>
                <input type="email" name="email" required class="form-control">
            </div>
            <div class="mb-2">
                <label>Password</label>
                <input type="password" name="password" required class="form-control">
            </div>
            <button type="submit" class="btn btn-success w-100">Login</button>
        </form>
        <p class="mt-3 text-center">Belum punya akun? <a href="/register">Daftar di sini</a></p>
    </div>
</body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Register</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: linear-gradient(120deg,#f4f7f6 60%,#e3fcec 100%);}
        .register-card { max-width: 400px; margin: 60px auto; border-radius: 18px; box-shadow: 0 2px 16px rgba(44,62,80,0.07);}
    </style>
</head>
<body>
    <div class="register-card bg-white p-4">
        <h2 class="mb-3" style="color:#228B22;"><i class="fa fa-user-plus"></i> Registrasi Pengguna Baru</h2>
        {% if error %}
        <div class="alert alert-danger">{{ error }}</div>
        {% endif %}
        <form action="/register" method="post" autocomplete="off">
            <div class="mb-2">
                <label>Nama</label>
                <input type="text" name="name" required class="form-control">
            </div>
            <div class="mb-2">
                <label>Email</label>
                <input type="email" name="email" required class="form-control">
            </div>
            <div class="mb-2">
                <label>Password</label>
                <input type="password" name="password" required class="form-control">
            </div>
            <button type="submit" class="btn btn-success w-100">Daftar</button>
        </form>
        <p class="mt-3 text-center">Sudah punya akun? <a href="/login">Login di sini</a></p>
    </div>
</body>
</html>
'''

# ========================
# DATABASE HELPERS
# ========================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        c = conn.cursor()
        # Users table
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        # Waste data table
        c.execute('''
            CREATE TABLE waste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                jenis TEXT NOT NULL,
                berat REAL NOT NULL,
                lokasi TEXT,
                deskripsi TEXT,
                tanggal TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        # Chat history table
        c.execute('''
            CREATE TABLE chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
        conn.close()
        print("Database initialized.")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

# ========================
# ROUTES
# ========================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(INDEX_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, hash_password(password)))
            conn.commit()
            return redirect(url_for('login_page'))
        except sqlite3.IntegrityError:
            return render_template_string(REGISTER_TEMPLATE, error="Email sudah terdaftar.")
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user and verify_password(password, user['password']):
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Email atau password salah.")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    # Hapus data sampah jika ada request POST dari tombol hapus
    if request.method == 'POST':
        waste_id = request.form.get('waste_id')
        if waste_id:
            conn.execute('DELETE FROM waste WHERE id = ? AND user_id = ?', (waste_id, user_id))
            conn.commit()

    # Filter dan search
    search = request.args.get('search', '')
    filter_jenis = request.args.get('filter_jenis', '')
    query = 'SELECT * FROM waste WHERE user_id = ?'
    params = [user_id]
    if filter_jenis:
        query += ' AND jenis = ?'
        params.append(filter_jenis)
    if search:
        query += ' AND (lokasi LIKE ? OR deskripsi LIKE ?)'
        params += [f'%{search}%', f'%{search}%']
    query += ' ORDER BY tanggal DESC, id DESC'
    waste_history = conn.execute(query, params).fetchall()

    # Summary
    summary = {k: 0 for k in KATEGORI_SAMPAH}
    total_sampah = 0
    for row in conn.execute('SELECT jenis, SUM(berat) as total FROM waste WHERE user_id = ? GROUP BY jenis', (user_id,)):
        summary[row['jenis']] = float(row['total'])
        total_sampah += float(row['total'])
    kategori_colors = KATEGORI_COLORS

    return render_template_string(
        DASHBOARD_TEMPLATE,
        user=user,
        summary=summary,
        summary_json=json.dumps(summary),
        kategori_colors=kategori_colors,
        kategori_sampah=KATEGORI_SAMPAH,
        waste_history=waste_history,
        search=search,
        filter_jenis=filter_jenis,
        total_sampah=round(total_sampah,2)
    )

@app.route('/input-sampah', methods=['GET', 'POST'])
def input_sampah():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    message = None
    if request.method == 'POST':
        jenis = request.form.get('jenis')
        berat = float(request.form.get('berat'))
        lokasi = request.form.get('lokasi','')
        deskripsi = request.form.get('deskripsi','')
        tanggal = datetime.datetime.now().strftime('%Y-%m-%d')
        conn = get_db_connection()
        conn.execute('INSERT INTO waste (user_id, jenis, berat, lokasi, deskripsi, tanggal) VALUES (?,?,?,?,?,?)',
                     (session['user_id'], jenis, berat, lokasi, deskripsi, tanggal))
        conn.commit()
        message = "Data sampah berhasil ditambahkan!"
    return render_template_string(INPUT_SAMPAH_TEMPLATE, kategori_sampah=KATEGORI_SAMPAH, message=message)

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    conn = get_db_connection()
    chat_history = conn.execute('SELECT user_message as user, bot_response as bot FROM chat_history WHERE user_id = ? ORDER BY id ASC', (session['user_id'],)).fetchall()
    chat_history = [dict(row) for row in chat_history]
    if request.method == 'POST':
        message = request.form.get('message')
        # Bot logic sederhana, bisa diganti AI sebenarnya
        if 'plastik' in message.lower():
            bot = "Pastikan plastik bersih sebelum didaur ulang. Pisahkan dari sampah organik ya!"
        elif 'organik' in message.lower():
            bot = "Sampah organik bisa dijadikan kompos. Sudah pernah coba membuat kompos?"
        elif 'kaca' in message.lower():
            bot = "Kaca bisa didaur ulang, tapi hati-hati saat membuangnya!"
        elif 'logam' in message.lower():
            bot = "Logam seperti kaleng bisa dijual ke pengepul atau didaur ulang."
        elif 'b3' in message.lower():
            bot = "Sampah B3 (Bahan Berbahaya dan Beracun) harus dibuang di tempat khusus."
        elif 'halo' in message.lower() or 'hai' in message.lower():
            bot = "Halo! Ada yang bisa EcoBot bantu seputar daur ulang sampah?"
        else:
            bot = "Terima kasih atas pertanyaannya! Untuk info lebih lanjut, silakan tanyakan jenis sampah atau tips daur ulang."
        conn.execute('INSERT INTO chat_history (user_id, user_message, bot_response, timestamp) VALUES (?,?,?,?)',
                     (session['user_id'], message, bot, datetime.datetime.now().isoformat()))
        conn.commit()
        return redirect(url_for('chatbot'))
    return render_template_string(CHATBOT_TEMPLATE, chat_history=chat_history)

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    conn = get_db_connection()
    rows = conn.execute('SELECT jenis, SUM(berat) as total FROM waste WHERE user_id = ? GROUP BY jenis', (session['user_id'],)).fetchall()
    labels = [row['jenis'] for row in rows]
    values = [float(row['total']) for row in rows]
    colors = [KATEGORI_COLORS.get(jenis, "#cccccc") for jenis in labels]
    return render_template_string(ANALYTICS_TEMPLATE, labels=labels, values=values, colors=colors)

# ========================
# INIT
# ========================

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
