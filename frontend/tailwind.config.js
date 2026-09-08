/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#020617",
        panel: "#0f172a",
        panelSoft: "#111827",
       
      },
      boxShadow: {
        card: "0 24px 80px rgba(2, 6, 23, 0.38)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Arial"],
      },
    },
  },
  plugins: [],
};
