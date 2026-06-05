import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../hooks/useAuth'
import useAuthStore from '../../store/authStore'

const NAV_ITEMS = [
  { to: '/dashboard', icon: '⚡', label: 'Dashboard' },
  { to: '/chat',      icon: '💬', label: 'Ask AI' },
  { to: '/quiz',      icon: '📝', label: 'Mock Test' },
  { to: '/analytics', icon: '📊', label: 'Analytics' },
  { to: '/vision',    icon: '📸', label: 'Vision OCR' },
  { to: '/profile',   icon: '👤', label: 'Profile' },
]

const SUBJECT_COLORS = {
  physics: 'from-sky-500 to-blue-600',
  chemistry: 'from-emerald-500 to-teal-600',
  mathematics: 'from-violet-500 to-purple-600',
  general: 'from-slate-500 to-slate-600',
}

export default function Navbar() {
  const location = useLocation()
  const { signOut } = useAuth()
  const user = useAuthStore((s) => s.user)
  const [collapsed, setCollapsed] = useState(false)

  const name = user?.user_metadata?.full_name || 'Student'
  const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 220 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="relative flex-shrink-0 h-screen flex flex-col overflow-hidden z-50"
      style={{
        background: 'linear-gradient(180deg, #0d1117 0%, #0a0f1a 100%)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Glow accent line */}
      <div className="absolute top-0 left-0 right-0 h-0.5"
        style={{ background: 'linear-gradient(90deg, transparent, #6366f1, transparent)' }} />

      {/* Logo row */}
      <div className="flex items-center gap-3 px-4 py-5 flex-shrink-0">
        <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
          <span className="text-white text-sm font-bold">T</span>
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }} transition={{ duration: 0.2 }}
              className="font-extrabold text-white text-lg tracking-tight whitespace-nowrap"
              style={{ fontFamily: "'Inter', sans-serif" }}
            >
              TutorAI
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-2 space-y-1 overflow-hidden">
        {NAV_ITEMS.map(({ to, icon, label }) => {
          const active = location.pathname === to || location.pathname.startsWith(to + '/')
          return (
            <Link key={to} to={to} title={collapsed ? label : undefined}
              className={`relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${
                active
                  ? 'text-white'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {active && (
                <motion.div layoutId="sidebar-active"
                  className="absolute inset-0 rounded-xl"
                  style={{
                    background: 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.1))',
                    border: '1px solid rgba(99,102,241,0.3)',
                  }}
                  transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                />
              )}
              <span className="relative text-lg flex-shrink-0 group-hover:scale-110 transition-transform duration-200">{icon}</span>
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -6 }} transition={{ duration: 0.15 }}
                    className="relative text-sm font-medium whitespace-nowrap"
                  >
                    {label}
                  </motion.span>
                )}
              </AnimatePresence>
              {active && !collapsed && (
                <motion.div
                  layoutId="sidebar-dot"
                  className="relative ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ background: '#6366f1' }}
                />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Divider */}
      <div className="mx-3 my-2 h-px bg-white/5" />

      {/* User footer */}
      <div className="px-2 pb-4 space-y-2 flex-shrink-0">
        <div className={`flex items-center gap-3 px-2 py-2 rounded-xl transition-all ${collapsed ? 'justify-center' : ''}`}>
          {/* Avatar */}
          <div className="w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center text-xs font-bold text-white"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
            {initials}
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex-1 overflow-hidden min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate">{name}</p>
                <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <button id="signout-btn" onClick={signOut}
          title={collapsed ? 'Sign out' : undefined}
          className={`flex items-center gap-2 w-full px-3 py-2 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all text-xs font-medium ${collapsed ? 'justify-center' : ''}`}
        >
          <span className="text-base">🚪</span>
          <AnimatePresence>
            {!collapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                Sign out
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Collapse toggle */}
        <button onClick={() => setCollapsed(p => !p)}
          className={`flex items-center gap-2 w-full px-3 py-2 rounded-xl text-slate-600 hover:text-slate-300 hover:bg-white/5 transition-all text-xs ${collapsed ? 'justify-center' : ''}`}
        >
          <motion.span animate={{ rotate: collapsed ? 180 : 0 }} transition={{ duration: 0.3 }}
            className="text-base">
            ◀
          </motion.span>
          <AnimatePresence>
            {!collapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                Collapse
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  )
}
