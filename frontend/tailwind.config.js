/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        esi: {
          1: {
            bg: '#DC2626',
            text: '#FFFFFF',
            light: '#FEE2E2',
            border: '#B91C1C'
          },
          2: {
            bg: '#EA580C',
            text: '#FFFFFF',
            light: '#FFEDD5',
            border: '#C2410C'
          },
          3: {
            bg: '#D97706',
            text: '#FFFFFF',
            light: '#FEF3C7',
            border: '#B45309'
          },
          4: {
            bg: '#16A34A',
            text: '#FFFFFF',
            light: '#DCFCE7',
            border: '#15803D'
          },
          5: {
            bg: '#2563EB',
            text: '#FFFFFF',
            light: '#DBEAFE',
            border: '#1D4ED8'
          }
        },
        clinical: {
          dark: '#0F172A',
          card: '#1E293B',
          border: '#334155',
          text: '#F8FAFC',
          muted: '#94A3B8'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.2s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(2px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}
