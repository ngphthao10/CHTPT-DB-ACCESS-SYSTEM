# Hệ thống điều phối truy cập CSDL

Hệ thống điều phối truy cập cơ sở dữ liệu cho phép quản lý và giám sát việc truy cập của các client vào các database server trong mạng nội bộ. Hệ thống đảm bảo mỗi client chỉ được truy cập vào một server tại một thời điểm và cung cấp giao diện web để theo dõi trạng thái hệ thống theo thời gian thực.

## Kiến trúc hệ thống

Hệ thống gồm 3 thành phần chính:

1. **Coordinator** (Máy điều phối): Nhận yêu cầu từ client và chỉ định database server phù hợp
2. **Database Servers** (2 máy CSDL giống nhau): Chứa dữ liệu và xử lý các truy vấn từ client
3. **Clients**: Các máy tính có nhu cầu truy cập dữ liệu

## Cài đặt

### Yêu cầu

- Python 3.6+
- pip

### Thiết lập

```bash
# Clone repository
git clone <repository-url>
cd db-access-system
```

1. Máy điều phối (Coordinator):

```bash
cd coordinator
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Database Server 1:

```bash
cd db_server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. Database Server 2:

```bash
cd db_server_2
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
```

4. Client:

```bash
cd client
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Khởi động hệ thống

Bước 1: Khởi động Coordinator

```bash
cd coordinator
python coordinator-server.py
```

Coordinator sẽ chạy trên http://localhost:5000.

Bước 2: Khởi động Database Server 1

```bash
cd db_server
python db-server-websocket.py
```

Database Server 1 sẽ chạy trên http://localhost:5001.

Bước 3: Khởi động Database Server 2

```bash
cd db_server_2
python db-server-websocket.py
```

Database Server 2 sẽ chạy trên http://localhost:5002.

Bước 4: Truy cập Dashboard

Mở trình duyệt web và truy cập http://localhost:5000 để theo dõi trạng thái hệ thống thông qua dashboard.

## Các tính năng chính

* Coordinator quản lý việc phân bổ client đến database server
* Mỗi client chỉ được phép truy cập vào một server tại một thời điểm
* Cập nhật tình trạng server và client theo thời gian thực
* Dashboard trực quan để theo dõi và điều khiển hệ thống
* Tự động giải phóng tài nguyên khi client ngắt kết nối

### Lưu ý

* Đảm bảo các cổng 5000, 5001 và 5002 không bị sử dụng bởi các ứng dụng khác
* Mặc định, hệ thống chạy trên localhost. Để kết nối qua mạng, cần điều chỉnh cấu hình IP trong các file

## Công nghệ sử dụng

### Backend

Python

* Framework Flask: Microframework Python để xây dựng API và web server nhẹ, linh hoạt
* Flask-SocketIO: Mở rộng của Flask để hỗ trợ WebSocket và giao tiếp real-time
* Python-SocketIO: Thư viện client WebSocket dành cho Python

Cơ sở dữ liệu

* SQLite: Hệ quản trị cơ sở dữ liệu nhẹ, không cần cài đặt server riêng, tích hợp trong mỗi instance database server
* SQLite3: Module tích hợp sẵn của Python để tương tác với SQLite database

Giao tiếp mạng

* Requests: Thư viện HTTP cho Python, được sử dụng để giao tiếp giữa các thành phần qua REST API
* WebSocket: Giao thức giao tiếp hai chiều, real-time qua một kết nối TCP duy nhất
* CORS (Cross-Origin Resource Sharing): Cơ chế cho phép các truy cập tài nguyên từ các domain khác nhau

### Quản lý môi trường

* Virtualenv: Công cụ tạo môi trường ảo Python riêng biệt cho mỗi thành phần
* Requirements.txt: Quản lý phụ thuộc và phiên bản thư viện

### Frontend

Web Technologies

* HTML5: Markup language cho giao diện người dùng
* CSS3: Định dạng và tạo style cho giao diện
* JavaScript (ES6+): Xử lý tương tác phía client và cập nhật UI động

Frameworks & Libraries

* Bootstrap 5: Framework CSS cho UI responsive và hiện đại
* Font Awesome 6: Thư viện icon vector được sử dụng cho các biểu tượng trực quan
* Socket.IO Client: JavaScript client cho WebSocket, giúp kết nối real-time với server

Tương tác API

* Fetch API: Giao diện JavaScript hiện đại để thực hiện các HTTP request
* JSON: Định dạng dữ liệu trao đổi giữa client và server

### Kiến trúc Hệ thống

* Mô hình Client-Server: Sử dụng mô hình client-server truyền thống với tầng điều phối (coordinator) làm trung gian
* Real-time Communication: Kết hợp giữa RESTful API và WebSocket để cả xử lý request/response thông thường và giao tiếp real-time
* Microservices: Hệ thống chia thành các thành phần độc lập (coordinator, database servers, clients) có thể triển khai và mở rộng riêng biệt
* Stateful Design: Hệ thống lưu trạng thái phiên làm việc và kết nối của client

### Kỹ thuật Lập trình

* Event-driven Programming: Lập trình hướng sự kiện với WebSocket
* Asynchronous I/O: Xử lý không đồng bộ cho các thao tác mạng và I/O
* RESTful API Design: Thiết kế API theo nguyên tắc REST
* Reactive UI Updates: Cập nhật UI phản ứng với thay đổi dữ liệu từ server