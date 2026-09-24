import os
import asyncio
import uvicorn
from main import app

async def start_tcp_forwarder(source_port: int, target_port: int):
    """Forwards incoming TCP connections from source_port to target_port."""
    async def handle_client(client_reader, client_writer):
        try:
            target_reader, target_writer = await asyncio.open_connection('127.0.0.1', target_port)
        except Exception:
            client_writer.close()
            return

        async def pipe(r, w):
            try:
                while True:
                    data = await r.read(65536)
                    if not data:
                        break
                    w.write(data)
                    await w.drain()
            except Exception:
                pass
            finally:
                try:
                    w.close()
                except Exception:
                    pass

        await asyncio.gather(
            pipe(client_reader, target_writer),
            pipe(target_reader, client_writer)
        )

    try:
        server = await asyncio.start_server(handle_client, '0.0.0.0', source_port)
        print(f"🔗 Forwarder active: 0.0.0.0:{source_port} -> 127.0.0.1:{target_port}")
        async with server:
            await server.serve_forever()
    except Exception as e:
        print(f"Forwarder on {source_port} skipped: {e}")

async def main():
    primary_port = int(os.getenv("PORT", 3000))
    other_ports = [p for p in [3000, 8000, 8080, 5000, 80] if p != primary_port]

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=primary_port,
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_level="info"
    )
    server = uvicorn.Server(config)

    print(f"🚀 Launching primary Uvicorn on 0.0.0.0:{primary_port}...")
    
    forwarders = [start_tcp_forwarder(p, primary_port) for p in other_ports]
    
    await asyncio.gather(
        server.serve(),
        *forwarders
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
