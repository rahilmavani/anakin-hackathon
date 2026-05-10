import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#f3f5f8",
        ink: "#0d1b2a",
        panel: "#ffffff",
        accent: "#1f6feb",
        muted: "#667085",
      },
      boxShadow: {
        panel: "0 12px 30px rgba(12, 24, 44, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
