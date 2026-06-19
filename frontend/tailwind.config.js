/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B0C0E",
        panel: "#15171A",
        paper: "#F3F0E8",
        amber: {
          DEFAULT: "#D9A656",
          dim: "#8C6E3C",
          soft: "#3A301E",
        },
        muted: "#8A8F98",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
