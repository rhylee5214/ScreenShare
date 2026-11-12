# ScreenShare — consent-based prototype

This is a small, consent-first remote screen-viewing prototype based on your uploaded project.

## What it does
- The computer owner runs `client.py` (later packaged as an EXE).
- The app displays a stable pairing ID.
- An admin enters that ID and sends a request from the hosted dashboard.
- The owner receives a Windows Allow/Disallow dialog.
- If allowed, the owner’s browser opens a sharing page.
- The owner must click **Choose screen and start sharing** and select a screen/window in the browser's own picker.
- The admin opens the live viewer only after approval.
- The owner can stop sharing at any time.

It does not provide keyboard/mouse control, hidden capture, unattended access, or a way around the browser/OS screen-sharing picker.

## Important prototype limitations
- The server stores requests and WebSocket peer state in process memory. Deploy exactly one server instance; restarting/redeploying clears pending sessions.
- Render's free service may sleep and is not suitable for dependable always-on real-time sessions.
- STUN alone does not guarantee connectivity across every network. For reliable worldwide connectivity, configure a reputable TURN provider using `TURN_URL`, `TURN_USERNAME`, and `TURN_CREDENTIAL` environment variables. Do not expose TURN credentials in public source code.
- This is a prototype, not a hardened production remote-support product. Before using it with other people, add rate limits, audit logs, stronger device pairing, request expiry, and security review.

## 1. Run locally first
Use Python 3.11 or 3.12.

```powershell
cd ScreenShare_Render
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:ADMIN_KEY = "replace-this-with-a-long-random-secret"
uvicorn server:app --host 127.0.0.1 --port 8000
```

On the computer being viewed, open a second PowerShell window:

```powershell
cd ScreenShare_Render
.venv\Scripts\activate
```

Edit `client.py` and temporarily set:
```python
SERVER_URL = "http://127.0.0.1:8000"
```
Then run:
```powershell
python client.py
```

Open `http://127.0.0.1:8000` on the admin computer. Enter the admin key and the pairing ID shown in the client app. For a local test, both can run on the same PC; for two PCs on the same LAN, use the host PC's LAN address and allow the port through the firewall.

## 2. Deploy to Render
1. Create a GitHub repository and upload the contents of this folder (do not upload `.venv`).
2. In Render, choose **New + → Blueprint** and select the repository containing `render.yaml`.
3. Render creates the web service and generates `ADMIN_KEY`.
4. In the Render service's Environment page, copy the generated `ADMIN_KEY` and keep it private.
5. Wait for deployment. Your public URL will look like `https://your-service.onrender.com`.
6. Edit `client.py`: set `SERVER_URL` to that exact HTTPS URL.
7. Rebuild the EXE after changing the URL.

Render free services can sleep; the first request after idle may take time. For an always-on service, use a paid plan.

## 3. Configure TURN for cross-network reliability
STUN is included for initial testing. For wider network compatibility, obtain TURN credentials from a reputable TURN provider and set these Render environment variables:
- `TURN_URL` (one or more URLs, comma-separated, e.g. `turn:host:3478?transport=udp,turns:host:5349?transport=tcp`)
- `TURN_USERNAME`
- `TURN_CREDENTIAL`

Do not put long-lived TURN secrets in GitHub. Use provider-issued time-limited credentials if available.

## 4. Build the Windows EXE
On Windows, with the virtual environment activated:

```powershell
pyinstaller --onefile --noconsole --name ScreenShareClient client.py
```

The EXE is created in `dist\ScreenShareClient.exe`. Give it only to people who understand what it does. Windows SmartScreen may show a warning for unsigned personal builds.

## 5. Security checklist
- Use HTTPS only for public deployment.
- Keep `ADMIN_KEY` secret; never commit it.
- Share the device pairing ID privately; treat it like a credential.
- Keep the owner’s consent dialog and browser screen picker.
- Test denial, stop-sharing, browser-close, and network-drop behavior.
- Do not use this for covert monitoring or to access a computer without its owner's informed permission.
