import asyncio
import base64
import json
import subprocess
import time
import requests
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9222
USER_DATA = r"C:\Users\LENOVO\AppData\Local\Temp\chrome_cdp_profile"

def start_chrome():
    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={USER_DATA}",
        "--headless=new",
        "--disable-gpu",
        "--window-size=1366,768",
        "http://localhost:8501"
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(2)
    return proc

async def capture_pages():
    res = requests.get(f"http://localhost:{PORT}/json")
    tabs = res.json()
    page_tab = [t for t in tabs if t["type"] == "page"][0]
    ws_url = page_tab["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        msg_id = 1
        
        async def send_cmd(method, params=None):
            nonlocal msg_id
            msg_id += 1
            payload = {"id": msg_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            while True:
                resp = await ws.recv()
                data = json.loads(resp)
                if data.get("id") == msg_id:
                    return data.get("result", {})

        await send_cmd("Page.enable")
        await send_cmd("Runtime.enable")
        await send_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 1366,
            "height": 768,
            "deviceScaleFactor": 1,
            "mobile": False
        })

        await asyncio.sleep(4)

        # 1. Page 1 Screenshot
        res = await send_cmd("Page.captureScreenshot", {"format": "png"})
        with open("page1_initial.png", "wb") as f:
            f.write(base64.b64decode(res["data"]))
        print("Captured page1_initial.png")

        # Click RUN INSPECTION button
        click_js = """
        (() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const runBtn = buttons.find(b => b.innerText.includes('RUN INSPECTION'));
            if (runBtn) {
                runBtn.click();
                return 'CLICKED';
            }
            return 'NOT_FOUND';
        })()
        """
        await send_cmd("Runtime.evaluate", {"expression": click_js})
        await asyncio.sleep(6)

        # 2. Page 2 Screenshot
        res = await send_cmd("Page.captureScreenshot", {"format": "png"})
        with open("page2_result.png", "wb") as f:
            f.write(base64.b64decode(res["data"]))
        print("Captured page2_result.png")

        async def navigate_to(page_text, out_filename):
            nav_js = f"""
            (() => {{
                const labels = Array.from(document.querySelectorAll('label'));
                const target = labels.find(l => l.innerText.includes('{page_text}'));
                if (target) {{
                    target.click();
                    return 'NAV_CLICKED';
                }}
                return 'LABEL_NOT_FOUND';
            }})()
            """
            await send_cmd("Runtime.evaluate", {"expression": nav_js})
            await asyncio.sleep(3)
            shot = await send_cmd("Page.captureScreenshot", {"format": "png"})
            with open(out_filename, "wb") as f:
                f.write(base64.b64decode(shot["data"]))
            print(f"Captured {out_filename}")

        # Navigate to Page 3, 4, 5, 6
        await navigate_to("Visual Inspection", "page3_visual.png")
        await navigate_to("Measurements", "page4_measurements.png")
        await navigate_to("Inspection Report", "page5_report.png")
        await navigate_to("Architecture", "page6_architecture.png")

if __name__ == "__main__":
    proc = start_chrome()
    try:
        asyncio.run(capture_pages())
    finally:
        proc.terminate()
