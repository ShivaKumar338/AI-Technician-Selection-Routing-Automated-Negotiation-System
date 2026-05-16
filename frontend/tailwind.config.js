/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0F172A",
        card: "#1E293B",
        primary: "#10B981",
        secondary: "#6366F1",
        foreground: "#F1F5F9",
        muted: "#94A3B8",
        border: "#334155",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "0.75rem",
      },
      boxShadow: {
        card: "0 4px 24px rgba(0, 0, 0, 0.25)",
      },
    },
  },
  plugins: [],
};
