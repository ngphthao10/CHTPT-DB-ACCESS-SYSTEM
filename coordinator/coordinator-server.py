from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import requests
import time
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Thông tin về các database servers
database_servers = [
    {"id": 1, "name": "Database Server 1", "url": "http://192.168.214.103:5001"},
    {"id": 2, "name": "Database Server 2", "url": "http://192.168.214.103:5002"}
]

# Lưu trữ trạng thái của các database servers
server_status = {}

# Lưu trữ socket connections
socket_connections = {}

@app.route('/')
def serve_dashboard():
    return send_from_directory('.', 'dashboard.html')

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối websocket"""
    print(f"Client connected: {request.sid}")
    emit('server_status_update', {
        'servers': database_servers,
        'status': server_status
    })

# @socketio.on('register')
# def handle_register(data):
#     """Đăng ký client với ID"""
#     client_id = data.get('client_id')
#     if client_id:
#         socket_connections[client_id] = request.sid
#         print(f"Client {client_id} registered with socket {request.sid}")
#         emit('registered', {
#             'status': 'success', 
#             'message': f'Đăng ký kết nối WebSocket thành công cho client {client_id}. Gửi yêu cầu truy cập để kết nối tới server.'
#         })

@socketio.on('register')
def handle_register(data):
    client_id = data.get('client_id')
    if client_id:
        socket_connections[client_id] = request.sid
        print(f"Client {client_id} registered with socket {request.sid}")
        emit('registered', {
            'status': 'success', 
            'message': f'Đăng ký kết nối WebSocket thành công cho client {client_id}.'
        })
        # Phát thông báo tới tất cả client (bao gồm dashboard)
        socketio.emit('notification', {
            'message': f'Client {client_id} đã đăng ký kết nối.',
            'type': 'info'
        })


@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối"""
    # Tìm và xóa client_id khỏi socket_connections
    for client_id, sid in list(socket_connections.items()):
        if sid == request.sid:
            # Tự động giải phóng server nếu client disconnect
            for server_id, status in server_status.items():
                if status["current_client"] == client_id:
                    server_status[server_id]["busy"] = False
                    server_status[server_id]["current_client"] = None
                    print(f"Client {client_id} ngắt kết nối, tự động giải phóng server {server_id}")
                    
                    # Thông báo cho database server nếu cần
                    try:
                        server = next((s for s in database_servers if s["id"] == server_id), None)
                        if server:
                            requests.post(
                                f"{server['url']}/release",
                                json={"client_id": client_id},
                                timeout=10
                            )
                    except Exception as e:
                        print(f"Lỗi khi giải phóng server: {str(e)}")
            
            del socket_connections[client_id]
            print(f"Client {client_id} disconnected")
            
            # Thông báo cập nhật trạng thái server cho tất cả client
            socketio.emit('server_status_change', {
                'servers': database_servers,
                'status': server_status
            })
            break

@app.route('/request_access', methods=['POST'])
def request_access():
    """Endpoint cho client yêu cầu quyền truy cập database"""
    data = request.json
    client_id = data.get('client_id')
    
    if not client_id:
        return jsonify({"error": "Client ID is required"}), 400
    
    # Kiểm tra xem client này đã đang kết nối tới server nào chưa
    for server_id, status in server_status.items():
        if status.get("current_client") == client_id:
            # Client đã kết nối tới một server
            server = next((s for s in database_servers if s["id"] == int(server_id)), None)
            if server:
                return jsonify({
                    "error": "Client already connected", 
                    "message": f"Client {client_id} đã đang truy cập {server['name']}",
                    "server_id": server["id"],
                    "server_name": server["name"],
                    "server_url": server["url"]
                }), 409  # Conflict status code
    
    # Kiểm tra xem tất cả server có đang bận không TRƯỚC KHI thử chọn server
    busy_servers = 0
    for status in server_status.values():
        if status.get("busy", False):
            busy_servers += 1
    
    if busy_servers >= len(database_servers):
        # Thu thập thông tin các client đang kết nối để hiển thị
        connected_clients = []
        for srv_id, status in server_status.items():
            if status.get("current_client"):
                connected_clients.append(f"Server {srv_id}: Client {status.get('current_client')}")
        
        connected_info = ", ".join(connected_clients)
        
        return jsonify({
            "error": f"All database servers are busy. Clients đang kết nối: {connected_info}"
        }), 503
    
    # Chọn database server phù hợp
    selected_server = select_database_server()
    
    if not selected_server:
        return jsonify({"error": "All database servers are busy. Please try again later."}), 503
    
    # Cập nhật trạng thái server
    server_id = selected_server["id"]
    server_status[server_id]["busy"] = True
    server_status[server_id]["current_client"] = client_id
    server_status[server_id]["last_access"] = time.time()
    
    print(f"CLIENT {client_id} được điều phối đến {selected_server['name']}")
    
    # Thông báo cho database server về client sắp kết nối
    try:
        notify_database_server(selected_server, client_id)
    except Exception as e:
        # Reset trạng thái server nếu thông báo thất bại
        server_status[server_id]["busy"] = False
        server_status[server_id]["current_client"] = None
        print(f"Lỗi thông báo DB server: {str(e)}")
        return jsonify({"error": f"Không thể thông báo cho database server: {str(e)}"}), 500
    
    # Thông báo qua WebSocket nếu client đã đăng ký
    if client_id in socket_connections:
        socketio.emit('server_assigned', {
            "server_id": selected_server["id"],
            "server_name": selected_server["name"],
            "server_url": selected_server["url"]
        }, room=socket_connections[client_id])

        socketio.emit('notification', {
            'message': f'Client {client_id} được gán tới {selected_server["name"]}.',
            'type': 'success'
        })
    
    # Thông báo cập nhật trạng thái server cho tất cả client
    socketio.emit('server_status_change', {
        'servers': database_servers,
        'status': server_status
    })
    
    return jsonify({
        "server_id": selected_server["id"],
        "server_name": selected_server["name"],
        "server_url": selected_server["url"]
    })

