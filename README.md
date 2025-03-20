# Hệ thống điều phối truy cập CSDL

Hệ thống quản lý và điều phối các client truy cập vào database server trên mạng nội bộ.

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

# Chạy script thiết lập
# Linux/Mac
./scripts/setup.sh
# Windows
scripts\setup.bat