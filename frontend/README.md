# EchoGuard Frontend

Run this dashboard through Vite. Opening `index.html` directly from File Explorer will not work because the app uses JavaScript modules and Vite transforms.

```powershell
cd "c:\Users\aadir\Desktop\eaco gaurd\echoguard\frontend"
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:5173
```

If the page looks stale or blank, stop old Node processes and restart:

```powershell
Get-Process node -ErrorAction SilentlyContinue | Stop-Process
npm.cmd run dev
```
