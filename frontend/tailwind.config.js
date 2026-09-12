/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0a0e14',
          card: '#111823',
          border: '#1e2a3a',
          hover: '#182232',
        }
      }
    },
  },
  plugins: [],
}
