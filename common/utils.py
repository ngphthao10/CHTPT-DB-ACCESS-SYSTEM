import time
import json

def log_to_file(filename, message):
    """Ghi log ra file"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def format_response(success=True, data=None, error=None):
    """Định dạng chuẩn cho response API"""
    response = {
        "success": success,
        "timestamp": time.time()
    }
    
    if data is not None:
        response["data"] = data
    
    if error is not None:
        response["error"] = error
    
    return response

def parse_json_safely(json_str):
    """Parse JSON an toàn, trả về None nếu có lỗi"""
    try:
        return json.loads(json_str)
    except:
        return None