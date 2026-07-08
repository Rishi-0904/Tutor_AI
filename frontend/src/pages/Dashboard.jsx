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
        {/* Redesigned Greeting Banner + Today's Goal */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="rounded-3xl border border-indigo-500/15 p-6 md:p-8 relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.03))',
            boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
          }}
        >
          {/* Decorative background circle */}
          <div className="absolute -top-12 -right-12 w-48 h-48 bg-indigo-500/5 rounded-full blur-2xl pointer-events-none" />

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
            <div>
              <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight min-h-[1.2em]">
                {typed}
                <motion.span
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ repeat: Infinity, duration: 1 }}
                  className="inline-block w-0.5 h-8 bg-indigo-400 ml-1 align-middle"
                />
              </h1>
              <p className="text-slate-400 mt-2 text-sm leading-relaxed max-w-xl">
                Ready to continue your rank-boosting workflow? Practice adaptive question sets or search notes to lock in concepts.
              </p>
              
              <div className="flex items-center gap-3 mt-4">
                <Link
                  to="/chat"
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all duration-200 hover:scale-105"
                  style={{
                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                    boxShadow: '0 0 20px rgba(99,102,241,0.4)',
                  }}
                >
                  Continue Learning →
                </Link>
              </div>
            </div>

            {/* Today's Goal Progress Box */}
            <div className="w-full lg:max-w-md rounded-2xl bg-white/[0.02] border border-white/[0.04] p-5">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center justify-between">
                <span>🎯 Today's Goal</span>
                <span className="text-[10px] text-indigo-400 normal-case font-semibold">Daily Target</span>
              </h3>
              
              <div className="space-y-4">
                {/* Solved Topics progress */}
                <div>
                  <div className="flex justify-between text-xs text-slate-300 mb-1.5 font-medium">
                    <span>Topics Studied</span>
                    <span className="text-white font-bold">{summary?.topics_mastered || 3} / 5</span>
                  </div>
                  <MasteryBar score={((summary?.topics_mastered || 3) / 5) * 100} color="#6366f1" />
                </div>

                {/* Solved Questions progress */}
                <div>
                  <div className="flex justify-between text-xs text-slate-300 mb-1.5 font-medium">
                    <span>Questions Solved</span>
                    <span className="text-white font-bold">{summary?.total_sessions || 15} / 25</span>
                  </div>
                  <MasteryBar score={((summary?.total_sessions || 15) / 25) * 100} color="#8b5cf6" />
                </div>
              </div>

              {/* Sub-stats layout */}
              <div className="grid grid-cols-2 gap-4 mt-5 pt-4 border-t border-white/[0.05]">
                <div>
                  <div className="text-xs text-slate-500 font-semibold mb-0.5">CURRENT STREAK</div>
                  <div className="text-lg font-extrabold text-white flex items-center gap-1">
                    <span>🔥</span> {summary?.streak_days || 4} Days
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 font-semibold mb-0.5">MASTERY SCORE</div>
                  <div className="text-lg font-extrabold text-white flex items-center gap-1">
                    <span>⚡</span> {summary?.avg_mastery || 76}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

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
