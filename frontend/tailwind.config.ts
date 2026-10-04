import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111111",
        muted: "#5F6368",
        border: "#E5E7EB",
        surface: "#F8FAF9",
        "surface-muted": "#F3F4F6",
        gov: {
          50: "#F0FDF4",
          100: "#DCFCE7",
          600: "#16A34A",
          700: "#15803D",
          900: "#14532D"
        }
      },
      fontFamily: {
        sans: ["Poppins", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"]
      },
      boxShadow: {
        soft: "0 1px 2px rgba(17, 17, 17, 0.04)"
      }
    }
  },
  plugins: []
};

export default config;
