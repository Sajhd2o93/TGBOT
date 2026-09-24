import os
import asyncio
import uvicorn
from main import app

async def run_port(port: int):
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_level="info"
    )
    server = uvicorn.Server(config)
    try:
        print(f"🚀 Listener active on 0.0.0.0:{port}")
        await server.serve()
    except Exception as e:
        print(f"⚠️ Port {port} binding skipped: {e}")

async def main():
    print("--- ENVIRONMENT KEYS DETECTED ---")
    for key in sorted(os.environ.keys()):
        if any(secret in key.lower() for secret in ["token", "hash", "secret", "password", "key"]):
            print(f"  {key} = [HIDDEN]")
        else:
            print(f"  {key} = {os.environ[key]}")
    print("--------------------------------")

    ports_to_try = [8000, 8080, 5000, 3000, 80]
    
    env_port = os.getenv("PORT")
    if env_port:
        try:
            p = int(env_port)
            if p not in ports_to_try:
                ports_to_try.insert(0, p)
        except ValueError:
            pass

    print(f"🌐 Multi-port listener starting on ports: {ports_to_try}")
    
    # Run servers on all candidate ports concurrently
    servers = [run_port(p) for p in ports_to_try]
    await asyncio.gather(*servers)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
