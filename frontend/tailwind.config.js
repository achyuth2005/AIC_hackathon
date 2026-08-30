/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      boxShadow: {
        card: 'inset 0 0 0 1px rgba(255, 255, 255, 0.8), 0 8px 32px 0 rgba(31, 38, 135, 0.04)',
        'card-lg': 'inset 0 0 0 1px rgba(255, 255, 255, 0.9), 0 12px 36px 0 rgba(31, 38, 135, 0.06)',
        glass: 'inset 0 0 0 1px rgba(255, 255, 255, 0.8), 0 8px 32px 0 rgba(31, 38, 135, 0.04)',
        'glass-hover': 'inset 0 0 0 1px rgba(255, 255, 255, 0.95), 0 12px 40px 0 rgba(31, 38, 135, 0.08)',
        'glass-inset': 'inset 0 0 0 1px rgba(255, 255, 255, 0.8)',
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'beacon': 'beacon 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(2px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        beacon: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(225,29,72,0.25)' },
          '50%': { boxShadow: '0 0 0 6px rgba(225,29,72,0)' },
        },
      }
    },
  },
  plugins: [],
}
