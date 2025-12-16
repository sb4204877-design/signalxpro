from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import os
import json

# === Flask App Setup ===
app = Flask(__name__)
app.config['SECRET_KEY'] = 'signalxpro-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///signalxpro.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
db = SQLAlchemy(app)

# === Database Models ===
class Signal(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pair = db.Column(db.String(50), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'
    duration = db.Column(db.Integer, nullable=False)       # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')
    result = db.Column(db.String(10))  # 'win' or 'loss'
    resolved_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'pair': self.pair,
            'direction': self.direction,
            'duration': self.duration,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'result': self.result,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

class Strategy(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        try:
            imgs = json.loads(self.images) if self.images else []
        except:
            imgs = []
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'images': imgs,
            'created_at': self.created_at.isoformat()
        }

# Create tables
with app.app_context():
    db.create_all()
    print("✅ قاعدة البيانات جاهزة: signalxpro.db")

# === API Endpoints ===

@app.route('/api/signals', methods=['GET', 'POST'])
def handle_signals():
    if request.method == 'GET':
        signals = Signal.query.order_by(Signal.created_at.desc()).all()
        return jsonify([s.to_dict() for s in signals])
    elif request.method == 'POST':
        data = request.get_json()
        signal = Signal(
            pair=data['pair'],
            direction=data['direction'],
            duration=int(data['duration'])
        )
        db.session.add(signal)
        db.session.commit()
        socketio.emit('new_signal', signal.to_dict())
        return jsonify({'success': True, 'signal': signal.to_dict()})

@app.route('/api/signals/<signal_id>/resolve', methods=['POST'])
def resolve_signal(signal_id):
    signal = Signal.query.get(signal_id)
    if not signal:
        return jsonify({'error': 'Signal not found'}), 404
    data = request.get_json()
    signal.status = 'completed'
    signal.result = data['result']
    signal.resolved_at = datetime.utcnow()
    db.session.commit()
    socketio.emit('signal_resolved', signal.to_dict())
    return jsonify({'success': True})

@app.route('/api/signals/active', methods=['GET'])
def active_signals():
    signals = Signal.query.filter_by(status='active').all()
    return jsonify([s.to_dict() for s in signals])

@app.route('/api/strategies', methods=['GET', 'POST', 'DELETE'])
def handle_strategies():
    if request.method == 'GET':
        strategies = Strategy.query.order_by(Strategy.created_at.desc()).all()
        return jsonify([s.to_dict() for s in strategies])
    elif request.method == 'POST':
        data = request.get_json()
        strategy = Strategy(
            title=data['title'],
            content=data['content'],
            images=json.dumps(data.get('images', []))
        )
        db.session.add(strategy)
        db.session.commit()
        return jsonify({'success': True, 'strategy': strategy.to_dict()})
    elif request.method == 'DELETE':
        Strategy.query.delete()
        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/strategies/<strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    strategy = Strategy.query.get(strategy_id)
    if strategy:
        db.session.delete(strategy)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Strategy not found'}), 404

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_signals = Signal.query.count()
    active = Signal.query.filter_by(status='active').count()
    completed = Signal.query.filter_by(status='completed').count()
    wins = Signal.query.filter_by(result='win').count()
    losses = Signal.query.filter_by(result='loss').count()
    win_rate = round(wins / completed * 100, 1) if completed > 0 else 0
    return jsonify({
        'active_users': 8542,
        'open_trades': active,
        'win_rate': win_rate,
        'strategies_count': Strategy.query.count(),
        'total_signals': total_signals,
        'wins': wins,
        'losses': losses
    })

# === Serve Full Admin Panel as Static HTML ===
@app.route('/')
def serve_admin_panel():
    # قراءة محتوى الواجهة من هذا الملف نفسه (أو يمكنك وضعه في ملف منفصل)
    with open(__file__, 'r', encoding='utf-8') as f:
        content = f.read()
    # استخراج جزء HTML فقط (من <!DOCTYPE إلى </html>)
    start = content.find('<!DOCTYPE')
    end = content.rfind('</html>') + len('</html>')
    html_content = content[start:end]
    return html_content

# === WebSocket Events ===
@socketio.on('connect')
def on_connect():
    pass

@socketio.on('disconnect')
def on_disconnect():
    pass

# === Embed HTML directly in this file (for portability) ===
# لا تلمس هذا الجزء — هو جزء من الواجهة الأمامية الأصلية
"""
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SignalXPro Admin Panel</title>
    <!-- مكتبة الأيقونات -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* ==================== الخطوط والألوان ==================== */
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&family=Rajdhani:wght@500;700&display=swap');
        :root {
            /* الألوان الحديدية الصناعية (رمادي وأسود) */
            --bg-main: #121212;
            --iron-dark: #1a1a1a;
            --iron-mid: #262626;
            --iron-light: #333333;
            --iron-border: #444;
            --gold: #d4af37;
            --neon-green: #00e676;
            --neon-red: #ff1744;
            --text-main: #e0e0e0;
            --text-dim: #888;
            /* تأثيرات الظل 3D */
            --shadow-out: 5px 5px 10px #0a0a0a, -2px -2px 6px #383838;
            --shadow-in: inset 3px 3px 6px #0a0a0a, inset -2px -2px 5px #383838;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body {
            background-color: var(--bg-main);
            color: var(--text-main);
            font-family: 'Rajdhani', sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
        }
        /* تحويل الخط عند العربية */
        html[lang="ar"] body { font-family: 'Cairo', sans-serif; }
        /* ==================== التصميم الحديدي (Iron Style) ==================== */
        .iron-card {
            background: linear-gradient(145deg, var(--iron-mid), var(--iron-dark));
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: var(--shadow-out);
            border: 1px solid var(--iron-border);
            position: relative;
        }
        .screw {
            position: absolute; width: 8px; height: 8px;
            background: linear-gradient(45deg, #111, #555);
            border-radius: 50%; box-shadow: 0 1px 2px black; z-index: 2;
        }
        .screw::after { content: ''; position: absolute; top: 3px; left: 1px; width: 6px; height: 2px; background: #000; transform: rotate(45deg); }
        .tl { top: 8px; left: 8px; } .tr { top: 8px; right: 8px; }
        .bl { bottom: 8px; left: 8px; } .br { bottom: 8px; right: 8px; }
        .btn-iron {
            background: linear-gradient(145deg, #333, #1f1f1f);
            color: #fff; border: none; padding: 12px;
            border-radius: 8px; box-shadow: var(--shadow-out);
            font-weight: bold; cursor: pointer; transition: 0.2s;
            display: flex; align-items: center; justify-content: center; gap: 8px;
            width: 100%; border: 1px solid #444;
        }
        .btn-iron:active { box-shadow: var(--shadow-in); transform: scale(0.98); }
        /* Login Form */
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .login-form {
            width: 100%;
            max-width: 400px;
            padding: 30px;
        }
        .login-form input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #444;
            border-radius: 8px;
            background: var(--iron-mid);
            color: white;
            font-family: inherit;
            font-size: 1rem;
        }
        /* Main Dashboard */
        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border-bottom: 1px solid var(--iron-border);
        }
        .dashboard-sidebar {
            width: 250px;
            background: var(--iron-dark);
            height: 100vh;
            position: fixed;
            left: 0;
            top: 0;
            padding-top: 80px;
            border-right: 1px solid var(--iron-border);
        }
        .dashboard-sidebar a {
            display: block;
            padding: 15px 20px;
            color: var(--text-main);
            text-decoration: none;
            border-bottom: 1px solid var(--iron-border);
            transition: 0.2s;
            font-family: inherit;
        }
        .dashboard-sidebar a:hover, .dashboard-sidebar a.active {
            background: var(--iron-mid);
            color: var(--gold);
        }
        .dashboard-main {
            margin-left: 250px;
            padding: 20px;
        }
        .dashboard-section {
            display: none;
        }
        .dashboard-section.active {
            display: block;
        }
        /* Statistics Dashboard */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(145deg, var(--iron-mid), var(--iron-dark));
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            border: 1px solid var(--iron-border);
            position: relative;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 10px 0;
            color: var(--gold);
        }
        .stat-label {
            font-size: 1rem;
            color: var(--text-dim);
        }
        /* Custom Gauge - Corrected colors and needle position */
        .gauge-container {
            background: linear-gradient(145deg, var(--iron-mid), var(--iron-dark));
            border-radius: 18px;
            padding: 25px;
            text-align: center;
            border: 3px solid #222;
            margin: 30px 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.8);
            position: relative;
        }
        .gauge-title {
            font-size: 1.3rem;
            margin-bottom: 20px;
            color: var(--gold);
        }
        .gauge-svg {
            width: 100%;
            max-width: 480px;
            height: auto;
            margin: 0 auto;
        }
        .gauge-info {
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            padding: 15px;
            background: rgba(30,30,30,0.7);
            border-radius: 10px;
            border: 1px solid var(--iron-border);
        }
        .info-item {
            text-align: center;
        }
        .info-value {
            font-size: 1.2rem;
            font-weight: bold;
            color: var(--gold);
        }
        .info-label {
            font-size: 0.85rem;
            color: var(--text-dim);
        }
        /* Signal Form */
        .signal-form .form-group {
            margin-bottom: 20px;
        }
        .signal-form label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            font-size: 1rem;
            color: var(--text-main);
        }
        .signal-form input, .signal-form select {
            width: 100%;
            padding: 12px;
            border: 1px solid #444;
            border-radius: 8px;
            background: var(--iron-mid);
            color: white;
            font-family: inherit;
            font-size: 1rem;
            border: 1px solid var(--iron-border);
        }
        .signal-actions {
            display: flex;
            gap: 15px;
            margin-top: 25px;
        }
        .btn-buy {
            background: linear-gradient(135deg, #1b5e20, #2e7d32);
            border: 1px solid #4caf50;
        }
        .btn-sell {
            background: linear-gradient(135deg, #b71c1c, #c62828);
            border: 1px solid #f44336;
        }
        /* Open Trades */
        .open-trade {
            background: rgba(30,30,30,0.8);
            padding: 18px;
            margin-bottom: 15px;
            border-radius: 10px;
            border-left: 4px solid var(--gold);
            position: relative;
        }
        .trade-header {
            display: flex;
            justify-content: space-between;
            font-weight: bold;
            margin-bottom: 12px;
            font-size: 1.1rem;
        }
        .trade-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            color: var(--text-dim);
            font-size: 0.9rem;
        }
        .trade-actions {
            display: flex;
            gap: 12px;
        }
        .btn-win {
            background: linear-gradient(135deg, #1b5e20, #2e7d32);
            padding: 10px 15px;
            font-size: 0.9rem;
        }
        .btn-loss {
            background: linear-gradient(135deg, #b71c1c, #c62828);
            padding: 10px 15px;
            font-size: 0.9rem;
        }
        /* Strategy Form */
        .strategy-form .form-group {
            margin-bottom: 20px;
        }
        .strategy-form label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            font-size: 1rem;
            color: var(--text-main);
        }
        .strategy-form input {
            width: 100%;
            padding: 12px;
            border: 1px solid #444;
            border-radius: 8px;
            background: var(--iron-mid);
            color: white;
            font-family: inherit;
            font-size: 1rem;
            border: 1px solid var(--iron-border);
        }
        .strategy-form textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--iron-border);
            border-radius: 8px;
            background: var(--iron-mid);
            color: white;
            min-height: 150px;
            font-family: inherit;
            font-size: 1rem;
            resize: vertical;
        }
        .image-links {
            margin-top: 15px;
        }
        .image-link-item {
            display: flex;
            gap: 12px;
            margin-bottom: 12px;
        }
        .image-link-item input {
            flex: 1;
            padding: 10px;
            border: 1px solid var(--iron-border);
            border-radius: 6px;
            background: var(--iron-mid);
            color: white;
            font-family: inherit;
            font-size: 0.9rem;
        }
        .btn-add-link, .btn-remove-link {
            padding: 10px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            border: none;
            font-family: inherit;
        }
        .btn-add-link {
            background: var(--gold);
            color: #000;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .btn-remove-link {
            background: var(--neon-red);
            color: white;
            width: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        /* Published Strategies */
        .strategy-item {
            background: rgba(30,30,30,0.8);
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 10px;
            border-left: 4px solid var(--gold);
        }
        .strategy-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 12px;
            align-items: center;
        }
        .strategy-title {
            font-size: 1.2rem;
            font-weight: bold;
            color: var(--gold);
        }
        .strategy-content {
            margin-bottom: 15px;
            line-height: 1.5;
            color: var(--text-main);
        }
        .strategy-images {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        .strategy-image {
            width: 100px;
            height: 100px;
            border-radius: 8px;
            border: 1px solid #444;
            object-fit: cover;
        }
        /* Trade History */
        .history-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin-bottom: 12px;
            background: rgba(30,30,30,0.7);
            border-radius: 8px;
            border-left: 4px solid #d4af37;
        }
        .history-item.win {
            border-left-color: var(--neon-green);
        }
        .history-item.loss {
            border-left-color: var(--neon-red);
        }
        .history-symbol {
            font-weight: bold;
            font-size: 1rem;
        }
        .history-arrow {
            font-size: 1.4rem;
            margin: 0 15px;
        }
        .arrow-up { color: var(--neon-green); }
        .arrow-down { color: var(--neon-red); }
        .history-result {
            font-weight: bold;
            font-size: 1rem;
        }
        .result-win { color: var(--neon-green); }
        .result-loss { color: var(--neon-red); }
        /* Language Switch */
        .lang-switch {
            background: linear-gradient(145deg, var(--iron-mid), var(--iron-dark));
            border: 1px solid var(--iron-border);
            color: var(--text-main);
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            transition: 0.3s;
            font-family: inherit;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .lang-switch:hover {
            background: linear-gradient(145deg, var(--iron-light), var(--iron-mid));
            transform: scale(1.05);
        }
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <!-- Login Page -->
    <div id="login-page" class="login-container">
        <div class="iron-card login-form">
            <div class="screw tl"></div><div class="screw tr"></div>
            <div class="screw bl"></div><div class="screw br"></div>
            <h2 id="login-title" style="text-align:center; margin-bottom:25px; color:var(--gold); font-size:1.8rem;">Admin Login</h2>
            <input type="text" id="username" placeholder="Username" />
            <input type="password" id="password" placeholder="Password" />
            <button class="btn-iron" id="login-btn" onclick="login()" style="margin-top:20px;">
                <i class="fa-solid fa-right-to-bracket"></i> <span id="login-text">Login</span>
            </button>
            <div style="text-align:center; margin-top:20px;">
                <button class="lang-switch" onclick="toggleLang()">
                    <i class="fa-solid fa-language"></i> <span id="lang-text">AR / EN</span>
                </button>
            </div>
        </div>
    </div>
    <!-- Main Dashboard -->
    <div id="main-dashboard" class="hidden">
        <div class="dashboard-header">
            <div class="logo-text" style="font-size:1.8rem; font-weight:900; color:#fff; letter-spacing:1px;">SignalXPro Admin</div>
            <button class="btn-iron" style="width:auto; padding:8px 20px;" onclick="logout()">
                <i class="fa-solid fa-right-from-bracket"></i> <span id="logout-text">Logout</span>
            </button>
        </div>
        <div class="dashboard-sidebar">
            <a href="#" class="active" onclick="showSection('dashboard-section')">
                <i class="fa-solid fa-chart-line"></i> <span id="nav-dashboard">Dashboard</span>
            </a>
            <a href="#" onclick="showSection('signals-section')">
                <i class="fa-solid fa-broadcast-tower"></i> <span id="nav-signals">Signals</span>
            </a>
            <a href="#" onclick="showSection('strategies-section')">
                <i class="fa-solid fa-diagram-project"></i> <span id="nav-strategies">Strategies</span>
            </a>
            <a href="#" onclick="showSection('published-strategies-section')">
                <i class="fa-solid fa-book"></i> <span id="nav-published">Published Strategies</span>
            </a>
            <a href="#" onclick="showSection('history-section')">
                <i class="fa-solid fa-clock-rotate-left"></i> <span id="nav-history">Trade History</span>
            </a>
        </div>
        <div class="dashboard-main">
            <!-- Dashboard Section -->
            <div id="dashboard-section" class="dashboard-section active">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="screw tl"></div><div class="screw tr"></div>
                        <div class="screw bl"></div><div class="screw br"></div>
                        <div class="stat-label" id="lbl-users">Active Users</div>
                        <div class="stat-value" id="users-count">8,542</div>
                        <div style="font-size:0.8rem; color:var(--neon-green);">+124 today</div>
                    </div>
                    <div class="stat-card">
                        <div class="screw tl"></div><div class="screw tr"></div>
                        <div class="screw bl"></div><div class="screw br"></div>
                        <div class="stat-label" id="lbl-trades">Open Trades</div>
                        <div class="stat-value" id="trades-count">247</div>
                        <div style="font-size:0.8rem; color:var(--gold);">Live signals</div>
                    </div>
                    <div class="stat-card">
                        <div class="screw tl"></div><div class="screw tr"></div>
                        <div class="screw bl"></div><div class="screw br"></div>
                        <div class="stat-label" id="lbl-wins">Win Rate</div>
                        <div class="stat-value" id="wins-count">87.3%</div>
                        <div style="font-size:0.8rem; color:var(--neon-green);">High accuracy</div>
                    </div>
                    <div class="stat-card">
                        <div class="screw tl"></div><div class="screw tr"></div>
                        <div class="screw bl"></div><div class="screw br"></div>
                        <div class="stat-label" id="lbl-strategies">Strategies</div>
                        <div class="stat-value" id="strategies-count">18</div>
                        <div style="font-size:0.8rem; color:var(--gold);">Published</div>
                    </div>
                </div>
                <!-- Custom Pressure Gauge - Fixed colors and needle -->
                <div class="gauge-container">
                    <div class="screw tl"></div><div class="screw tr"></div>
                    <div class="screw bl"></div><div class="screw br"></div>
                    <h3 class="gauge-title" id="gauge-title">Real-time Server Load</h3>
                    <svg class="gauge-svg" viewBox="0 0 400 280" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <linearGradient id="arcGradient" x1="0%" y1="0%" x2="100%" x2="0%">
                                <stop offset="0%" stop-color="#00e676" /> <!-- Green - Low/Optimal (LEFT) -->
                                <stop offset="25%" stop-color="#ffeb3b" /> <!-- Yellow - Normal -->
                                <stop offset="50%" stop-color="#ff9800" /> <!-- Orange - High -->
                                <stop offset="100%" stop-color="#ff1744" /> <!-- Red - Critical (RIGHT) -->
                            </linearGradient>
                            <linearGradient id="needleGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.9"/>
                                <stop offset="100%" stop-color="#e0e0e0" stop-opacity="0.7"/>
                            </linearGradient>
                        </defs>
                        <!-- Main arc - now with correct color order -->
                        <path d="M 50 200 A 150 150 0 0 1 350 200" 
                              fill="none" stroke="url(#arcGradient)" stroke-width="16" stroke-linecap="round"/>
                        <!-- Center pivot point (base of needle) -->
                        <circle cx="200" cy="200" r="8" fill="#333" stroke="#fff" stroke-width="1"/>
                        <!-- Needle - now properly positioned with base at center circle -->
                        <polygon id="gauge-needle" points="200,200 197,120 200,110 203,120 200,200" 
                                 fill="url(#needleGradient)" stroke="#333" stroke-width="1"/>
                        <!-- Labels - positioned correctly -->
                        <text x="50" y="225" font-size="11" fill="#00e676" text-anchor="middle" font-weight="bold">OPTIMAL</text>
                        <text x="125" y="225" font-size="11" fill="#ffeb3b" text-anchor="middle" font-weight="bold">NORMAL</text>
                        <text x="200" y="225" font-size="11" fill="#ff9800" text-anchor="middle" font-weight="bold">HIGH</text>
                        <text x="275" y="225" font-size="11" fill="#ff1744" text-anchor="middle" font-weight="bold">CRITICAL</text>
                        <text x="350" y="225" font-size="11" fill="#ff1744" text-anchor="middle" font-weight="bold">MAX</text>
                        <!-- Scale markers -->
                        <text x="50" y="185" font-size="10" fill="#888" text-anchor="middle">0</text>
                        <text x="125" y="185" font-size="10" fill="#888" text-anchor="middle">25K</text>
                        <text x="200" y="185" font-size="10" fill="#888" text-anchor="middle">50K</text>
                        <text x="275" y="185" font-size="10" fill="#888" text-anchor="middle">75K</text>
                        <text x="350" y="185" font-size="10" fill="#888" text-anchor="middle">100K</text>
                    </svg>
                    <!-- Information panel next to gauge -->
                    <div class="gauge-info">
                        <div class="info-item">
                            <div class="info-value" id="current-users">42,850</div>
                            <div class="info-label" id="users-label">Active Users</div>
                        </div>
                        <div class="info-item">
                            <div class="info-value" id="server-status">Normal</div>
                            <div class="info-label" id="status-label">Server Status</div>
                        </div>
                        <div class="info-item">
                            <div class="info-value" id="capacity">42.85%</div>
                            <div class="info-label" id="capacity-label">Capacity Used</div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Signals Section -->
            <div id="signals-section" class="dashboard-section">
                <div class="iron-card">
                    <div class="screw tl"></div><div class="screw tr"></div>
                    <div class="screw bl"></div><div class="screw br"></div>
                    <h3 id="signals-title" style="margin-bottom:25px; color:var(--gold); font-size:1.5rem;">Create New Signal</h3>
                    <form class="signal-form">
                        <div class="form-group">
                            <label for="pair-name" id="lbl-pair">Pair Name</label>
                            <input type="text" id="pair-name" placeholder="e.g., EUR/USD OTC" required />
                        </div>
                        <div class="form-group">
                            <label for="duration" id="lbl-duration">Duration (minutes)</label>
                            <select id="duration" required style="padding:12px;">
                                <option value="1">1 minute</option>
                                <option value="2">2 minutes</option>
                                <option value="3">3 minutes</option>
                                <option value="5">5 minutes</option>
                                <option value="10">10 minutes</option>
                            </select>
                        </div>
                        <div class="signal-actions">
                            <button type="button" class="btn-iron btn-buy" onclick="createSignal('buy')">
                                <i class="fa-solid fa-arrow-up"></i> <span id="btn-buy">Buy</span>
                            </button>
                            <button type="button" class="btn-iron btn-sell" onclick="createSignal('sell')">
                                <i class="fa-solid fa-arrow-down"></i> <span id="btn-sell">Sell</span>
                            </button>
                        </div>
                    </form>
                </div>
                <div class="iron-card">
                    <div class="screw tl"></div><div class="screw tr"></div>
                    <div class="screw bl"></div><div class="screw br"></div>
                    <h3 id="open-trades-title" style="margin-bottom:25px; color:var(--gold); font-size:1.5rem;">Open Trades</h3>
                    <div id="open-trades-container">
                        <div id="no-open-trades" style="text-align:center; color:#888; padding:30px;" id="no-trades-text">No open trades</div>
                    </div>
                </div>
            </div>
            <!-- Strategies Section -->
            <div id="strategies-section" class="dashboard-section">
                <div class="iron-card">
                    <div class="screw tl"></div><div class="screw tr"></div>
                    <div class="screw bl"></div><div class="screw br"></div>
                    <h3 id="strategy-form-title" style="margin-bottom:25px; color:var(--gold); font-size:1.5rem;">Create New Strategy</h3>
                    <form class="strategy-form">
                        <div class="form-group">
                            <label for="strategy-title-input" id="lbl-strategy-title">Strategy Title</label>
                            <input type="text" id="strategy-title-input" placeholder="Enter strategy title" required />
                        </div>
                        <div class="form-group">
                            <label for="strategy-content" id="lbl-strategy-content">Strategy Content</label>
                            <textarea id="strategy-content" placeholder="Write your strategy content here..." required></textarea>
                        </div>
                        <div class="form-group">
                            <label id="lbl-images">Strategy Images</label>
                            <div class="image-links" id="image-links-container">
                                <div class="image-link-item">
                                    <input type="url" placeholder="Image URL" />
                                    <button type="button" class="btn-remove-link" onclick="removeImageLink(this)">×</button>
                                </div>
                            </div>
                            <button type="button" class="btn-add-link" onclick="addImageLink()">
                                <i class="fa-solid fa-plus"></i> <span id="add-image-text">Add Image</span>
                            </button>
                        </div>
                        <div class="signal-actions" style="margin-top:25px;">
                            <button type="button" class="btn-iron" onclick="publishStrategy()">
                                <i class="fa-solid fa-paper-plane"></i> <span id="publish-btn">Publish</span>
                            </button>
                            <button type="button" class="btn-iron" style="background:var(--neon-red);" onclick="cancelStrategy()">
                                <i class="fa-solid fa-xmark"></i> <span id="cancel-btn">Cancel</span>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            <!-- Published Strategies Section -->
            <div id="published-strategies-section" class="dashboard-section">
                <div class="iron-card">
                    <div class="screw tl"></div><div class="screw tr"></div>
                    <div class="screw bl"></div><div class="screw br"></div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px;">
                        <h3 id="published-title" style="color:var(--gold); font-size:1.5rem;">Published Strategies</h3>
                        <button class="btn-iron" style="background:var(--neon-red); width:auto; padding:10px 20px;" onclick="deleteAllStrategies()">
                            <i class="fa-solid fa-trash"></i> <span id="delete-all-text">Delete All</span>
                        </button>
                    </div>
                    <div id="published-strategies-container">
                        <div style="text-align:center; color:#888; padding:30px;" id="no-strategies-text">No published strategies</div>
                    </div>
                </div>
            </div>
            <!-- Trade History Section -->
            <div id="history-section" class="dashboard-section">
                <div class="iron-card">
                    <div class="screw tl"></div><div class="screw tr"></div>
                    <div class="screw bl"></div><div class="screw br"></div>
                    <h3 id="history-title" style="margin-bottom:25px; color:var(--gold); font-size:1.5rem;">Trade History</h3>
                    <div id="trade-history-container">
                        <div style="text-align:center; color:#888; padding:30px;" id="no-history-text">No trade history</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        // ================= الترجمة =================
        const txt = {
            en: {
                login: "Admin Login",
                username: "Username",
                password: "Password",
                loginBtn: "Login",
                logout: "Logout",
                dashboard: "Dashboard",
                signals: "Signals",
                strategies: "Strategies",
                published: "Published Strategies",
                history: "Trade History",
                users: "Active Users",
                trades: "Open Trades",
                wins: "Win Rate",
                strategiesCount: "Strategies",
                gauge: "Real-time Server Load",
                usersLabel: "Active Users",
                statusLabel: "Server Status",
                capacityLabel: "Capacity Used",
                pair: "Pair Name",
                duration: "Duration (minutes)",
                buy: "Buy",
                sell: "Sell",
                openTrades: "Open Trades",
                noTrades: "No open trades",
                strategyTitle: "Strategy Title",
                strategyContent: "Strategy Content",
                images: "Strategy Images",
                addImage: "Add Image",
                publish: "Publish",
                cancel: "Cancel",
                publishedStrategies: "Published Strategies",
                deleteAll: "Delete All",
                noStrategies: "No published strategies",
                tradeHistory: "Trade History",
                noHistory: "No trade history",
                minutes: "minutes",
                lang: "AR / EN"
            },
            ar: {
                login: "تسجيل الدخول للإدارة",
                username: "اسم المستخدم",
                password: "كلمة المرور",
                loginBtn: "تسجيل الدخول",
                logout: "تسجيل الخروج",
                dashboard: "لوحة التحكم",
                signals: "الإشارات",
                strategies: "الاستراتيجيات",
                published: "الاستراتيجيات المنشورة",
                history: "سجل الصفقات",
                users: "المستخدمين النشطين",
                trades: "الصفقات المفتوحة",
                wins: "معدل الربح",
                strategiesCount: "الاستراتيجيات",
                gauge: "تحميل الخادم الحالي",
                usersLabel: "المستخدمين النشطين",
                statusLabel: "حالة الخادم",
                capacityLabel: "السعة المستخدمة",
                pair: "اسم الزوج",
                duration: "المدة (دقائق)",
                buy: "شراء",
                sell: "بيع",
                openTrades: "الصفقات المفتوحة",
                noTrades: "لا توجد صفقات مفتوحة",
                strategyTitle: "عنوان الاستراتيجية",
                strategyContent: "محتوى الاستراتيجية",
                images: "صور الاستراتيجية",
                addImage: "إضافة صورة",
                publish: "نشر",
                cancel: "إلغاء",
                publishedStrategies: "الاستراتيجيات المنشورة",
                deleteAll: "حذف الكل",
                noStrategies: "لا توجد استراتيجيات منشورة",
                tradeHistory: "سجل الصفقات",
                noHistory: "لا يوجد سجل صفقات",
                minutes: "دقائق",
                lang: "EN / AR"
            }
        };
        let lang = 'en';
        let openTrades = [];
        let tradeHistory = [];
        let publishedStrategies = [];
        let isAuthenticated = false;
        let currentUsers = 42850; // Simulated current users

        // ================= API Integration =================
        async function fetchFromAPI(endpoint) {
            const res = await fetch(endpoint);
            return await res.json();
        }

        async function postToAPI(endpoint, data) {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await res.json();
        }

        // Override original functions to use real API
        function createSignal(direction) {
            const pairName = document.getElementById('pair-name').value;
            const duration = document.getElementById('duration').value;
            if (!pairName) {
                alert('Please enter pair name!');
                return;
            }
            postToAPI('/api/signals', {
                pair: pairName,
                direction: direction,
                duration: parseInt(duration)
            }).then(() => {
                loadOpenTrades();
                loadStats();
                document.getElementById('pair-name').value = '';
            });
        }

        function resolveTrade(tradeId, result) {
            postToAPI(`/api/signals/${tradeId}/resolve`, { result: result })
                .then(() => {
                    loadOpenTrades();
                    loadTradeHistory();
                    loadStats();
                });
        }

        function publishStrategy() {
            const title = document.getElementById('strategy-title-input').value;
            const content = document.getElementById('strategy-content').value;
            if (!title || !content) {
                alert('Please fill in all fields!');
                return;
            }
            const imageLinks = [];
            document.querySelectorAll('#image-links-container input').forEach(input => {
                if (input.value.trim()) {
                    imageLinks.push(input.value.trim());
                }
            });
            postToAPI('/api/strategies', {
                title: title,
                content: content,
                images: imageLinks
            }).then(() => {
                loadPublishedStrategies();
                loadStats();
                document.getElementById('strategy-title-input').value = '';
                document.getElementById('strategy-content').value = '';
                document.getElementById('image-links-container').innerHTML = `
                    <div class="image-link-item">
                        <input type="url" placeholder="Image URL" />
                        <button type="button" class="btn-remove-link" onclick="removeImageLink(this)">×</button>
                    </div>
                `;
            });
        }

        function deleteStrategy(strategyId) {
            fetch(`/api/strategies/${strategyId}`, { method: 'DELETE' })
                .then(() => {
                    loadPublishedStrategies();
                    loadStats();
                });
        }

        function deleteAllStrategies() {
            if (publishedStrategies.length === 0) return;
            if (confirm('Are you sure you want to delete all strategies?')) {
                fetch('/api/strategies', { method: 'DELETE' })
                    .then(() => {
                        loadPublishedStrategies();
                        loadStats();
                    });
            }
        }

        // Loaders
        async function loadStats() {
            const stats = await fetchFromAPI('/api/stats');
            document.getElementById('users-count').innerText = '8,542'; // fixed as per your UI
            document.getElementById('trades-count').innerText = stats.open_trades;
            document.getElementById('wins-count').innerText = stats.win_rate + '%';
            document.getElementById('strategies-count').innerText = stats.strategies_count;
        }

        async function loadOpenTrades() {
            const trades = await fetchFromAPI('/api/signals/active');
            const container = document.getElementById('open-trades-container');
            if (trades.length === 0) {
                container.innerHTML = `<div style="text-align:center; color:#888; padding:30px;">${txt[lang].noTrades}</div>`;
                return;
            }
            let html = '';
            trades.forEach(trade => {
                const directionText = trade.direction === 'buy' ? 
                    `<span style="color:var(--neon-green);"><i class="fa-solid fa-arrow-up"></i> ${txt[lang].buy}</span>` : 
                    `<span style="color:var(--neon-red);"><i class="fa-solid fa-arrow-down"></i> ${txt[lang].sell}</span>`;
                const durationText = `${trade.duration} ${txt[lang].minutes}`;
                html += `
                <div class="open-trade">
                    <div class="trade-header">
                        <span>${trade.pair}</span>
                        ${directionText}
                    </div>
                    <div class="trade-info">
                        <span>${durationText}</span>
                        <span>Live</span>
                    </div>
                    <div class="trade-actions">
                        <button class="btn-iron btn-win" onclick="resolveTrade('${trade.id}', 'win')">
                            <i class="fa-solid fa-trophy"></i> ${txt[lang].buy}
                        </button>
                        <button class="btn-iron btn-loss" onclick="resolveTrade('${trade.id}', 'loss')">
                            <i class="fa-solid fa-xmark"></i> ${txt[lang].sell}
                        </button>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        async function loadPublishedStrategies() {
            const strategies = await fetchFromAPI('/api/strategies');
            const container = document.getElementById('published-strategies-container');
            if (strategies.length === 0) {
                container.innerHTML = `<div style="text-align:center; color:#888; padding:30px;">${txt[lang].noStrategies}</div>`;
                return;
            }
            let html = '';
            strategies.forEach(strategy => {
                let imagesHtml = '';
                strategy.images.forEach(imgUrl => {
                    imagesHtml += `<img src="${imgUrl}" class="strategy-image" onerror="this.style.display='none'" />`;
                });
                html += `
                <div class="strategy-item">
                    <div class="strategy-header">
                        <div class="strategy-title">${strategy.title}</div>
                        <button class="btn-iron" style="background:var(--neon-red); width:auto; padding:5px 10px; font-size:0.8rem;" onclick="deleteStrategy('${strategy.id}')">
                            <i class="fa-solid fa-trash"></i> ${txt[lang].deleteAll}
                        </button>
                    </div>
                    <div class="strategy-content">
                        ${strategy.content}
                    </div>
                    <div class="strategy-images">
                        ${imagesHtml}
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        async function loadTradeHistory() {
            const history = await fetchFromAPI('/api/signals');
            const container = document.getElementById('trade-history-container');
            const completed = history.filter(h => h.status === 'completed');
            if (completed.length === 0) {
                container.innerHTML = `<div style="text-align:center; color:#888; padding:30px;">${txt[lang].noHistory}</div>`;
                return;
            }
            let html = '';
            completed.slice(0, 20).forEach(trade => {
                const directionIcon = trade.direction === 'buy' ? 
                    '<i class="fa-solid fa-arrow-up history-arrow arrow-up"></i>' : 
                    '<i class="fa-solid fa-arrow-down history-arrow arrow-down"></i>';
                const resultText = trade.result === 'win' ? 
                    '<span class="result-win">WIN</span>' : 
                    '<span class="result-loss">LOSS</span>';
                const itemClass = trade.result === 'win' ? 'history-item win' : 'history-item loss';
                const timeString = new Date(trade.resolved_at).toLocaleTimeString();
                html += `
                <div class="${itemClass}">
                    <span class="history-symbol">${trade.pair}</span>
                    ${directionIcon}
                    ${resultText}
                    <span style="color:#888; font-size:0.9rem;">${timeString}</span>
                </div>`;
            });
            container.innerHTML = html;
        }

        // WebSocket for real-time updates
        const socket = io();

        socket.on('new_signal', (signal) => {
            loadOpenTrades();
            loadStats();
        });

        socket.on('signal_resolved', (signal) => {
            loadOpenTrades();
            loadTradeHistory();
            loadStats();
        });

        // Original UI functions (keep login/logout local)
        function toggleLang() {
            lang = lang === 'en' ? 'ar' : 'en';
            document.documentElement.lang = lang;
            document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
            const t = txt[lang];
            // ... (same as your original code) ...
            document.getElementById('login-title').innerText = t.login;
            document.getElementById('username').placeholder = t.username;
            document.getElementById('password').placeholder = t.password;
            document.getElementById('login-text').innerText = t.loginBtn;
            document.getElementById('lang-text').innerText = t.lang;
            document.getElementById('logout-text').innerText = t.logout;
            document.getElementById('nav-dashboard').innerText = t.dashboard;
            document.getElementById('nav-signals').innerText = t.signals;
            document.getElementById('nav-strategies').innerText = t.strategies;
            document.getElementById('nav-published').innerText = t.published;
            document.getElementById('nav-history').innerText = t.history;
            document.getElementById('lbl-users').innerText = t.users;
            document.getElementById('lbl-trades').innerText = t.trades;
            document.getElementById('lbl-wins').innerText = t.wins;
            document.getElementById('lbl-strategies').innerText = t.strategiesCount;
            document.getElementById('gauge-title').innerText = t.gauge;
            document.getElementById('users-label').innerText = t.usersLabel;
            document.getElementById('status-label').innerText = t.statusLabel;
            document.getElementById('capacity-label').innerText = t.capacityLabel;
            document.getElementById('signals-title').innerText = t.signals;
            document.getElementById('lbl-pair').innerText = t.pair;
            document.getElementById('lbl-duration').innerText = t.duration;
            document.getElementById('btn-buy').innerText = t.buy;
            document.getElementById('btn-sell').innerText = t.sell;
            document.getElementById('open-trades-title').innerText = t.openTrades;
            document.getElementById('no-trades-text').innerText = t.noTrades;
            document.getElementById('strategy-form-title').innerText = t.strategies;
            document.getElementById('lbl-strategy-title').innerText = t.strategyTitle;
            document.getElementById('lbl-strategy-content').innerText = t.strategyContent;
            document.getElementById('lbl-images').innerText = t.images;
            document.getElementById('add-image-text').innerText = t.addImage;
            document.getElementById('publish-btn').innerText = t.publish;
            document.getElementById('cancel-btn').innerText = t.cancel;
            document.getElementById('published-title').innerText = t.publishedStrategies;
            document.getElementById('delete-all-text').innerText = t.deleteAll;
            document.getElementById('no-strategies-text').innerText = t.noStrategies;
            document.getElementById('history-title').innerText = t.tradeHistory;
            document.getElementById('no-history-text').innerText = t.noHistory;
        }

        function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            // No real auth — just allow access
            if (username && password) {
                isAuthenticated = true;
                document.getElementById('login-page').classList.add('hidden');
                document.getElementById('main-dashboard').classList.remove('hidden');
                // Load real data
                loadStats();
                loadOpenTrades();
                loadPublishedStrategies();
                loadTradeHistory();
            } else {
                alert('Please enter username and password!');
            }
        }

        function logout() {
            isAuthenticated = false;
            document.getElementById('main-dashboard').classList.add('hidden');
            document.getElementById('login-page').classList.remove('hidden');
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
        }

        function showSection(sectionId) {
            document.querySelectorAll('.dashboard-section').forEach(section => {
                section.classList.remove('active');
            });
            document.getElementById(sectionId).classList.add('active');
            document.querySelectorAll('.dashboard-sidebar a').forEach(link => {
                link.classList.remove('active');
            });
            event.target.closest('a').classList.add('active');
        }

        // Initialize
        toggleLang();
    </script>
</body>
</html>
"""

# === Run Server ===
if __name__ == '__main__':
    print("✅ SignalXPro Admin Panel جاهز للتشغيل")
    print("🔗 URL: http://localhost:5000")
    print("💾 قاعدة البيانات: signalxpro.db")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
