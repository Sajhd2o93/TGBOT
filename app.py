import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Launching TG Cloud Drive on 0.0.0.0:{port}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
