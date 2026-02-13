import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: "#0D0F12",
        ink: "#F3F4F6",
        "ink-light": "#D7DCE5",
        "ink-muted": "#B6BDC8",
        rule: "#2A303B",
        "rule-dark": "#7E8796",
        accent: "#FF4D4D",
        "accent-dark": "#E43E3E",
        "accent-light": "#2A1517",
        warm: "#151922",
        panel: "#11151C",
        "panel-soft": "#1A202B",
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "Georgia", "serif"],
        body: ['"Cormorant Garamond"', "Georgia", "serif"],
        sans: ['"Manrope"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      animation: {
        "fade-in": "fadeIn 0.42s ease-out forwards",
        "fade-up": "fadeUp 0.45s ease-out forwards",
        "slide-in": "slideIn 0.35s ease-out forwards",
        "rule-draw": "ruleDraw 0.6s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        ruleDraw: {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
