import React, { useState, useRef } from 'react'

export default function FunctionPlot({ data }) {
  const { expression, points } = data
  const [hoveredPoint, setHoveredPoint] = useState(null)
  const containerRef = useRef(null)

  if (!points || points.length === 0) {
    return (
      <div className="p-4 bg-red-950/20 border border-red-500/30 rounded-xl text-red-300 text-xs">
        No valid coordinates to plot for expression: {expression}
      </div>
    )
  }

  // Find min/max boundaries
  const xValues = points.map((p) => p.x)
  const yValues = points.map((p) => p.y)
  const minX = Math.min(...xValues)
  const maxX = Math.max(...xValues)
  const minY = Math.min(...yValues)
  const maxY = Math.max(...yValues)

  const margin = 40
  const width = 500
  const height = 300

  // Coordinate transformation helpers
  const scaleX = (x) => {
    const range = maxX - minX || 1
    return margin + ((x - minX) / range) * (width - 2 * margin)
  }

  const scaleY = (y) => {
    const range = maxY - minY || 1
    // Invert Y for SVG coordinates (0,0 is top-left)
    return height - margin - ((y - minY) / range) * (height - 2 * margin)
  }

  // Generate SVG path string
  let pathD = ""
  points.forEach((p, idx) => {
    const px = scaleX(p.x)
    const py = scaleY(p.y)
    if (idx === 0) {
      pathD += `M ${px} ${py}`
    } else {
      pathD += ` L ${px} ${py}`
    }
  })

  const handleMouseMove = (e) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const mouseX = e.clientX - rect.left

    // Find closest point by x-coordinate in SVG space
    let closest = null
    let minDist = Infinity

    points.forEach((p) => {
      const px = scaleX(p.x)
      const dist = Math.abs(px - (mouseX * (width / rect.width)))
      if (dist < minDist) {
        minDist = dist
        closest = p
      }
    })

    if (closest && minDist < 25) {
      setHoveredPoint(closest)
    } else {
      setHoveredPoint(null)
    }
  }

  const handleMouseLeave = () => {
    setHoveredPoint(null)
  }

  // Y=0 and X=0 axis positions
  const axisY = minY <= 0 && maxY >= 0 ? scaleY(0) : height - margin
  const axisX = minX <= 0 && maxX >= 0 ? scaleX(0) : margin

  return (
    <div 
      className="p-5 my-4 bg-slate-900/60 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl relative overflow-hidden"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      ref={containerRef}
    >
      <div className="absolute inset-0 bg-gradient-to-tr from-brand-500/5 to-purple-500/5 pointer-events-none"></div>
      
      <div className="flex justify-between items-center mb-3">
        <h4 className="text-sm font-semibold text-slate-200">
          Mathematical Plot: <span className="text-brand-300 font-mono font-medium">{expression}</span>
        </h4>
        <span className="text-[10px] bg-brand-500/20 text-brand-300 px-2 py-0.5 rounded-full border border-brand-500/30">
          Interactive
        </span>
      </div>

      <svg 
        viewBox={`0 0 ${width} ${height}`} 
        className="w-full h-auto text-slate-500 overflow-visible"
      >
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = margin + ratio * (height - 2 * margin)
          const x = margin + ratio * (width - 2 * margin)
          return (
            <React.Fragment key={ratio}>
              {/* Horizontal grid */}
              <line 
                x1={margin} y1={y} x2={width - margin} y2={y} 
                stroke="rgba(255,255,255,0.05)" strokeWidth={1} strokeDasharray="4 4" 
              />
              {/* Vertical grid */}
              <line 
                x1={x} y1={margin} x2={x} y2={height - margin} 
                stroke="rgba(255,255,255,0.05)" strokeWidth={1} strokeDasharray="4 4" 
              />
            </React.Fragment>
          )
        })}

        {/* X and Y Axes */}
        <line x1={margin} y1={axisY} x2={width - margin} y2={axisY} stroke="rgba(255,255,255,0.3)" strokeWidth={1.5} />
        <line x1={axisX} y1={margin} x2={axisX} y2={height - margin} stroke="rgba(255,255,255,0.3)" strokeWidth={1.5} />

        {/* Axis tick labels */}
        <text x={width - margin + 5} y={axisY + 4} fill="#64748b" fontSize={10} textAnchor="start">x</text>
        <text x={axisX} y={margin - 10} fill="#64748b" fontSize={10} textAnchor="middle">y</text>

        {/* Curve line */}
        <path 
          d={pathD} 
          fill="none" 
          stroke="url(#neon-gradient)" 
          strokeWidth={3} 
          strokeLinecap="round"
          className="drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]"
        />

        {/* Neon Gradient Def */}
        <defs>
          <linearGradient id="neon-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#818cf8" />
            <stop offset="50%" stopColor="#a78bfa" />
            <stop offset="100%" stopColor="#f472b6" />
          </linearGradient>
        </defs>

        {/* Hover tracker */}
        {hoveredPoint && (
          <>
            <line 
              x1={scaleX(hoveredPoint.x)} y1={margin} 
              x2={scaleX(hoveredPoint.x)} y2={height - margin} 
              stroke="rgba(129,140,248,0.3)" strokeWidth={1} strokeDasharray="2 2" 
            />
            <circle 
              cx={scaleX(hoveredPoint.x)} 
              cy={scaleY(hoveredPoint.y)} 
              r={6} 
              fill="#818cf8" 
              stroke="#ffffff" 
              strokeWidth={2}
              className="animate-pulse shadow-xl"
            />
          </>
        )}
      </svg>

      {/* Hover tooltip values */}
      <div className="h-6 flex items-center justify-center mt-2">
        {hoveredPoint ? (
          <span className="text-xs text-brand-300 font-mono">
            x: <strong className="text-slate-200">{hoveredPoint.x}</strong>, y: <strong className="text-slate-200">{hoveredPoint.y}</strong>
          </span>
        ) : (
          <span className="text-[10px] text-slate-500 italic">
            Hover cursor over plot area to inspect coordinates
          </span>
        )}
      </div>
    </div>
  )
}
