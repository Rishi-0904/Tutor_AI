import { useRef, useState, useEffect } from 'react'
import { motion, useInView, useScroll, useTransform, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'

/* ───────────────────────────────────────────
   SCROLL-REVEAL WRAPPER
   ─────────────────────────────────────────── */
function Reveal({ children, className = '', delay = 0 }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 32 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

/* ───────────────────────────────────────────
   NAVBAR
   ─────────────────────────────────────────── */
function LandingNav() {
  return (
    <motion.nav
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50 glass-navbar px-6 py-4"
    >
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
            <span className="text-white text-sm font-bold">T</span>
          </div>
          <span className="text-white font-extrabold text-lg tracking-tight group-hover:text-indigo-400 transition-colors">
            TutorAI
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
          <a href="#how-it-works" className="hover:text-white underline-hover transition-all duration-200">How It Works</a>
          <a href="#features" className="hover:text-white underline-hover transition-all duration-200">Features</a>
          <a href="#workflow" className="hover:text-white underline-hover transition-all duration-200">Workflow</a>
          <a href="#architecture" className="hover:text-white underline-hover transition-all duration-200">Architecture</a>
          <a href="#tech" className="hover:text-white underline-hover transition-all duration-200">Tech Stack</a>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/login"
            className="text-sm text-slate-400 hover:text-white transition-colors px-4 py-2">
            Sign In
          </Link>
          <Link to="/login"
            className="text-sm font-semibold text-white px-5 py-2.5 rounded-xl transition-all duration-200 hover:scale-105"
            style={{
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              boxShadow: '0 0 20px rgba(99,102,241,0.3)',
            }}>
            Get Started
          </Link>
        </div>
      </div>
    </motion.nav>
  )
}

/* ───────────────────────────────────────────
   HERO SECTION
   ─────────────────────────────────────────── */
function HeroSection() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] })
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0])
  const scale = useTransform(scrollYProgress, [0, 0.5], [1, 0.95])
  const y = useTransform(scrollYProgress, [0, 0.5], [0, 60])

  return (
    <motion.section
      ref={ref}
      style={{ opacity, scale, y }}
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden pt-28 pb-16"
    >
      {/* Ambient background blur blobs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full blur-[140px] opacity-30"
          style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.18), transparent 70%)' }} />
        <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] rounded-full blur-[120px] opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.15), transparent 70%)' }} />
      </div>

      <div className="relative z-10 text-center max-w-4xl mx-auto px-6">
        {/* Outcome-led top badge */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8 text-xs font-semibold"
          style={{
            background: 'rgba(99,102,241,0.08)',
            border: '1px solid rgba(99,102,241,0.2)',
            color: '#a5b4fc',
          }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Rank-Boosting Platform for JEE & NEET Aspirants
        </motion.div>

        {/* Outcome-led Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="text-5xl md:text-7xl font-extrabold leading-[1.1] tracking-tight mb-6"
        >
          <span className="text-white">Solve Doubts Instantly.</span>
          <br />
          <span className="gradient-text">Practice Adaptively.</span>
          <br />
          <span className="text-white">Master Concepts.</span>
        </motion.h1>

        {/* Short value statement */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="text-base md:text-lg text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          TutorAI helps you study smarter. Upload your notes, ask tricky textbook doubts,
          get step-by-step mathematical explanations, and take diagnostic quizzes calibrated to your weak areas.
        </motion.p>

        {/* Primary Call to Action */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.6 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
        >
          <Link to="/login"
            className="group relative px-8 py-4 rounded-2xl font-bold text-white text-base transition-all duration-300 hover:scale-105"
            style={{
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              boxShadow: '0 0 30px rgba(99,102,241,0.4)',
            }}>
            Start Studying Now
            <span className="ml-2 inline-block group-hover:translate-x-1 transition-transform">→</span>
          </Link>
          <a href="#how-it-works"
            className="px-8 py-4 rounded-2xl font-semibold text-slate-300 text-base transition-all duration-300 hover:text-white hover:bg-white/5"
            style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
            Learn More
          </a>
        </motion.div>

        {/* Live product screenshot/mockup */}
        <Reveal delay={0.7} className="relative w-full max-w-4xl mx-auto">
          <div className="absolute inset-0 bg-gradient-to-t from-[#080b14] via-transparent to-transparent z-10 pointer-events-none" />
          <motion.div
            whileHover={{ y: -4, rotateX: 1, rotateY: -1 }}
            transition={{ duration: 0.4 }}
            className="rounded-3xl border border-white/8 overflow-hidden shadow-glow-indigo bg-surface-900"
          >
            <img
              src="/tutor_ai_demo_mockup.png"
              alt="TutorAI Application Interface"
              className="w-full h-auto object-cover opacity-90 hover:opacity-100 transition-opacity"
            />
          </motion.div>
        </Reveal>
      </div>
    </motion.section>
  )
}

/* ───────────────────────────────────────────
   "HOW IT WORKS" 3-STEP TIMELINE
   ─────────────────────────────────────────── */
const HOW_IT_WORKS = [
  {
    step: '01',
    title: 'Upload & Scan Notes',
    desc: 'Take a photo of a tricky textbook question or upload lecture notes. Our vision system extracts raw equations and diagrams with high precision.',
    icon: '📷',
  },
  {
    step: '02',
    title: 'Ask & Interact',
    desc: 'Ask follow-up questions to break down derivations. Specialized solver tools generate explanations using step-by-step LaTeX formatting.',
    icon: '💬',
  },
  {
    step: '03',
    title: 'Master via Quizzes',
    desc: 'Verify understanding with custom conceptual quizzes. The system monitors weak topics and adapts difficulty dynamically.',
    icon: '🏆',
  },
]

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="relative py-28 px-6 bg-surface-900/40">
      <div className="max-w-6xl mx-auto">
        <Reveal>
          <div className="text-center mb-20">
            <span className="text-xs uppercase tracking-widest text-indigo-400 font-bold">Process</span>
            <h2 className="text-4xl md:text-5xl font-extrabold text-white mt-3 mb-4">
              Simple 3-Step <span className="gradient-text">Learning Loop</span>
            </h2>
            <p className="text-slate-400 max-w-lg mx-auto">
              How TutorAI builds deep understanding and boosts test scores.
            </p>
          </div>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          {HOW_IT_WORKS.map((h, i) => (
            <Reveal key={h.step} delay={i * 0.15}>
              <div className="relative p-6 rounded-2xl bg-white/[0.02] border border-white/[0.02] overflow-hidden group">
                <span className="absolute top-4 right-6 text-6xl font-extrabold text-white/[0.02] group-hover:text-white/[0.04] transition-colors font-mono select-none">
                  {h.step}
                </span>
                <div className="text-3xl mb-4 p-3 bg-white/[0.02] rounded-xl w-fit border border-white/5">
                  {h.icon}
                </div>
                <h3 className="text-lg font-bold text-white mb-2">{h.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{h.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ───────────────────────────────────────────
   FEATURE BENTO GRID
   ─────────────────────────────────────────── */
const BENTO_FEATURES = [
  {
    icon: '📝', title: 'Adaptive MCQ Assessments',
    desc: 'Calibrated diagnostic quizzes focusing exclusively on your weak topic tags to strengthen areas of difficulty.',
    gradient: 'from-orange-500/10 to-amber-500/5',
    border: 'border-orange-500/15',
    span: 'col-span-1',
  },
  {
    icon: '🎓', title: 'Interactive Teach-Back Mode',
    desc: 'Explain concepts in your own words. The evaluator agent scans for coverage, missing ideas, and misconceptions.',
    gradient: 'from-emerald-500/10 to-teal-500/5',
    border: 'border-emerald-500/15',
    span: 'col-span-1 md:col-span-2',
  },
  {
    icon: '📸', title: 'Problem Scanner (OCR)',
    desc: 'Extract and format physical/chemical equations instantly. Supports hand-written sketches and textbook figures.',
    gradient: 'from-pink-500/10 to-rose-500/5',
    border: 'border-pink-500/15',
    span: 'col-span-1',
  },
  {
    icon: '📊', title: 'Detailed Mastery Analytics',
    desc: 'Monitor topic tags, study streak dynamics, average accuracy metrics, and response completion statistics.',
    gradient: 'from-cyan-500/10 to-sky-500/5',
    border: 'border-cyan-500/15',
    span: 'col-span-1',
  },
  {
    icon: '🔎', title: 'Critic Agent Quality Assurance',
    desc: 'Dual-pass verification ensures explanations are factually correct and include detailed derivations.',
    gradient: 'from-indigo-500/10 to-violet-500/5',
    border: 'border-indigo-500/15',
    span: 'col-span-1',
  },
]

function FeaturesSection() {
  return (
    <section id="features" className="relative py-28 px-6">
      <div className="max-w-6xl mx-auto">
        <Reveal>
          <div className="text-center mb-16">
            <span className="text-xs uppercase tracking-widest text-indigo-400 font-bold">Features</span>
            <h2 className="text-4xl md:text-5xl font-extrabold text-white mt-3 mb-4">
              Everything Needed to <span className="gradient-text">Master Concepts</span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Specially engineered modules targeting exam syllabus requirements.
            </p>
          </div>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {BENTO_FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.08} className={f.span}>
              <div className={`group relative h-full rounded-2xl border ${f.border} bg-gradient-to-br ${f.gradient} p-6 overflow-hidden transition-all duration-300 hover:scale-[1.02]`}>
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl"
                  style={{ boxShadow: 'inset 0 0 40px rgba(99,102,241,0.05)' }} />
                
                <div className="relative">
                  <div className="text-3xl mb-4 group-hover:scale-115 transition-transform duration-300 inline-block">{f.icon}</div>
                  <h3 className="text-base font-bold text-white mb-2">{f.title}</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ───────────────────────────────────────────
   STUDENT WORKFLOW / LEARNING LOOP
   ─────────────────────────────────────────── */
const WORKFLOW_STEPS = [
  { step: 'Doubt', icon: '❓', desc: 'Ask a text/image query' },
  { step: 'Explanation', icon: '📚', desc: 'Step-by-step derivations' },
  { step: 'Quiz', icon: '📝', desc: 'Test topic mastery' },
  { step: 'Teach Back', icon: '🎓', desc: 'Validate active recall' },
  { step: 'Analytics', icon: '📊', desc: 'Personalized tag telemetry' },
  { step: 'Mastery', icon: '🏆', desc: 'Concept unlocked' },
]

function WorkflowSection() {
  return (
    <section id="workflow" className="relative py-28 px-6 bg-surface-900/30">
      <div className="max-w-5xl mx-auto">
        <Reveal>
          <div className="text-center mb-16">
            <span className="text-xs uppercase tracking-widest text-indigo-400 font-bold">Feedback Loop</span>
            <h2 className="text-4xl md:text-5xl font-extrabold text-white mt-3 mb-4">
              Complete <span className="gradient-text">Student Workflow</span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              How students advance from initial question to guaranteed syllabus mastery.
            </p>
          </div>
        </Reveal>

        <div className="relative flex flex-col md:flex-row items-center justify-between gap-6 md:gap-3">
          {WORKFLOW_STEPS.map((w, i) => (
            <Reveal key={w.step} delay={i * 0.08} className="w-full md:w-auto">
              <div className="flex flex-col items-center text-center p-4 rounded-xl bg-white/[0.01] border border-white/[0.03] w-full md:w-[130px]">
                <div className="text-3xl mb-2">{w.icon}</div>
                <h4 className="text-sm font-bold text-white mb-1">{w.step}</h4>
                <p className="text-[10px] text-slate-500 leading-tight">{w.desc}</p>
              </div>
              {i < WORKFLOW_STEPS.length - 1 && (
                <div className="text-indigo-500/40 text-xl font-bold hidden md:block text-center mt-4">
                  →
                </div>
              )}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ───────────────────────────────────────────
   ARCHITECTURE SECTION
   ─────────────────────────────────────────── */
const PIPELINE_NODES = [
  { id: 'orchestrator', label: '🧠 Orchestrator', desc: 'Classifies intent', color: '#6366f1' },
  { id: 'research', label: '🔍 Research', desc: 'Web + YouTube search', color: '#0ea5e9' },
  { id: 'tutor', label: '📚 Tutor', desc: 'Core reasoning engine', color: '#8b5cf6' },
  { id: 'critic', label: '🔎 Critic', desc: 'Quality assurance', color: '#f97316' },
  { id: 'memory', label: '💾 Memory', desc: 'Mastery tracking', color: '#10b981' },
  { id: 'composer', label: '✨ Composer', desc: 'Final formatting', color: '#ec4899' },
]

function ArchitectureSection() {
  return (
    <section id="architecture" className="relative py-28 px-6">
      <div className="max-w-5xl mx-auto relative">
        <Reveal>
          <div className="text-center mb-16">
            <span className="text-xs uppercase tracking-widest text-indigo-400 font-bold">For Technical Visitors</span>
            <h2 className="text-4xl md:text-5xl font-extrabold text-white mt-3 mb-4">
              Multi-Agent <span className="gradient-text">LangGraph Pipeline</span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Behind the simple interface sits a robust coordination graph ensuring precise answers.
            </p>
          </div>
        </Reveal>

        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 md:gap-4">
          {PIPELINE_NODES.map((node, i) => (
            <Reveal key={node.id} delay={i * 0.08}>
              <motion.div
                whileHover={{ scale: 1.05, y: -2 }}
                className="group relative flex flex-col items-center gap-1.5 p-4 rounded-xl cursor-default transition-all duration-300"
                style={{
                  background: `linear-gradient(135deg, ${node.color}12, ${node.color}04)`,
                  border: `1px solid ${node.color}20`,
                  textAlign: 'center',
                }}
              >
                <span className="text-2xl relative">{node.label.split(' ')[0]}</span>
                <span className="text-[11px] font-bold text-white relative">{node.label.split(' ').slice(1).join(' ')}</span>
                <span className="text-[9px] text-slate-500 relative leading-tight">{node.desc}</span>
                
                <div className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full"
                  style={{ background: `linear-gradient(90deg, transparent, ${node.color}50, transparent)` }} />
              </motion.div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.5}>
          <div className="flex justify-center mt-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs text-slate-500"
              style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.04)' }}>
              <span className="text-amber-400 animate-spin-slow">↺</span>
              The critic automatically loops back if answers miss required technical details.
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ───────────────────────────────────────────
   INTERACTIVE CAROUSEL
   ─────────────────────────────────────────── */
const SLIDES = [
  {
    title: 'Dashboard Workspace',
    desc: 'Track mastery progress across Physics, Chemistry, and Math with weekly heatmaps, analytics metrics, and study streaks.',
    img: '/dashboard_page_mockup.png',
  },
  {
    title: 'AI Doubt Solver',
    desc: 'Get LaTeX-rendered equations, live coordinate plots, and conceptual summaries for complex board and exam questions.',
    img: '/chat_page_mockup.png',
  },
]

function CarouselSection() {
  const [activeIdx, setActiveIdx] = useState(0)

  return (
    <section className="relative py-28 px-6 bg-surface-900/40">
      <div className="max-w-5xl mx-auto">
        <Reveal>
          <div className="text-center mb-16">
            <span className="text-xs uppercase tracking-widest text-indigo-400 font-bold">Visuals</span>
            <h2 className="text-4xl md:text-5xl font-extrabold text-white mt-3 mb-4">
              Explore the <span className="gradient-text">Workspace</span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Real screenshots of the platform designed to accelerate study speeds.
            </p>
          </div>
        </Reveal>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
          {/* Controls */}
          <div className="space-y-4">
            {SLIDES.map((slide, idx) => (
              <Reveal key={slide.title} delay={idx * 0.1}>
                <button
                  onClick={() => setActiveIdx(idx)}
                  className={`w-full text-left p-5 rounded-2xl border transition-all duration-300 ${
                    activeIdx === idx
                      ? 'bg-indigo-600/10 border-indigo-500/30 shadow-glow-indigo'
                      : 'bg-white/[0.01] border-white/[0.04] hover:bg-white/[0.03]'
                  }`}
                >
                  <h4 className="font-bold text-white text-base mb-1.5">{slide.title}</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">{slide.desc}</p>
                </button>
              </Reveal>
            ))}
          </div>

          {/* Picture frame */}
          <div className="lg:col-span-2 relative">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeIdx}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.4 }}
                className="rounded-2xl border border-white/8 overflow-hidden bg-surface-900 shadow-glow-card"
              >
                <img
                  src={SLIDES[activeIdx].img}
                  alt={SLIDES[activeIdx].title}
                  className="w-full h-auto object-cover"
                />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ───────────────────────────────────────────
   TECH STACK SECTION
   ─────────────────────────────────────────── */
const TECH_ITEMS = [
  { name: 'React.js', role: 'Interactive Frontend' },
  { name: 'FastAPI', role: 'High-Performance API' },
  { name: 'LangGraph', role: 'Multi-Agent StateGraph' },
  { name: 'Supabase', role: 'Database & Auth' },
  { name: 'DeepSeek V4', role: 'Reasoning Engine' },
  { name: 'Llama 3.1', role: 'Critic Evaluator' },
  { name: 'Phi-4 Mini', role: 'GRPO Fine-Tuned Local Models' },
  { name: 'Vite', role: 'Asset Bundling' },
]

function TechSection() {
  return (
    <section id="tech" className="relative py-28 px-6">
      <div className="max-w-5xl mx-auto">
        <Reveal>
          <div className="text-center mb-12">
            <span className="text-xs uppercase tracking-widest text-indigo-400 font-bold">Tech Stack</span>
            <h2 className="text-4xl md:text-5xl font-extrabold text-white mt-3 mb-4">
              Engineered for <span className="gradient-text">Scale</span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Modern framework ecosystem driving fast token streaming and query parsing.
            </p>
          </div>
        </Reveal>

        <div className="flex flex-wrap justify-center gap-3">
          {TECH_ITEMS.map((t, i) => (
            <Reveal key={t.name} delay={i * 0.05}>
              <div
                className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:border-white/10 transition-colors cursor-default"
              >
                <div className="w-2 h-2 rounded-full bg-indigo-400" />
                <div>
                  <div className="text-xs font-bold text-white">{t.name}</div>
                  <div className="text-[9px] text-slate-500">{t.role}</div>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ───────────────────────────────────────────
   FINAL CTA + FOOTER
   ─────────────────────────────────────────── */
function CTASection() {
  return (
    <section className="relative py-28 px-6">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[700px] h-[350px] rounded-full blur-[140px] opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.15), transparent 70%)' }} />
      </div>

      <div className="max-w-3xl mx-auto relative text-center">
        <Reveal>
          <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-6">
            Boost Your Syllabus <span className="gradient-text">Mastery</span>
          </h2>
          <p className="text-base text-slate-400 mb-10 max-w-lg mx-auto">
            Interact with specialized multi-agent tutors and check active recall metrics on every study topic.
          </p>
          <Link to="/login"
            className="group inline-flex items-center gap-2 px-10 py-4 rounded-2xl font-bold text-white text-lg transition-all duration-300 hover:scale-105"
            style={{
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              boxShadow: '0 0 30px rgba(99,102,241,0.4)',
            }}>
            Sign Up for Free
            <span className="group-hover:translate-x-1 transition-transform">→</span>
          </Link>
        </Reveal>
      </div>

      <Reveal delay={0.2}>
        <div className="max-w-6xl mx-auto mt-24 pt-8 text-center"
          style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-6 h-6 rounded-lg flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
              <span className="text-white text-[10px] font-bold">T</span>
            </div>
            <span className="text-sm font-bold text-white">TutorAI</span>
          </div>
          <p className="text-[10px] text-slate-600">
            Multi-Agent AI Tutoring System • Powered by LangGraph & GRPO Fine-Tuned Models
          </p>
          <p className="text-[9px] text-slate-700 mt-2">
            © {new Date().getFullYear()} TutorAI. All rights reserved.
          </p>
        </div>
      </Reveal>
    </section>
  )
}

/* ───────────────────────────────────────────
   MAIN LANDING PAGE
   ─────────────────────────────────────────── */
export default function LandingPage() {
  const [coords, setCoords] = useState({ x: 0, y: 0 })

  const handleMouseMove = (e) => {
    setCoords({ x: e.clientX, y: e.clientY })
  }

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <div
      className="min-h-screen relative overflow-hidden"
      style={{
        background: '#080b14',
        '--x': `${coords.x}px`,
        '--y': `${coords.y}px`
      }}
    >
      {/* Interactive cursor glow layout */}
      <div className="fixed inset-0 pointer-events-none z-0 cursor-glow-bg opacity-40" />

      <div className="relative z-10">
        <LandingNav />
        <HeroSection />
        <HowItWorksSection />
        <FeaturesSection />
        <WorkflowSection />
        <ArchitectureSection />
        <CarouselSection />
        <TechSection />
        <CTASection />
      </div>
    </div>
  )
}
