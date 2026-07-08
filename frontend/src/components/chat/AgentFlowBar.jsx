import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

const STATUS_ICONS = {
  pending: '○',
  running: '◌',
  done: '●',
}

const STATUS_COLORS = {
  pending: 'text-slate-600',
  running: 'text-amber-400 animate-pulse',
  done: 'text-emerald-400',
}

export default function AgentFlowBar({ agentSteps = [], isStreaming }) {
  const [expanded, setExpanded] = useState(true)

  if (!agentSteps || agentSteps.length === 0) return null

  // Auto-collapse when streaming is done
  const allDone = agentSteps.every((s) => s.status === 'done')

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-2"
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-[11px] font-medium 
                   bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] 
                   hover:border-white/10 backdrop-blur-md transition-all duration-200
                   text-slate-400 hover:text-slate-300 cursor-pointer select-none w-fit"
      >
        <span className="text-indigo-400">⚡</span>
        <span>Agent Pipeline</span>
        <span className={`text-[10px] ${allDone ? 'text-emerald-400' : 'text-amber-400'}`}>
          {allDone ? '✓ Complete' : '⏳ Running...'}
        </span>
        <span className="text-slate-600 ml-1">{expanded ? '▾' : '▸'}</span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="flex flex-wrap items-center gap-1 mt-2 px-1">
              {agentSteps.map((step, idx) => (
                <div key={`${step.agent}-${idx}`} className="flex items-center gap-1">
                  {idx > 0 && (
                    <span className={`text-[10px] mx-0.5 ${
                      step.status !== 'pending' ? 'text-slate-500' : 'text-slate-700'
                    }`}>
                      →
                    </span>
                  )}
                  <motion.span
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: idx * 0.05 }}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium
                      ${step.status === 'running' 
                        ? 'bg-amber-500/10 border border-amber-500/20 text-amber-300' 
                        : step.status === 'done'
                          ? 'bg-emerald-500/8 border border-emerald-500/15 text-emerald-400'
                          : 'bg-white/[0.02] border border-white/5 text-slate-600'
                      } transition-all duration-300`}
                  >
                    <span className={STATUS_COLORS[step.status]}>
                      {STATUS_ICONS[step.status]}
                    </span>
                    {step.label}
                  </motion.span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
