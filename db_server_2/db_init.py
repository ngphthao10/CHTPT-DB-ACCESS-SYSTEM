import sqlite3

def init_db():
    """Khởi tạo database và tạo các bảng cần thiết"""
    conn = sqlite3.connect('database.db')
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
            ('Item 4', 'Value 4'),
            ('Item 5', 'Value 5')
        ]
        c.executemany("INSERT INTO sample_data (name, value) VALUES (?, ?)", sample_data)
    
    conn.commit()
    conn.close()
    
    print("Database initialized successfully")

if __name__ == "__main__":
    init_db()