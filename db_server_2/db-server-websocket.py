from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3
import datetime
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ID của database server này (thay đổi cho mỗi máy chủ)
SERVER_ID = 2  # Đặt là 1 cho server 1, 2 cho server 2
SERVER_PORT = 5002  # Port mặc định cho server 1, sử dụng 5002 cho server 2

# Lưu trữ thông tin client hiện tại
current_client = None

# Lưu trữ socket connections
socket_connections = {}

# Tạo và khởi tạo cơ sở dữ liệu
def init_db():
    """Khởi tạo cơ sở dữ liệu nếu chưa tồn tại"""
    db_file = f'database_server{SERVER_ID}.db'
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    # Tạo bảng access_log để ghi lại lịch sử truy cập
    c.execute('''
    CREATE TABLE IF NOT EXISTS access_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        access_time TIMESTAMP NOT NULL,
        operation TEXT
    )
    ''')
    
    # Tạo bảng dữ liệu mẫu nếu chưa có
    c.execute('''
    CREATE TABLE IF NOT EXISTS sample_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        value TEXT NOT NULL
    )
    ''')
    
    # Thêm dữ liệu mẫu nếu bảng trống
    c.execute("SELECT COUNT(*) FROM sample_data")
    if c.fetchone()[0] == 0:
        sample_data = [
            ('Item 1', 'Value 1'),
            ('Item 2', 'Value 2'),
            ('Item 3', 'Value 3'),
            ('Item 4', f'Value 4 from Server {SERVER_ID}'),
            ('Item 5', f'Value 5 from Server {SERVER_ID}')
        ]
        c.executemany("INSERT INTO sample_data (name, value) VALUES (?, ?)", sample_data)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized for server {SERVER_ID}")

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối websocket"""
    print(f"Client connected to database server {SERVER_ID}: {request.sid}")

@socketio.on('register_db_client')
def handle_register(data):
    """Đăng ký client với server"""
    client_id = data.get('client_id')
    if client_id:
        socket_connections[client_id] = request.sid
        print(f"Client {client_id} registered with DB server {SERVER_ID}, socket: {request.sid}")
        
        # Kiểm tra xem client này có phải là client hiện tại không
        if client_id == current_client:
            emit('db_registered', {
                'status': 'success', 
                'message': f'Registered as {client_id} with database server {SERVER_ID}'
            })
        else:
            emit('db_registered', {
                'status': 'warning',
                'message': f'Connected to server {SERVER_ID} but not authorized for access'
            })

@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối"""
    global current_client
    
    # Tìm và xóa client_id khỏi socket_connections
    for client_id, sid in list(socket_connections.items()):
        if sid == request.sid:
            # Nếu client này là client hiện tại, reset trạng thái
            if client_id == current_client:
                print(f"Client {client_id} đã ngắt kết nối từ database server {SERVER_ID}")
                current_client = None
                
                # Ghi log giải phóng tự động
                log_access(client_id, "auto_release")
                
                # Broadcast thông tin cập nhật
                socketio.emit('client_disconnected', {
                    'client_id': client_id,
                    'server_id': SERVER_ID,
                    'message': f"Client {client_id} đã ngắt kết nối từ Database Server {SERVER_ID}"
                })
            
            del socket_connections[client_id]
            break

@app.route('/notify_access', methods=['POST'])
def notify_access():
    """Endpoint để coordinator thông báo rằng một client sẽ truy cập server này"""
    global current_client
    
    data = request.json
    client_id = data.get('client_id')
    
    if not client_id:
        return jsonify({"error": "Client ID is required"}), 400
    
    # Lưu client hiện tại
    current_client = client_id
    
    # Hiển thị thông báo về client đang truy cập
    print(f"=== DATABASE SERVER {SERVER_ID} ===")
    print(f"Client {client_id} đang truy cập Database Server {SERVER_ID}")
    print("=====================================")
    
    # Ghi log truy cập
    log_access(client_id, "connect")
    
    # Broadcast thông tin truy cập cho tất cả các kết nối
    socketio.emit('client_accessing', {
        'client_id': client_id,
        'server_id': SERVER_ID,
        'timestamp': datetime.datetime.now().isoformat(),
        'message': f"Client {client_id} đang truy cập Database Server {SERVER_ID}"
    })
    
    return jsonify({
        "status": "success",
        "message": f"Database Server {SERVER_ID} ready for client {client_id}"
    })

