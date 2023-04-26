/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./build/*.html'],
  theme: {
    extend: {
      colors: {
        'pea-blue': '#10171d',
        'weird-white': '#f6f7f6',
      },
      width: {
        '128': '32rem',
        '100': '26rem',
      },
    },
  },
plugins: [require("daisyui")],
}
