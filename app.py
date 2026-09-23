import os
import uvicorn
from main import app

if __name__ == "__main__":
    # Log environment variables (without secret values)
    print("--- ENVIRONMENT KEYS DETECTED ---")
    for key in sorted(os.environ.keys()):
        if any(secret in key.lower() for secret in ["token", "hash", "secret", "password", "key"]):
            print(f"  {key} = [HIDDEN]")
        else:
            print(f"  {key} = {os.environ[key]}")
    print("--------------------------------")

    # Infrlo Buildpack default port detection (3000 / 8080)
    port_env = os.getenv("PORT")
    if port_env:
        port = int(port_env)
        print(f"🌐 Using system PORT environment variable: {port}")
    else:
        # Buildpack default port is 3000
        port = int(os.getenv("CONTAINER_PORT", "3000"))
        print(f"🌐 PORT environment variable not found, using Buildpack default port: {port}")

    print(f"🚀 Starting Uvicorn server on 0.0.0.0:{port}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
