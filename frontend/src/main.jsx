import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

const root = document.getElementById("root");

try {
  createRoot(root).render(<App />);
} catch (error) {
  root.innerHTML = `
    <main style="min-height:100vh;display:grid;place-items:center;background:#111;color:#f5f5f3;font-family:Inter,Segoe UI,Arial,sans-serif;padding:24px">
      <section style="max-width:640px;border:1px solid #313131;background:#181818;border-radius:8px;padding:24px">
        <h1 style="margin:0 0 12px;font-size:24px">EchoGuard could not load</h1>
        <p style="margin:0;color:#a3a3a0">Restart the frontend with <code>npm.cmd run dev</code> and refresh the browser.</p>
        <pre style="white-space:pre-wrap;color:#ff5a5f;margin-top:16px">${String(error?.message ?? error)}</pre>
      </section>
    </main>
  `;
}
