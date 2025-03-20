class Server:
    """Model cho thông tin server"""
    def __init__(self, id, name, url):
        self.id = id
        self.name = name
        self.url = url
        self.status = "offline"
        self.client = None
        self.last_access = 0
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "status": self.status,
            "client": self.client,
            "last_access": self.last_access
        }

class Client:
    """Model cho thông tin client"""
    def __init__(self, id):
        self.id = id
        self.server = None
        self.connected_at = 0
    
    def to_dict(self):
        return {
            "id": self.id,
            "server": self.server,
            "connected_at": self.connected_at
        }