@app.route('/release_access', methods=['POST'])
def release_access():
    """Endpoint cho client giải phóng quyền truy cập"""
    data = request.json
    client_id = data.get('client_id')
    
    if not client_id:
        return jsonify({"error": "Client ID is required"}), 400
    
    # Nếu không cung cấp server_id, tìm tất cả server mà client này đang sử dụng
    released_servers = []
    
    # Giải phóng tất cả server mà client này đang sử dụng
    for svr_id_str, status in server_status.items():
        # Chuyển đổi svr_id từ string sang int nếu cần
        svr_id = int(svr_id_str) if isinstance(svr_id_str, str) else svr_id_str
        
        current_client = status.get("current_client")
        
        if current_client == client_id:
            server_status[svr_id]["busy"] = False
            server_status[svr_id]["current_client"] = None
            released_servers.append(svr_id)
            print(f"Released server {svr_id}")

        socketio.emit('notification', {
            'message': f'Client {client_id} đã ngắt kết nối/giải phóng quyền truy cập.',
            'type': 'warning'
        })

    
    if released_servers:
        # Thông báo cập nhật trạng thái server cho tất cả client
        socketio.emit('server_status_change', {
            'servers': database_servers,
            'status': server_status
        })
        
        return jsonify({
            "status": "success", 
            "message": f"Access released successfully for {len(released_servers)} servers",
            "released_servers": released_servers
        })
    
    # Nếu không tìm thấy server nào, kiểm tra lại tất cả những client đang kết nối
    connected_clients = []
    for svr_id, status in server_status.items():
        if status.get("current_client"):
            connected_clients.append({
                "server_id": svr_id,
                "client_id": status.get("current_client")
            })
    
    return jsonify({
        "error": "No servers found for this client", 
        "client_id": client_id,
        "connected_clients": connected_clients
    }), 404
    
@app.route('/server_status', methods=['GET'])
def get_server_status():
    return jsonify({
        "servers": database_servers,
        "status": server_status
    })

def select_database_server():
    """Thuật toán chọn database server dựa trên trạng thái hiện tại"""
    # Kiểm tra xem có server nào không bận
    available_servers = []
    
    for server_id, status in server_status.items():
        is_busy = status.get("busy", False)
        
        if not is_busy:
            available_servers.append(server_id)
    
    # Nếu không có server nào available
    if not available_servers:
        return None
    
    # Nếu có nhiều server available, chọn server được truy cập lâu nhất
    if len(available_servers) > 1:
        min_last_access = float('inf')
        selected_id = None
        
        for server_id in available_servers:
            if server_status[server_id]["last_access"] < min_last_access:
                min_last_access = server_status[server_id]["last_access"]
                selected_id = server_id
        
        return next((s for s in database_servers if s["id"] == int(selected_id)), None)
    
    # Nếu chỉ có một server available
    server_id = available_servers[0]
    return next((s for s in database_servers if s["id"] == int(server_id)), None)

def notify_database_server(server, client_id):
    """Thông báo cho database server về client sắp kết nối"""
    try:
        response = requests.post(
            f"{server['url']}/notify_access",
            json={"client_id": client_id},
            timeout=12
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Lỗi khi thông báo cho server {server['name']}: {str(e)}")
        raise

def init_server_status():
    """Khởi tạo trạng thái các server"""
    global server_status
    for server in database_servers:
        server_status[server["id"]] = {
            "busy": False,
            "current_client": None,
            "last_access": 0
        }

if __name__ == '__main__':
    init_server_status()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)