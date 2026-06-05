import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { useWeakness } from '../hooks/useWeakness'
import useAuthStore from '../store/authStore'
import SubjectBadge from '../components/shared/SubjectBadge'
import API from '../lib/api'

const SUBJECTS = ['physics', 'chemistry', 'mathematics']

// Animated typing hook
function useTypewriter(text, speed = 60) {
  const [display, setDisplay] = useState('')
  useEffect(() => {
    setDisplay('')
    let i = 0
    const iv = setInterval(() => {
      setDisplay(text.slice(0, i + 1))
      i++
      if (i >= text.length) clearInterval(iv)
    }, speed)
    return () => clearInterval(iv)
  }, [text, speed])
  return display
}

// Mini animated bar
function MasteryBar({ score, color = '#6366f1' }) {
  return (
    <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${score}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="h-full rounded-full"
        style={{ background: color }}
      />
    </div>
  )
}

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const { report, loading, fetchWeaknessReport } = useWeakness()
  const [summary, setSummary] = useState(null)

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const name = user?.user_metadata?.full_name?.split(' ')[0] || 'Student'
  const fullGreeting = `${greeting}, ${name}!`
  const typed = useTypewriter(fullGreeting, 50)

  useEffect(() => {
    fetchWeaknessReport()
    API.get('/analytics/summary').then(r => setSummary(r.data)).catch(() => {})
  }, [])

  const QUICK_ACTIONS = [
    {
      to: '/chat', icon: '💬', title: 'Ask a Doubt',
      desc: 'Step-by-step AI explanations',
      gradient: 'from-indigo-600/20 to-violet-600/10',
      border: 'border-indigo-500/25',
      glow: 'rgba(99,102,241,0.35)',
    },
    {
      to: '/quiz', icon: '📝', title: 'Mock Test',
      desc: 'Adaptive quizzes on weak topics',
      gradient: 'from-orange-600/20 to-amber-600/10',
      border: 'border-orange-500/25',
      glow: 'rgba(249,115,22,0.35)',
    },
    {
      to: '/analytics', icon: '📊', title: 'Analytics',
      desc: 'Mastery heatmaps & velocity',
      gradient: 'from-emerald-600/20 to-teal-600/10',
      border: 'border-emerald-500/25',
      glow: 'rgba(52,211,153,0.35)',
    },
    {
      to: '/vision', icon: '📷', title: 'Scan a Problem',
      desc: 'Upload a photo for OCR+AI',
      gradient: 'from-pink-600/20 to-rose-600/10',
      border: 'border-pink-500/25',
      glow: 'rgba(236,72,153,0.35)',
    },
  ]

  const weakTopics = SUBJECTS.flatMap(s => (report?.[s] || []).map(t => ({ ...t, subject: s }))).slice(0, 8)

  return (
    <div className="flex-1 overflow-y-auto relative" style={{ background: '#080b14' }}>
      {/* Ambient background blobs */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full blur-3xl opacity-20"
          style={{ background: 'radial-gradient(circle, #6366f1, transparent)' }} />
        <div className="absolute top-1/3 -left-16 w-64 h-64 rounded-full blur-3xl opacity-10"
          style={{ background: 'radial-gradient(circle, #8b5cf6, transparent)' }} />
        <div className="absolute bottom-0 right-1/3 w-72 h-72 rounded-full blur-3xl opacity-10"
          style={{ background: 'radial-gradient(circle, #0ea5e9, transparent)' }} />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto p-6 md:p-8 space-y-8">
        {/* Greeting */}
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight min-h-[1.2em]">
                {typed}
                <motion.span animate={{ opacity: [1, 0, 1] }} transition={{ repeat: Infinity, duration: 1 }}
                  className="inline-block w-0.5 h-8 bg-indigo-400 ml-1 align-middle" />
              </h1>
              <p className="text-slate-400 mt-1.5 text-sm">
                {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}
              </p>
            </div>
            <Link to="/chat"
              className="hidden sm:flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all duration-200 hover:scale-105"
              style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', boxShadow: '0 0 20px rgba(99,102,241,0.4)' }}>
              ✨ Start Studying
            </Link>
          </div>
        </motion.div>

        {/* Stats row */}
        {summary && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
            className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Topics Mastered', value: summary.topics_mastered, icon: '🏆', color: '#6366f1' },
              { label: 'Avg Mastery', value: `${summary.avg_mastery}%`, icon: '⚡', color: '#0ea5e9' },
              { label: 'Streak', value: `${summary.streak_days}d`, icon: '🔥', color: '#f97316' },
              { label: 'Sessions', value: summary.total_sessions, icon: '📚', color: '#34d399' },
            ].map((stat, i) => (
              <motion.div key={stat.label} initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + i * 0.07 }}
                className="rounded-2xl border border-white/8 p-4 text-center relative overflow-hidden"
                style={{ background: `linear-gradient(135deg, ${stat.color}15, ${stat.color}05)` }}>
                <div className="text-xl mb-1">{stat.icon}</div>
                <p className="text-2xl font-bold text-white">{stat.value}</p>
                <p className="text-[10px] text-slate-500 mt-0.5 uppercase tracking-wider font-semibold">{stat.label}</p>
                <div className="absolute bottom-0 left-0 right-0 h-0.5"
                  style={{ background: `linear-gradient(90deg, transparent, ${stat.color}, transparent)` }} />
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* Quick actions */}
        <div>
          <h2 className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {QUICK_ACTIONS.map(({ to, icon, title, desc, gradient, border, glow }, i) => (
              <motion.div key={title} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.08 }}>
                <Link to={to} id={`action-${title.toLowerCase().replace(/\s+/g, '-')}`}
                  className={`group relative block rounded-2xl border ${border} bg-gradient-to-br ${gradient} p-5 overflow-hidden transition-all duration-300 hover:scale-[1.03]`}
                  style={{ '--glow': glow }}
                >
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-2xl"
                    style={{ boxShadow: `inset 0 0 24px ${glow}` }} />
                  <div className="text-3xl mb-3 group-hover:scale-110 transition-transform duration-300">{icon}</div>
                  <p className="font-bold text-white text-sm">{title}</p>
                  <p className="text-slate-400 text-xs mt-1 leading-relaxed">{desc}</p>
                  <div className="mt-3 text-xs font-semibold text-indigo-400 group-hover:gap-2 flex items-center gap-1 transition-all">
                    Open <span className="group-hover:translate-x-1 transition-transform">→</span>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Weak topics + Analytics CTA */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Weak Topics */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            className="lg:col-span-2 rounded-2xl border border-white/8 p-6"
            style={{ background: 'rgba(255,255,255,0.02)' }}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-sm font-bold text-white">⚠️ Weak Topics</h2>
              <Link to="/quiz" className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition-colors">
                Generate Test →
              </Link>
            </div>
            {loading ? (
              <div className="flex justify-center py-8">
                <div className="w-6 h-6 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              </div>
            ) : weakTopics.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-4xl mb-3">🌟</p>
                <p className="text-slate-400 text-sm">No weak topics yet! Keep learning to see personalized insights.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {weakTopics.map((t, i) => {
                  const pct = Math.round(t.error_rate * 100)
                  const color = pct > 60 ? '#ef4444' : pct > 40 ? '#f97316' : '#fbbf24'
                  return (
                    <motion.div key={t.topic} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.45 + i * 0.05 }}
                      className="flex items-center gap-3">
                      <SubjectBadge subject={t.subject} className="text-[10px] py-0.5 px-2" />
                      <span className="text-sm text-slate-300 flex-1 truncate capitalize">
                        {t.topic.replace(/-/g, ' ')}
                      </span>
                      <MasteryBar score={pct} color={color} />
                      <span className="text-xs font-bold w-9 text-right" style={{ color }}>{pct}%</span>
                    </motion.div>
                  )
                })}
              </div>
            )}
          </motion.div>

          {/* Analytics CTA */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
            <Link to="/analytics"
              className="block h-full rounded-2xl border border-indigo-500/20 p-6 relative overflow-hidden group transition-all duration-300 hover:border-indigo-500/40 hover:scale-[1.02]"
              style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.06))' }}>
              <div className="absolute top-0 right-0 w-32 h-32 opacity-10 group-hover:opacity-20 transition-opacity">
                <svg viewBox="0 0 100 100" fill="none">
                  {[30, 55, 72, 85, 40, 65].map((v, i) => (
                    <rect key={i} x={i * 16 + 2} y={100 - v} width={12} height={v} rx="3"
                      fill="#6366f1" />
                  ))}
                </svg>
              </div>
              <div className="text-3xl mb-3">📈</div>
              <h3 className="font-bold text-white text-sm mb-1">Deep Analytics</h3>
              <p className="text-slate-400 text-xs leading-relaxed mb-4">
                Radar charts, velocity graphs, mastery heatmaps — all your progress in one view.
              </p>
              <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-400 group-hover:gap-2.5 transition-all">
                View Dashboard <span className="group-hover:translate-x-1 transition-transform">→</span>
              </div>
            </Link>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
