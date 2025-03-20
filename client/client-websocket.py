import requests
import time
import uuid
import sys
import socketio
import argparse
import json

class DatabaseClient:
    def __init__(self, coordinator_url=None, client_id=None):
        self.client_id = client_id or str(uuid.uuid4())[:8]
        self.coordinator_url = coordinator_url or "http://localhost:5000"
        self.current_server = None
        
        # Khởi tạo socket cho coordinator
        self.socket = socketio.Client()
        self.setup_coordinator_socket()
        
        # Socket cho database server
        self.db_socket = None
        
        # Trạng thái
        self.is_connected_to_coordinator = False
        self.is_connected_to_db = False
    
    def setup_coordinator_socket(self):
        """Thiết lập các event handler cho WebSocket tới Coordinator"""
        @self.socket.event
        def connect():
            self.is_connected_to_coordinator = True
            print(f"[WebSocket] Đã kết nối tới Coordinator")
            # Đăng ký client với coordinator
            self.socket.emit('register', {'client_id': self.client_id})
        
        @self.socket.event
        def disconnect():
            self.is_connected_to_coordinator = False
            print("[WebSocket] Ngắt kết nối từ Coordinator")
        
        @self.socket.event
        def registered(data):
            print(f"[WebSocket] Đăng ký với Coordinator thành công: {data['message']}")
        
        @self.socket.event
        def server_assigned(data):
            print(f"[WebSocket] Thông báo từ Coordinator: Được gán vào {data['server_name']}")
            self.current_server = data
            
            # Kết nối đến database server thông qua websocket
            self.connect_to_db_server()
        
        @self.socket.event
        def server_status_change(data):
            # Cập nhật trạng thái server từ Coordinator
            if self.current_server:
                server_id = self.current_server["server_id"]
                for server in data["servers"]:
                    if server["id"] == server_id:
                        status = data["status"].get(str(server_id), {})
                        current_client = status.get("current_client")
                        
                        if current_client != self.client_id:
                            print(f"[WebSocket] Cảnh báo: Server {server_id} đã được gán cho client khác hoặc đã được giải phóng")
    
    def setup_db_socket(self):
        """Thiết lập các event handler cho WebSocket tới Database Server"""
        @self.db_socket.event
        def connect():
            self.is_connected_to_db = True
            print(f"[WebSocket] Đã kết nối tới Database Server {self.current_server['server_name']}")
            # Đăng ký với database server
            self.db_socket.emit('register_db_client', {'client_id': self.client_id})
        
        @self.db_socket.event
        def disconnect():
            self.is_connected_to_db = False
            print(f"[WebSocket] Ngắt kết nối từ Database Server")
        
        @self.db_socket.event
        def db_registered(data):
            print(f"[WebSocket] Đăng ký với Database Server: {data['message']}")
        
        @self.db_socket.event
        def client_accessing(data):
            if data['client_id'] != self.client_id:
                print(f"[WebSocket] Thông báo: Client {data['client_id']} đang truy cập Database Server {data['server_id']}")
        
        @self.db_socket.event
        def access_released(data):
            if data['client_id'] == self.client_id:
                print(f"[WebSocket] Thông báo: Bạn đã giải phóng Database Server {data['server_id']}")
            else:
                print(f"[WebSocket] Thông báo: Client {data['client_id']} đã giải phóng Database Server {data['server_id']}")
        
        @self.db_socket.event
        def data_accessed(data):
            if data['client_id'] == self.client_id:
                print(f"[WebSocket] Thông báo: Bạn đang truy xuất dữ liệu từ Database Server {data['server_id']}")
    
    def connect_to_coordinator(self):
        """Kết nối WebSocket đến coordinator"""
        try:
            # Chuẩn hóa URL
            socket_url = self.coordinator_url
            if socket_url.startswith('http://'):
                socket_url = socket_url.replace('http://', '')
            elif socket_url.startswith('https://'):
                socket_url = socket_url.replace('https://', '')
                
            # Thêm tùy chọn cho socketio
            self.socket = socketio.Client(logger=True, engineio_logger=True)
            self.setup_coordinator_socket()
            
            # Thực hiện kết nối với thêm tùy chọn transport
            self.socket.connect(
                f'http://{socket_url}',
                transports=['websocket', 'polling'],
                wait_timeout=10
            )
            return True
        except Exception as e:
            print(f"Lỗi kết nối WebSocket đến coordinator: {str(e)}")
            return False
    
    def connect_to_db_server(self):
        """Kết nối WebSocket đến database server"""
        if not self.current_server:
            print("Không thể kết nối đến Database Server: Chưa được gán server")
            return False
        
        try:
            # Ngắt kết nối cũ nếu có
            if self.db_socket and self.db_socket.connected:
                self.db_socket.disconnect()
            
            # Tạo kết nối mới
            self.db_socket = socketio.Client()
            self.setup_db_socket()
            
            # Chuẩn hóa URL
            socket_url = self.current_server['server_url']
            if socket_url.startswith('http://'):
                socket_url = socket_url.replace('http://', '')
            elif socket_url.startswith('https://'):
                socket_url = socket_url.replace('https://', '')
                
            self.db_socket.connect(f'http://{socket_url}')
            return True
        except Exception as e:
            print(f"Lỗi kết nối WebSocket đến database server: {str(e)}")
            return False
    
    def request_database_access(self):
        """Yêu cầu quyền truy cập database từ coordinator"""
        print(f"Client {self.client_id} đang yêu cầu quyền truy cập database...")
        
        try:
            response = requests.post(
                f"{self.coordinator_url}/request_access",
                json={"client_id": self.client_id},
                timeout=5
            )
            
            # Xử lý response thành công
            if response.status_code == 200:
                self.current_server = response.json()
                print(f"✅ Được cấp quyền truy cập vào {self.current_server['server_name']}")
                
                # Kết nối WebSocket đến database server nếu chưa kết nối
                if not self.is_connected_to_db:
                    self.connect_to_db_server()
                
                return True
            
            # Client đã kết nối tới một server (status code 409)
            elif response.status_code == 409:
                self.current_server = response.json()
                print(f"ℹ️ {response.json().get('message', 'Bạn đã được kết nối đến một server')}")
                return True
            
            # Các server đều bận (status code 503)
            elif response.status_code == 503:
                print(f"⚠️ {response.json().get('error', 'Tất cả server đều đang bận')}")
                return False
            
            # Các lỗi khác
            else:
                print(f"❌ Lỗi khi yêu cầu quyền truy cập: {response.json().get('error')}")
                return False
        
        except Exception as e:
            print(f"❌ Lỗi kết nối tới coordinator: {str(e)}")
            return False
    
    def access_database(self):
        """Truy cập database server đã được chỉ định"""
        if not self.current_server:
            print("❌ Chưa được cấp quyền truy cập database. Hãy yêu cầu quyền trước.")
            return None
        
        try:
            # Thêm header client ID vào request
            headers = {"X-Client-ID": self.client_id}
            
            # Truy vấn dữ liệu
            print(f"📤 Đang gửi yêu cầu truy xuất dữ liệu đến {self.current_server['server_name']}...")
            response = requests.get(
                f"{self.current_server['server_url']}/data",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                print("📥 Nhận dữ liệu thành công!")
                return response.json()
            else:
                print(f"❌ Lỗi khi truy cập database: {response.json().get('error')}")
                return None
        
        except Exception as e:
            print(f"❌ Lỗi kết nối tới database server: {str(e)}")
            return None
    
    def release_access(self):
        """Giải phóng quyền truy cập database"""
        if not self.current_server:
            print("ℹ️ Không có server nào để giải phóng.")
            return False
        
        try:
            # Thông báo database server
            print(f"📤 Đang thông báo giải phóng đến {self.current_server['server_name']}...")
            db_response = requests.post(
                f"{self.current_server['server_url']}/release",
                json={"client_id": self.client_id},
                timeout=5
            )
            
            # Thông báo coordinator
            print("📤 Đang thông báo giải phóng đến Coordinator...")
            coord_response = requests.post(
                f"{self.coordinator_url}/release_access",
                json={
                    "client_id": self.client_id,
                    "server_id": self.current_server["server_id"]
                },
                timeout=5
            )
            
            if db_response.status_code == 200 and coord_response.status_code == 200:
                print(f"✅ Đã giải phóng quyền truy cập từ {self.current_server['server_name']}")
                self.current_server = None
                return True
            else:
                print("❌ Lỗi khi giải phóng quyền truy cập:")
                if db_response.status_code != 200:
                    print(f"  - Database server: {db_response.json().get('error')}")
                if coord_response.status_code != 200:
                    print(f"  - Coordinator: {coord_response.json().get('error')}")
                return False
        
        except Exception as e:
            print(f"❌ Lỗi khi giải phóng quyền truy cập: {str(e)}")
            return False
    
    def view_server_status(self):
        """Xem trạng thái các server"""
        try:
            response = requests.get(f"{self.coordinator_url}/server_status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                print("\n=== TRẠNG THÁI SERVER ===")
                for server in data["servers"]:
                    server_id = server["id"]
                    status = data["status"].get(str(server_id), {})
                    is_busy = status.get("busy", False)
                    current_client = status.get("current_client", "Không có")
                    
                    print(f"Server {server['name']}:")
                    print(f"  - URL: {server['url']}")
                    print(f"  - Trạng thái: {'Đang bận' if is_busy else 'Sẵn sàng'}")
                    if is_busy:
                        print(f"  - Client đang truy cập: {current_client}")
                    print("")
                
                return data
            else:
                print(f"❌ Lỗi khi lấy trạng thái server: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Lỗi kết nối đến coordinator: {str(e)}")
            return None
    
    def run_demo(self):
        """Chạy demo truy cập database"""
        print(f"\n=== CLIENT {self.client_id} STARTING ===\n")
        
        # Kết nối WebSocket đến coordinator
        if not self.connect_to_coordinator():
            print("⚠️ Không thể kết nối WebSocket đến coordinator. Sẽ tiếp tục với REST API.")
        
        # Hiển thị trạng thái server
        self.view_server_status()
        
        # Yêu cầu quyền truy cập
        if not self.request_database_access():
            print("❌ Không thể yêu cầu quyền truy cập. Đang kết thúc.")
            return
        
        # Truy cập database 
        print("\n📊 Đang truy cập database...")
        data = self.access_database()
        
        if data:
            print(f"\n📋 Dữ liệu từ Database Server {data['server_id']}:")
            for item in data['data']:
                print(f"  - {item['name']}: {item['value']}")
        else:
            print("❌ Không nhận được dữ liệu từ server")
        
        # Giả lập thời gian xử lý
        print("\n⏳ Đang xử lý dữ liệu...")
        for i in range(3):
            print(f"  Xử lý... {i+1}/3")
            time.sleep(1)
        
        # Giải phóng quyền truy cập
        print("\n🔓 Đang giải phóng quyền truy cập...")
        self.release_access()
        
        # Hiển thị trạng thái server sau khi giải phóng
        self.view_server_status()
        
        print(f"\n=== CLIENT {self.client_id} FINISHED ===")
    
    def cleanup(self):
        """Dọn dẹp kết nối khi kết thúc"""
        try:
            if self.db_socket and self.db_socket.connected:
                print("Đang ngắt kết nối từ Database Server...")
                self.db_socket.disconnect()
            
            if self.socket and self.socket.connected:
                print("Đang ngắt kết nối từ Coordinator...")
                self.socket.disconnect()
        except Exception as e:
            print(f"Lỗi khi dọn dẹp kết nối: {str(e)}")

def parse_arguments():
    """Xử lý tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Client truy cập database')
    parser.add_argument('-c', '--coordinator', 
                        default="http://localhost:5000",
                        help='URL của Coordinator (mặc định: http://localhost:5000)')
    parser.add_argument('-i', '--id', 
                        help='ID của client (mặc định: tự động tạo)')
    parser.add_argument('--gui', action='store_true',
                        help='Mở giao diện web dashboard thay vì chạy demo')
    return parser.parse_args()

if __name__ == "__main__":
    # Xử lý tham số dòng lệnh
    args = parse_arguments()
    
    if args.gui:
        # Mở dashboard trên trình duyệt
        import webbrowser
        webbrowser.open(args.coordinator)
        print(f"Đã mở dashboard tại {args.coordinator}")
        sys.exit(0)
    
    try:
        # Tạo và chạy client
        client = DatabaseClient(args.coordinator, args.id)
        client.run_demo()
    except KeyboardInterrupt:
        print("\n\nNgắt bởi người dùng. Đang thoát...")
    finally:
        # Đảm bảo dọn dẹp kết nối
        if 'client' in locals():
            client.cleanup()