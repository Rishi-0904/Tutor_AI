/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          900: '#1e1b4b',
        },
        surface: {
          900: '#080b14',
          800: '#0d1117',
          700: '#111827',
          600: '#1a2235',
          500: '#1e2d42',
        },
        accent: {
          violet: '#8b5cf6',
          pink:   '#ec4899',
          cyan:   '#06b6d4',
          emerald:'#10b981',
          orange: '#f97316',
          amber:  '#f59e0b',
        },
      },
      backgroundImage: {
        'brand-gradient':  'linear-gradient(135deg, #6366f1, #8b5cf6)',
        'aurora':          'radial-gradient(ellipse 700px 500px at 0% 0%, rgba(99,102,241,0.10) 0%, transparent 70%), radial-gradient(ellipse 600px 600px at 100% 100%, rgba(139,92,246,0.08) 0%, transparent 70%), #080b14',
      },
      boxShadow: {
        'glow-indigo': '0 0 20px rgba(99,102,241,0.4)',
        'glow-violet': '0 0 20px rgba(139,92,246,0.4)',
        'glow-emerald':'0 0 20px rgba(52,211,153,0.4)',
        'glow-card':   '0 8px 32px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.06)',
      },
      animation: {
        'fade-in':      'fadeIn 0.25s ease-out',
        'slide-up':     'slideUp 0.35s ease-out',
        'float':        'float 4s ease-in-out infinite',
        'pulse-glow':   'pulseGlow 2.5s ease-in-out infinite',
        'shimmer':      'shimmer 1.6s infinite',
        'gradient':     'gradientShift 4s ease infinite',
        'spin-slow':    'spin 8s linear infinite',
      },
      keyframes: {
        fadeIn:        { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp:       { from: { opacity: 0, transform: 'translateY(14px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        float:         { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-8px)' } },
        pulseGlow:     { '0%,100%': { boxShadow: '0 0 12px rgba(99,102,241,0.3)' }, '50%': { boxShadow: '0 0 28px rgba(99,102,241,0.7)' } },
        shimmer:       { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        gradientShift: { '0%,100%': { backgroundPosition: '0% 50%' }, '50%': { backgroundPosition: '100% 50%' } },
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}
