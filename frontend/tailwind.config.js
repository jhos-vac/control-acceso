/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Color institucional
        brand: {
          DEFAULT: "#009EAD",
          50: "#E6F7F8",
          100: "#CCEFF1",
          200: "#99DFE3",
          300: "#66CFD5",
          400: "#33BFC7",
          500: "#009EAD",
          600: "#007E8A",
          700: "#005F68",
          800: "#003F45",
          900: "#002023",
        },
      },
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
