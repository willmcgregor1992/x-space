/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07090d",
        panel: "#0c1018",
        line: "rgba(232,236,245,0.10)",
        mist: "#8b93a7",
        paper: "#e8eaef",
        route: "#6d8aa8",
        ember: "#d4783a",
        live: "#c9a36a",
        alert: "#c4453c",
      },
      fontFamily: {
        sans: ["Barlow", "Segoe UI", "Helvetica Neue", "sans-serif"],
        cond: ["Barlow Condensed", "Barlow", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        label: "0.22em",
      },
      boxShadow: {
        panel: "inset 0 0 0 1px rgba(232,236,245,0.08)",
      },
    },
  },
  plugins: [],
};
