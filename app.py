import os
import socket
import uvicorn
from main import app

def bind_all_candidate_ports():
    sockets = []
    # Infrlo buildpacks route to 3000 or 8000
    candidate_ports = [3000, 8000, 8080, 80]
    
    env_port = os.getenv("PORT")
    if env_port:
        try:
            p = int(env_port)
            if p not in candidate_ports:
                candidate_ports.insert(0, p)
        except ValueError:
            pass

    for p in candidate_ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", p))
            s.listen(128)
            s.setblocking(False)
            sockets.append(s)
            print(f"✅ Uvicorn listening on port {p}")
        except Exception as e:
            print(f"⚠️ Port {p} unavailable: {e}")
            
    return sockets

if __name__ == "__main__":
    bound_sockets = bind_all_candidate_ports()

    config = uvicorn.Config(
        app,
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_level="info"
    )
    server = uvicorn.Server(config)

    print("🚀 Starting TG Cloud Drive server...")
    if bound_sockets:
        server.run(sockets=bound_sockets)
    else:
        server.run()
