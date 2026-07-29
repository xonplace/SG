module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.html",
    "./apps/**/*.py"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "#1f78b9",
          black: "#050505"
        }
      },
      fontFamily: {
        sans: ["Inter", "Arial", "Helvetica", "sans-serif"]
      }
    }
  },
  plugins: []
};
