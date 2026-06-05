import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import API from '../lib/api'

// ─── Pure SVG Radar Chart (no external lib) ────────────────────────────────
function RadarChart({ data = {}, size = 220 }) {
  const subjects = ['physics', 'chemistry', 'mathematics']
  const labels    = ['Physics', 'Chemistry', 'Maths']
  const cx = size / 2, cy = size / 2
  const r  = size * 0.38
  const angles = subjects.map((_, i) => (Math.PI * 2 * i) / subjects.length - Math.PI / 2)

  const point = (angle, frac) => ({
    x: cx + r * frac * Math.cos(angle),
    y: cy + r * frac * Math.sin(angle),
  })

  const getScore = (subj) => {
    const items = data[subj] || []
    if (!items.length) return 0
    return Math.min(1, items.reduce((s, t) => s + t.score, 0) / (items.length * 100))
  }

  const scores  = subjects.map(getScore)
  const polygon = angles.map((a, i) => point(a, scores[i]))
  const polyStr = polygon.map(p => `${p.x},${p.y}`).join(' ')

  // Grid rings
  const rings = [0.25, 0.5, 0.75, 1]

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="overflow-visible">
      {/* Grid */}
      {rings.map(frac => (
        <polygon
          key={frac}
          points={angles.map(a => `${point(a, frac).x},${point(a, frac).y}`).join(' ')}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="1"
        />
      ))}
      {/* Axis lines */}
      {angles.map((a, i) => (
        <line key={i} x1={cx} y1={cy} x2={point(a, 1).x} y2={point(a, 1).y}
          stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
      ))}
      {/* Data polygon */}
      <polygon
        points={polyStr}
        fill="url(#radarFill)"
        stroke="#6366f1"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <defs>
        <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#6366f1" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0.1" />
        </radialGradient>
      </defs>
      {/* Dots */}
      {polygon.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="4" fill="#6366f1" stroke="#fff" strokeWidth="1.5" />
      ))}
      {/* Labels */}
      {angles.map((a, i) => {
        const lp = point(a, 1.22)
        return (
          <text key={i} x={lp.x} y={lp.y}
            textAnchor="middle" dominantBaseline="middle"
            fill="#94a3b8" fontSize="11" fontWeight="600" fontFamily="Inter, sans-serif"
          >
            {labels[i]}
          </text>
        )
      })}
      {/* Score labels on dots */}
      {polygon.map((p, i) => (
        <text key={`s${i}`} x={p.x} y={p.y - 9}
          textAnchor="middle" fill="#c7d2fe" fontSize="9" fontWeight="700"
        >
          {Math.round(scores[i] * 100)}%
        </text>
      ))}
    </svg>
  )
}

// ─── Pure SVG Sparkline (velocity) ─────────────────────────────────────────
function Sparkline({ data = [], width = 260, height = 60 }) {
  if (!data.length) return null
  const vals  = data.map(d => d.avg_delta)
  const max   = Math.max(...vals, 1)
  const min   = Math.min(...vals, 0)
  const range = max - min || 1
  const pad   = 8

  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1 || 1)) * (width - pad * 2)
    const y = height - pad - ((d.avg_delta - min) / range) * (height - pad * 2)
    return `${x},${y}`
  })

  const filled = [...pts, `${width - pad},${height}`, `${pad},${height}`].join(' ')

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="w-full">
      <defs>
        <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#34d399" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={filled} fill="url(#sparkFill)" />
      <polyline points={pts.join(' ')} fill="none" stroke="#34d399" strokeWidth="2.5"
        strokeLinejoin="round" strokeLinecap="round" />
      {data.map((d, i) => {
        const [x, y] = pts[i].split(',').map(Number)
        return (
          <circle key={i} cx={x} cy={y} r="3" fill="#34d399" stroke="rgba(0,0,0,0.5)" strokeWidth="1" />
        )
      })}
    </svg>
  )
}

// ─── Heatmap Cell ────────────────────────────────────────────────────────────
function scoreColor(score) {
  if (score >= 80) return { bg: 'rgba(52,211,153,0.2)', border: 'rgba(52,211,153,0.5)', text: '#34d399' }
  if (score >= 60) return { bg: 'rgba(251,191,36,0.15)', border: 'rgba(251,191,36,0.4)', text: '#fbbf24' }
  if (score >= 40) return { bg: 'rgba(249,115,22,0.15)', border: 'rgba(249,115,22,0.4)', text: '#f97316' }
  return { bg: 'rgba(239,68,68,0.15)', border: 'rgba(239,68,68,0.4)', text: '#ef4444' }
}