@app.route('/data', methods=['GET'])
def get_data():
    """Endpoint để client truy vấn dữ liệu"""
    client_id = request.headers.get('X-Client-ID')
    
    if not client_id:
        return jsonify({"error": "Client ID header is required"}), 400
    
    # Kiểm tra xem client này có phải là client đã được thông báo không
    if client_id != current_client:
        return jsonify({
            "error": "Unauthorized access. This client was not assigned to this server."
        }), 403
    
    # Log truy cập dữ liệu
    log_access(client_id, "query_data")
    
    # Hiển thị thông báo truy cập
    print(f"=== DATABASE SERVER {SERVER_ID} ===")
    print(f"Client {client_id} đang truy xuất dữ liệu từ Database Server {SERVER_ID}")
    print("=====================================")
    
    # Broadcast thông báo
    socketio.emit('data_accessed', {
        'client_id': client_id,
        'server_id': SERVER_ID,
        'timestamp': datetime.datetime.now().isoformat(),
        'message': f"Client {client_id} đang truy xuất dữ liệu từ Database Server {SERVER_ID}"
    })
    
    # Lấy dữ liệu từ database
    db_file = f'database_server{SERVER_ID}.db'
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM sample_data")
    rows = c.fetchall()
    
    # Chuyển đổi kết quả thành list of dict
    data = [dict(row) for row in rows]
    conn.close()
    
    return jsonify({
        "server_id": SERVER_ID,
        "data": data,
        "timestamp": datetime.datetime.now().isoformat()
    })

@app.route('/release', methods=['POST'])
def release_access():
    """Endpoint để client thông báo đã hoàn thành truy cập"""
    global current_client
    
    data = request.json
    client_id = data.get('client_id')
    
    if not client_id:
        return jsonify({"error": "Client ID is required"}), 400
    
    # Kiểm tra xem client này có phải là client hiện tại không
    if client_id != current_client:
        return jsonify({
            "error": "Unauthorized access. This client was not assigned to this server."
        }), 403
    
    # Log giải phóng truy cập
    log_access(client_id, "release")
    
    # Reset client hiện tại
    current_client = None
    
    # Hiển thị thông báo giải phóng
    print(f"=== DATABASE SERVER {SERVER_ID} ===")
    print(f"Client {client_id} đã giải phóng Database Server {SERVER_ID}")
    print("=====================================")
    
    # Broadcast thông báo
    socketio.emit('access_released', {
        'client_id': client_id,
        'server_id': SERVER_ID,
        'timestamp': datetime.datetime.now().isoformat(),
        'message': f"Client {client_id} đã giải phóng Database Server {SERVER_ID}"
    })
    
    return jsonify({
        "status": "success",
        "message": f"Access released for client {client_id}"
    })

@app.route('/status', methods=['GET'])
def server_status():
    """Endpoint để kiểm tra trạng thái server"""
    db_file = f'database_server{SERVER_ID}.db'
    
    # Đếm số lần truy cập
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM access_log")
    access_count = c.fetchone()[0]
    
    c.execute("SELECT * FROM access_log ORDER BY access_time DESC LIMIT 10")
    recent_logs = c.fetchall()
    
    conn.close()
    
    # Định dạng log gần đây thành list
    recent_activity = []
    for log in recent_logs:
        recent_activity.append({
            "client_id": log[1],
            "time": log[2],
            "operation": log[3]
        })
    
    return jsonify({
        "server_id": SERVER_ID,
        "status": "active",
        "current_client": current_client,
        "access_count": access_count,
        "recent_activity": recent_activity
    })

def log_access(client_id, operation):
    """Ghi log truy cập vào database"""
    db_file = f'database_server{SERVER_ID}.db'
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    now = datetime.datetime.now().isoformat()
    c.execute(
        "INSERT INTO access_log (client_id, access_time, operation) VALUES (?, ?, ?)",
        (client_id, now, operation)
    )
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Khởi tạo cơ sở dữ liệu
    init_db()
    
    # Sử dụng port tùy chỉnh nếu có từ môi trường
    port = int(os.environ.get('PORT', SERVER_PORT))
    
    # Chạy ứng dụng với socketio
    socketio.run(app, host='0.0.0.0', port=port, debug=True)