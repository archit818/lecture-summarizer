import requests
import sys
from lecture_ai import config

def send_command(endpoint):
    url = f"http://{config.SERVER_HOST}:{config.SERVER_PORT}/{endpoint}"
    headers = {"Authorization": f"Bearer {config.AUTH_TOKEN}"}
    
    try:
        if endpoint == "status":
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers)
            
        if response.status_code == 200:
            print(f"Success: {response.json()}")
        else:
            print(f"Error ({response.status_code}): {response.json()}")
    except Exception as e:
        print(f"Failed to connect to server: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python control.py [start|stop|status]")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    if cmd in ["start", "stop", "status"]:
        send_command(cmd)
    else:
        print(f"Unknown command: {cmd}")
