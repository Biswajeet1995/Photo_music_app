import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from aiohttp import ClientSession, WSMsgType, web

from verify import TARGET_IMAGE, verify_image

STREAMLIT_HOST = "127.0.0.1"
STREAMLIT_PORT = int(os.environ.get("STREAMLIT_PORT", "8501"))
STREAMLIT_BASE_URL = f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}"
APP_PORT = int(os.environ.get("PORT", "5000"))
TEMP_API_IMAGE = Path("temp_api_upload.jpg")


def start_streamlit_process():
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        str(STREAMLIT_PORT),
        "--server.headless",
        "true",
    ]
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def terminate_process(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def wait_for_streamlit(timeout: int = 30):
    import urllib.error
    import urllib.request

    end_time = time.time() + timeout
    url = f"{STREAMLIT_BASE_URL}/"

    while time.time() < end_time:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status in (200, 302, 303, 404):
                    return
        except (urllib.error.HTTPError, urllib.error.URLError, ConnectionError):
            time.sleep(0.5)

    raise RuntimeError("Streamlit did not start in time")


async def handle_verify_image(request: web.Request) -> web.Response:
    data = await request.post()
    if "image" not in data:
        return web.json_response({"error": "Missing form field 'image'"}, status=400)

    image_field = data["image"]
    if not image_field.filename:
        return web.json_response({"error": "Image file is empty"}, status=400)

    TEMP_API_IMAGE.write_bytes(image_field.file.read())
    matched, score = verify_image(str(TEMP_API_IMAGE), TARGET_IMAGE)
    TEMP_API_IMAGE.unlink(missing_ok=True)

    return web.json_response({"matched": matched, "score": int(score)})


async def proxy_websocket(request: web.Request) -> web.WebSocketResponse:
    ws_server = web.WebSocketResponse()
    await ws_server.prepare(request)

    ws_url = f"ws://{STREAMLIT_HOST}:{STREAMLIT_PORT}{request.rel_url}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in (
            "host",
            "connection",
            "upgrade",
            "sec-websocket-key",
            "sec-websocket-version",
            "sec-websocket-extensions",
            "sec-websocket-protocol",
        )
    }

    async with ClientSession() as client_session:
        async with client_session.ws_connect(ws_url, headers=headers) as ws_client:

            async def forward(source, target):
                async for msg in source:
                    if msg.type == WSMsgType.TEXT:
                        await target.send_str(msg.data)
                    elif msg.type == WSMsgType.BINARY:
                        await target.send_bytes(msg.data)
                    elif msg.type == WSMsgType.CLOSE:
                        await target.close()
                        break

            await asyncio.gather(
                forward(ws_server, ws_client),
                forward(ws_client, ws_server),
            )

    return ws_server


async def proxy_handler(request: web.Request) -> web.Response:
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await proxy_websocket(request)

    destination = f"{STREAMLIT_BASE_URL}{request.rel_url}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in (
            "host",
            "connection",
            "upgrade",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "encoding",
        )
    }

    body = await request.read()
    async with ClientSession() as client_session:
        async with client_session.request(
            request.method,
            destination,
            headers=headers,
            data=body,
            allow_redirects=False,
        ) as resp:
            response_headers = {
                name: value
                for name, value in resp.headers.items()
                if name.lower() not in (
                    "connection",
                    "keep-alive",
                    "proxy-authenticate",
                    "proxy-authorization",
                    "te",
                    "trailers",
                    "transfer-encoding",
                )
            }
            content = await resp.read()
            return web.Response(
                body=content,
                status=resp.status,
                headers=response_headers,
            )


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/api/verify-image", handle_verify_image)
    app.router.add_route("*", "/{path:.*}", proxy_handler)
    return app


def main() -> None:
    streamlit_process = start_streamlit_process()

    def handle_exit(signum, frame):
        terminate_process(streamlit_process)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    try:
        wait_for_streamlit()
    except Exception:
        terminate_process(streamlit_process)
        raise

    app = create_app()
    web.run_app(app, host="0.0.0.0", port=APP_PORT)
    terminate_process(streamlit_process)


if __name__ == "__main__":
    main()