// ─── Stat Card ───────────────────────────────────────────────────────────────
function StatCard({ icon, label, value, sub, color = '#6366f1', delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="relative overflow-hidden rounded-2xl border border-white/10 p-5"
      style={{ background: `linear-gradient(135deg, ${color}18, ${color}06)` }}
    >
      <div className="absolute top-3 right-3 text-2xl opacity-70">{icon}</div>
      <p className="text-xs text-slate-500 font-semibold uppercase tracking-widest mb-1">{label}</p>
      <p className="text-3xl font-bold text-white mb-0.5">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-b-2xl"
        style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }} />
    </motion.div>
  )
}

// ─── Main Page ──────────────────────────────────────────────────────────────
export default function AnalyticsPage() {
  const [summary, setSummary] = useState(null)
  const [mastery, setMastery] = useState({})
  const [sessions, setSessions] = useState([])
  const [velocity, setVelocity] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeSubject, setActiveSubject] = useState('all')

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [s, m, sess, v] = await Promise.all([
        API.get('/analytics/summary').then(r => r.data),
        API.get('/analytics/mastery').then(r => r.data),
        API.get('/analytics/sessions').then(r => r.data),
        API.get('/analytics/velocity').then(r => r.data),
      ])
      setSummary(s)
      setMastery(m)
      setSessions(sess)
      setVelocity(v)
    } catch (e) {
      console.error('Analytics load failed', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadAll() }, [loadAll])

  const allTopics = Object.entries(mastery).flatMap(([subj, topics]) =>
    topics.map(t => ({ ...t, subject: subj }))
  )
  const filtered = activeSubject === 'all'
    ? allTopics
    : allTopics.filter(t => t.subject === activeSubject)

  const subjects = ['all', ...Object.keys(mastery)]

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-2 border-indigo-500/30 border-t-indigo-500 animate-spin" />
          <p className="text-slate-400 text-sm font-medium">Loading your analytics…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto bg-[#080b14]" id="analytics-page">
      {/* Aurora BG */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 -right-24 w-72 h-72 bg-violet-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-1/3 w-80 h-80 bg-emerald-600/08 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto p-6 space-y-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white tracking-tight">Analytics</h1>
              <p className="text-slate-400 mt-1 text-sm">Your personalised learning intelligence dashboard</p>
            </div>
            <Link to="/quiz"
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-sm font-semibold hover:bg-indigo-600/30 transition-all">
              📝 Take a Test
            </Link>
          </div>
        </motion.div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon="🏆" label="Topics Mastered" value={summary?.topics_mastered ?? 0}
            sub={`of ${summary?.total_topics ?? 0} total`} color="#6366f1" delay={0} />
          <StatCard icon="🔥" label="Current Streak" value={`${summary?.streak_days ?? 0}d`}
            sub="consecutive days" color="#f97316" delay={0.08} />
          <StatCard icon="📚" label="Total Sessions" value={summary?.total_sessions ?? 0}
            sub="learning sessions" color="#0ea5e9" delay={0.16} />
          <StatCard icon="⚡" label="Avg Mastery" value={`${summary?.avg_mastery ?? 0}%`}
            sub="across all topics" color="#34d399" delay={0.24} />
        </div>

        {/* Radar + Velocity Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Radar */}
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
            className="rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-sm p-6">
            <h2 className="text-base font-bold text-white mb-1">Subject Strength Radar</h2>
            <p className="text-xs text-slate-500 mb-6">Average mastery per subject</p>
            <div className="flex justify-center">
              <RadarChart data={mastery} size={220} />
            </div>
          </motion.div>

          {/* Velocity Sparkline */}
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.35 }}
            className="rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-sm p-6">
            <h2 className="text-base font-bold text-white mb-1">Learning Velocity</h2>
            <p className="text-xs text-slate-500 mb-4">Avg mastery gain per day — last 7 days</p>
            {velocity.length ? (
              <>
                <Sparkline data={velocity} width={320} height={80} />
                <div className="flex justify-between mt-2 px-1">
                  {velocity.map(d => (
                    <div key={d.day} className="flex flex-col items-center">
                      <span className="text-[9px] text-slate-500">
                        {new Date(d.day).toLocaleDateString('en', { weekday: 'short' })}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-20 text-slate-600 text-sm">No session data yet</div>
            )}

            {/* Quick metrics */}
            <div className="mt-5 grid grid-cols-3 gap-3">
              {[
                { label: 'Best Day', value: velocity.length ? `+${Math.max(...velocity.map(d => d.avg_delta)).toFixed(1)}` : '—' },
                { label: 'Avg Gain', value: velocity.length ? `+${(velocity.reduce((s, d) => s + d.avg_delta, 0) / velocity.length).toFixed(1)}` : '—' },
                { label: 'Sessions', value: velocity.reduce((s, d) => s + d.sessions, 0) },
              ].map(m => (
                <div key={m.label} className="rounded-xl bg-white/5 p-3 text-center">
                  <p className="text-lg font-bold text-emerald-400">{m.value}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{m.label}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Topic Mastery Heatmap */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
          className="rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-sm p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-bold text-white">Topic Mastery Heatmap</h2>
              <p className="text-xs text-slate-500 mt-0.5">Coloured by mastery score — darker = stronger</p>
            </div>
            {/* Subject filter pills */}
            <div className="flex gap-2 flex-wrap">
              {subjects.map(s => (
                <button key={s} onClick={() => setActiveSubject(s)}
                  className={`px-3 py-1 rounded-full text-xs font-semibold capitalize transition-all ${
                    activeSubject === s
                      ? 'bg-indigo-600 text-white border border-indigo-500'
                      : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10'
                  }`}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          {filtered.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-slate-500 text-sm">No mastery data yet. Start answering questions!</p>
              <Link to="/chat" className="inline-block mt-4 text-indigo-400 text-sm hover:underline">
                Go to Chat →
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {filtered.map((t, i) => {
                const c = scoreColor(t.score)
                return (
                  <motion.div key={`${t.subject}-${t.topic}`}
                    initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="rounded-xl p-3 text-center transition-transform hover:scale-105 cursor-default"
                    style={{ background: c.bg, border: `1px solid ${c.border}` }}
                    title={`${t.topic}: ${t.score}%`}
                  >
                    <p className="text-xs font-semibold capitalize truncate" style={{ color: c.text }}>
                      {t.topic.replace(/-/g, ' ')}
                    </p>
                    <p className="text-xl font-bold mt-1" style={{ color: c.text }}>{t.score}%</p>
                    <div className="mt-1.5 h-1 rounded-full bg-black/20 overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${t.score}%`, background: c.text }} />
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}

          {/* Legend */}
          <div className="flex gap-4 mt-5 flex-wrap">
            {[
              { label: '< 40%  Weak', color: '#ef4444' },
              { label: '40–60%  Fair', color: '#f97316' },
              { label: '60–80%  Good', color: '#fbbf24' },
              { label: '≥ 80%  Mastered', color: '#34d399' },
            ].map(l => (
              <div key={l.label} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm" style={{ background: l.color }} />
                <span className="text-xs text-slate-500">{l.label}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Session History */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
          className="rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-sm p-6">
          <h2 className="text-base font-bold text-white mb-5">Recent Sessions</h2>
          {sessions.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-8">No sessions recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-500 text-xs uppercase tracking-wider border-b border-white/5">
                    <th className="pb-3 text-left font-semibold">Topic</th>
                    <th className="pb-3 text-left font-semibold">Subject</th>
                    <th className="pb-3 text-right font-semibold">Duration</th>
                    <th className="pb-3 text-right font-semibold">Before</th>
                    <th className="pb-3 text-right font-semibold">After</th>
                    <th className="pb-3 text-right font-semibold">Δ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {sessions.map((s, i) => {
                    const delta = s.delta
                    const deltaColor = delta == null ? 'text-slate-500'
                      : delta > 0 ? 'text-emerald-400' : delta < 0 ? 'text-red-400' : 'text-slate-400'
                    return (
                      <motion.tr key={s.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.04 }} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3 text-slate-200 capitalize font-medium">
                          {(s.topic || '—').replace(/-/g, ' ')}
                        </td>
                        <td className="py-3 text-slate-400 capitalize text-xs">{s.subject || '—'}</td>
                        <td className="py-3 text-right text-slate-400">{s.duration_min != null ? `${s.duration_min}m` : '—'}</td>
                        <td className="py-3 text-right text-slate-400">{s.score_before ?? '—'}</td>
                        <td className="py-3 text-right text-slate-400">{s.score_after ?? '—'}</td>
                        <td className={`py-3 text-right font-bold ${deltaColor}`}>
                          {delta != null ? (delta > 0 ? `+${delta}` : delta) : '—'}
                        </td>
                      </motion.tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
