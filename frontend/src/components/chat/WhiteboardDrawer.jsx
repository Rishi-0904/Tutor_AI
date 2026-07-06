import React, { useRef, useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { IoClose, IoTrashOutline, IoArrowUndoOutline } from 'react-icons/io5'

/**
 * WhiteboardDrawer
 *
 * Props:
 *   isOpen          boolean
 *   onClose         () => void
 *   conversationId  string
 *   onSendToChat    (imageFile: File) => void   ← NEW: sends canvas PNG to chat input
 */
export default function WhiteboardDrawer({ isOpen, onClose, conversationId, onSendToChat }) {
  const canvasRef    = useRef(null)
  const contextRef   = useRef(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [color, setColor]         = useState('#00f0ff')
  const [lineWidth, setLineWidth] = useState(4)
  const [history, setHistory]     = useState([])
  const [exporting, setExporting] = useState(false)

  const colors = [
    { name: 'Cyan',   value: '#00f0ff' },
    { name: 'Pink',   value: '#ff007f' },
    { name: 'Green',  value: '#39ff14' },
    { name: 'Yellow', value: '#facc15' },
    { name: 'White',  value: '#ffffff' },
    { name: 'Eraser', value: '#0b1329' },
  ]

  // ── canvas setup ──────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return
    const canvas = canvasRef.current
    const ratio  = window.devicePixelRatio || 2
    const w = canvas.offsetWidth
    const h = canvas.offsetHeight
    canvas.width  = w * ratio
    canvas.height = h * ratio
    canvas.style.width  = `${w}px`
    canvas.style.height = `${h}px`

    const ctx = canvas.getContext('2d')
    ctx.scale(ratio, ratio)
    ctx.lineCap   = 'round'
    ctx.lineJoin  = 'round'
    ctx.strokeStyle = color
    ctx.lineWidth   = lineWidth
    contextRef.current = ctx
    redrawAll(ctx, history)
  }, [isOpen])

  useEffect(() => {
    if (contextRef.current) {
      contextRef.current.strokeStyle = color
      contextRef.current.lineWidth   = lineWidth
    }
  }, [color, lineWidth])

  // ── drawing helpers ───────────────────────────────────────
  const redrawAll = (ctx, paths) => {
    const canvas = canvasRef.current
    if (!canvas) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    paths.forEach((path) => {
      ctx.beginPath()
      ctx.strokeStyle = path.color
      ctx.lineWidth   = path.lineWidth
      path.points.forEach((pt, i) => {
        if (i === 0) ctx.moveTo(pt.x, pt.y)
        else         ctx.lineTo(pt.x, pt.y)
      })
      ctx.stroke()
    })
  }

  const getXY = (e) => {
    if (e.touches?.length > 0) {
      const rect = canvasRef.current.getBoundingClientRect()
      return { x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top }
    }
    return { x: e.offsetX, y: e.offsetY }
  }

  const startDrawing = (e) => {
    const { x, y } = getXY(e.nativeEvent)
    contextRef.current.beginPath()
    contextRef.current.moveTo(x, y)
    setIsDrawing(true)
    setHistory((prev) => [...prev, { color, lineWidth, points: [{ x, y }] }])
  }

  const draw = (e) => {
    if (!isDrawing) return
    const { x, y } = getXY(e.nativeEvent)
    contextRef.current.lineTo(x, y)
    contextRef.current.stroke()
    setHistory((prev) => {
      const updated = [...prev]
      updated[updated.length - 1].points.push({ x, y })
      return updated
    })
  }

  const stopDrawing = () => {
    if (isDrawing) { contextRef.current.closePath(); setIsDrawing(false) }
  }

  const handleUndo = () => {
    const next = history.slice(0, -1)
    setHistory(next)
    const ctx = canvasRef.current?.getContext('2d')
    if (ctx) redrawAll(ctx, next)
  }

  const handleClear = () => {
    setHistory([])
    const ctx = canvasRef.current?.getContext('2d')
    if (ctx) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
  }

  // ── SEND TO CHAT ─────────────────────────────────────────
  // Exports the canvas as a PNG File and passes it to the chat input
  const handleSendToChat = async () => {
    if (history.length === 0) return
    setExporting(true)

    const canvas = canvasRef.current

    // Composite: white bg + drawing (so dark background doesn't look terrible in chat)
    const offscreen = document.createElement('canvas')
    offscreen.width  = canvas.width
    offscreen.height = canvas.height

    const octx = offscreen.getContext('2d')
    // Dark canvas background matching our theme
    octx.fillStyle = '#0b1329'
    octx.fillRect(0, 0, offscreen.width, offscreen.height)
    octx.drawImage(canvas, 0, 0)

    offscreen.toBlob((blob) => {
      if (!blob) { setExporting(false); return }
      const file = new File([blob], 'whiteboard.png', { type: 'image/png' })
      onSendToChat(file)      // ← hands the File up to ChatPage → MessageInput
      setExporting(false)
      onClose()               // close the drawer so the user sees the chat input
    }, 'image/png', 0.95)
  }

  if (!isOpen) return null

  return (
    <motion.div
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 28, stiffness: 220 }}
      className="absolute top-0 right-0 w-[440px] h-full bg-[#080d1e]/97 border-l border-white/10 shadow-[0_0_60px_rgba(0,0,0,0.9)] backdrop-blur-2xl z-50 flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-white/5 bg-slate-900/40 flex justify-between items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-indigo-400 shadow-[0_0_6px_rgba(99,102,241,0.8)]" />
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Whiteboard</h3>
            <p className="text-[10px] text-slate-500">Draw · then tag it in chat</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-500 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
        >
          <IoClose className="w-4 h-4" />
        </button>
      </div>

      {/* Canvas */}
      <div className="flex-1 bg-[#0b1329] p-3 relative select-none">
        <canvas
          ref={canvasRef}
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawing}
          onTouchMove={draw}
          onTouchEnd={stopDrawing}
          className="w-full h-full rounded-xl cursor-crosshair border border-white/5"
        />
        {history.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 pointer-events-none">
            <p className="text-slate-700 text-sm font-medium">Start drawing…</p>
            <p className="text-slate-800 text-xs">Then click "Ask AI" to tag it in chat</p>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="p-4 border-t border-white/5 bg-slate-900/30 space-y-4">
        {/* Color palette */}
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Brush</span>
          <div className="flex gap-2 items-center">
            {colors.map((c) => (
              <button
                key={c.name}
                onClick={() => setColor(c.value)}
                style={{ backgroundColor: c.value === '#0b1329' ? '#111827' : c.value }}
                title={c.name}
                className={`w-5 h-5 rounded-full border-2 transition-all duration-150 relative ${
                  color === c.value
                    ? 'scale-125 border-white shadow-[0_0_8px_rgba(255,255,255,0.5)]'
                    : 'border-transparent hover:scale-110'
                }`}
              >
                {c.name === 'Eraser' && (
                  <span className="absolute inset-0 flex items-center justify-center text-[8px] text-red-400 font-bold">E</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Brush size */}
        <div className="flex items-center justify-between gap-4">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 whitespace-nowrap">Size</span>
          <div className="flex items-center gap-3 flex-1">
            <input
              type="range"
              min="2" max="20"
              value={lineWidth}
              onChange={(e) => setLineWidth(parseInt(e.target.value))}
              className="flex-1 accent-indigo-500 h-1 rounded-full cursor-pointer"
            />
            <span className="text-xs text-slate-400 font-mono w-6 text-right">{lineWidth}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={handleUndo}
            disabled={history.length === 0}
            className="flex items-center justify-center gap-1.5 py-2.5 bg-white/5 hover:bg-white/10 disabled:opacity-30 text-slate-400 hover:text-white rounded-xl text-xs font-semibold transition-all border border-white/5"
          >
            <IoArrowUndoOutline className="w-3.5 h-3.5" />
            Undo
          </button>
          <button
            onClick={handleClear}
            disabled={history.length === 0}
            className="flex items-center justify-center gap-1.5 py-2.5 bg-white/5 hover:bg-white/10 disabled:opacity-30 text-slate-400 hover:text-red-400 rounded-xl text-xs font-semibold transition-all border border-white/5"
          >
            <IoTrashOutline className="w-3.5 h-3.5" />
            Clear
          </button>

          {/* PRIMARY CTA */}
          <button
            onClick={handleSendToChat}
            disabled={history.length === 0 || exporting}
            className={`flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-bold transition-all border ${
              history.length === 0 || exporting
                ? 'bg-indigo-600/30 border-indigo-500/20 text-indigo-400/50 cursor-not-allowed'
                : 'bg-gradient-to-r from-indigo-600 to-violet-600 border-indigo-500/40 text-white shadow-lg shadow-indigo-600/30 hover:shadow-indigo-600/50 hover:scale-[1.02] active:scale-95'
            }`}
          >
            {exporting ? (
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            )}
            Ask AI
          </button>
        </div>

        <p className="text-center text-[10px] text-slate-700">
          "Ask AI" attaches this drawing to your next message
        </p>
      </div>
    </motion.div>
  )
}
