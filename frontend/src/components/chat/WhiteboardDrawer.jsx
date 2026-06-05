import React, { useRef, useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { IoClose, IoTrashOutline, IoArrowUndoOutline, IoSaveOutline } from 'react-icons/io5'
import API from '../../lib/api'
import toast from 'react-hot-toast'

export default function WhiteboardDrawer({ isOpen, onClose, conversationId }) {
  const canvasRef = useRef(null)
  const contextRef = useRef(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [color, setColor] = useState('#00f0ff') // neon cyan default
  const [lineWidth, setLineWidth] = useState(4)
  const [history, setHistory] = useState([]) // stores vector paths for undo
  const [title, setTitle] = useState('New Concept Sketch')

  const colors = [
    { name: 'Cyan', value: '#00f0ff' },
    { name: 'Pink', value: '#ff007f' },
    { name: 'Green', value: '#39ff14' },
    { name: 'White', value: '#ffffff' },
    { name: 'Eraser', value: '#0b1329' } // matches dark canvas bg
  ]

  useEffect(() => {
    if (!isOpen) return

    const canvas = canvasRef.current
    // Adjust size for screen resolution
    canvas.width = canvas.offsetWidth * 2
    canvas.height = canvas.offsetHeight * 2
    canvas.style.width = `${canvas.offsetWidth}px`
    canvas.style.height = `${canvas.offsetHeight}px`

    const context = canvas.getContext('2d')
    context.scale(2, 2)
    context.lineCap = 'round'
    context.lineJoin = 'round'
    context.strokeStyle = color
    context.lineWidth = lineWidth
    contextRef.current = context

    // Redraw if history exists
    redrawHistory(context)
  }, [isOpen])

  // Stroke setup updates
  useEffect(() => {
    if (contextRef.current) {
      contextRef.current.strokeStyle = color
      contextRef.current.lineWidth = lineWidth
    }
  }, [color, lineWidth])

  const redrawHistory = (ctx) => {
    if (!ctx) return
    ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
    history.forEach((path) => {
      ctx.beginPath()
      ctx.strokeStyle = path.color
      ctx.lineWidth = path.lineWidth
      path.points.forEach((pt, i) => {
        if (i === 0) {
          ctx.moveTo(pt.x, pt.y)
        } else {
          ctx.lineTo(pt.x, pt.y)
        }
      })
      ctx.stroke()
    })
  }

  const startDrawing = ({ nativeEvent }) => {
    const { offsetX, offsetY } = getCoordinates(nativeEvent)
    contextRef.current.beginPath()
    contextRef.current.moveTo(offsetX, offsetY)
    setIsDrawing(true)

    // Start tracking new path in history
    setHistory((prev) => [
      ...prev,
      { color, lineWidth, points: [{ x: offsetX, y: offsetY }] }
    ])
  }

  const draw = ({ nativeEvent }) => {
    if (!isDrawing) return
    const { offsetX, offsetY } = getCoordinates(nativeEvent)
    contextRef.current.lineTo(offsetX, offsetY)
    contextRef.current.stroke()

    // Add point to active path in history
    setHistory((prev) => {
      const updated = [...prev]
      const activePath = updated[updated.length - 1]
      activePath.points.push({ x: offsetX, y: offsetY })
      return updated
    })
  }

  const stopDrawing = () => {
    if (isDrawing) {
      contextRef.current.closePath()
      setIsDrawing(false)
    }
  }

  const getCoordinates = (event) => {
    if (event.touches && event.touches.length > 0) {
      const rect = canvasRef.current.getBoundingClientRect()
      return {
        offsetX: event.touches[0].clientX - rect.left,
        offsetY: event.touches[0].clientY - rect.top
      }
    }
    return {
      offsetX: event.offsetX,
      offsetY: event.offsetY
    }
  }

  const handleUndo = () => {
    if (history.length === 0) return
    const newHistory = history.slice(0, -1)
    setHistory(newHistory)
    // Clear and redraw
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')
    context.clearRect(0, 0, canvas.width, canvas.height)
    newHistory.forEach((path) => {
      context.beginPath()
      context.strokeStyle = path.color
      context.lineWidth = path.lineWidth
      path.points.forEach((pt, i) => {
        if (i === 0) {
          context.moveTo(pt.x, pt.y)
        } else {
          context.lineTo(pt.x, pt.y)
        }
      })
      context.stroke()
    })
  }

  const handleClear = () => {
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')
    context.clearRect(0, 0, canvas.width, canvas.height)
    setHistory([])
  }

  const handleSave = async () => {
    if (history.length === 0) {
      toast.error('Sketch area is empty')
      return
    }

    try {
      const payload = {
        conversationId,
        title: title || 'Concept Sketch',
        svgData: JSON.stringify(history)
      }
      
      const loadingToast = toast.loading('Saving sketch to Supabase...')
      await API.post('/conversations/sketch', payload)
      toast.dismiss(loadingToast)
      toast.success(`Sketch "${title}" saved successfully!`)
      onClose()
    } catch (err) {
      toast.error('Failed to save sketch')
      console.error(err)
    }
  }

  if (!isOpen) return null

  return (
    <motion.div
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="absolute top-0 right-0 w-[420px] h-full bg-slate-950/95 border-l border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.8)] backdrop-blur-2xl z-50 flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-white/5 bg-slate-900/40 flex justify-between items-center">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Interactive Whiteboard</h3>
          <input 
            type="text" 
            value={title} 
            onChange={(e) => setTitle(e.target.value)}
            className="text-[10px] bg-transparent text-indigo-400 border-none outline-none focus:ring-0 w-full p-0 font-medium"
          />
        </div>
        <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-white bg-white/5 rounded-lg transition-colors">
          <IoClose className="w-5 h-5" />
        </button>
      </div>

      {/* Drawing Canvas Area */}
      <div className="flex-1 bg-slate-950 p-4 flex items-center justify-center relative select-none">
        <canvas
          ref={canvasRef}
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawing}
          onTouchMove={draw}
          onTouchEnd={stopDrawing}
          className="w-full h-full border border-white/10 rounded-2xl cursor-crosshair shadow-inner bg-[#0b1329]"
        />
      </div>

      {/* Control Panel Footer */}
      <div className="p-5 border-t border-white/5 bg-slate-900/30 space-y-4">
        {/* Neon Brushes selection */}
        <div className="flex justify-between items-center">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Color Palette</span>
          <div className="flex gap-2">
            {colors.map((c) => (
              <button
                key={c.name}
                onClick={() => setColor(c.value)}
                style={{ backgroundColor: c.value === '#0b1329' ? '#000000' : c.value }}
                className={`w-6 h-6 rounded-full border transition-all duration-250 relative ${
                  color === c.value 
                    ? 'scale-110 border-white ring-2 ring-indigo-500 shadow-lg' 
                    : 'border-white/20 hover:border-white/40'
                }`}
                title={c.name}
              >
                {c.name === 'Eraser' && (
                  <span className="absolute inset-0 flex items-center justify-center text-[8px] text-red-400 font-bold">E</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Thickness settings */}
        <div className="flex justify-between items-center">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Brush Size</span>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min="2"
              max="16"
              value={lineWidth}
              onChange={(e) => setLineWidth(parseInt(e.target.value))}
              className="w-32 accent-indigo-500 bg-slate-700 h-1.5 rounded-full cursor-pointer"
            />
            <span className="text-xs text-slate-300 font-mono w-4 text-right">{lineWidth}px</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-3 gap-2.5 pt-2">
          <button
            onClick={handleUndo}
            disabled={history.length === 0}
            className="flex items-center justify-center gap-2 py-2 bg-white/5 hover:bg-white/10 disabled:opacity-40 disabled:hover:bg-white/5 text-slate-300 rounded-xl text-xs font-semibold transition-all border border-white/5"
          >
            <IoArrowUndoOutline className="w-4 h-4" />
            Undo
          </button>
          <button
            onClick={handleClear}
            disabled={history.length === 0}
            className="flex items-center justify-center gap-2 py-2 bg-white/5 hover:bg-white/10 disabled:opacity-40 disabled:hover:bg-white/5 text-slate-300 rounded-xl text-xs font-semibold transition-all border border-white/5"
          >
            <IoTrashOutline className="w-4 h-4" />
            Clear
          </button>
          <button
            onClick={handleSave}
            className="flex items-center justify-center gap-2 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-all shadow-md shadow-indigo-600/20"
          >
            <IoSaveOutline className="w-4 h-4" />
            Save to Chat
          </button>
        </div>
      </div>
    </motion.div>
  )
}
