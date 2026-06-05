import React, { useState, useEffect, useRef } from 'react'

export default function DPTable({ data }) {
  const { problem, row_labels = [], col_labels = [], grid = [], explanation = '', steps = [] } = data
  const [currentStep, setCurrentStep] = useState(-1)
  const [isPlaying, setIsPlaying] = useState(false)
  const timerRef = useRef(null)

  // Map to find which step index fills which cell
  const stepMap = {}
  steps.forEach((step, idx) => {
    if (step && step.cell) {
      const key = `${step.cell[0]}-${step.cell[1]}`
      stepMap[key] = idx
    }
  })

  const isCellRevealed = (r, c) => {
    const key = `${r}-${c}`
    if (key in stepMap) {
      return currentStep >= stepMap[key]
    }
    // If not in steps list, it's a base case / pre-filled cell
    return true
  }

  const isCellCurrent = (r, c) => {
    if (currentStep < 0 || currentStep >= steps.length) return false
    const activeStep = steps[currentStep]
    return activeStep && activeStep.cell && activeStep.cell[0] === r && activeStep.cell[1] === c
  }

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1)
    } else {
      setIsPlaying(false) // stop at end
    }
  }

  const handlePrev = () => {
    if (currentStep >= 0) {
      setCurrentStep((prev) => prev - 1)
    }
  }

  const handleReset = () => {
    setCurrentStep(-1)
    setIsPlaying(false)
  }

  // Handle Autoplay Loop
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev < steps.length - 1) {
            return prev + 1
          } else {
            setIsPlaying(false)
            return prev
          }
        })
      }, 2000) // 2 seconds delay
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isPlaying, steps.length])

  const activeStepDetail = currentStep >= 0 && currentStep < steps.length ? steps[currentStep] : null

  return (
    <div className="p-5 my-4 bg-slate-900/60 border border-white/10 rounded-2xl backdrop-blur-xl shadow-2xl relative">
      <div className="absolute inset-0 bg-gradient-to-tr from-purple-500/5 to-pink-500/5 pointer-events-none"></div>

      {/* Header */}
      <div className="flex justify-between items-center mb-4 relative z-10">
        <div>
          <h4 className="text-sm font-semibold text-slate-200">
            DP Visualizer: <span className="text-purple-300 font-medium">{problem}</span>
          </h4>
          {explanation && (
            <p className="text-[10px] text-slate-400 font-mono mt-0.5">{explanation}</p>
          )}
        </div>
        <span className="text-[10px] bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full border border-purple-500/30 font-medium">
          DP Matrix
        </span>
      </div>

      {/* Grid Viewport */}
      <div className="overflow-x-auto w-full my-3 styled-scrollbar relative z-10 border border-white/5 rounded-xl bg-slate-950/40 p-2">
        <table className="min-w-full text-center border-collapse">
          <thead>
            <tr>
              {/* Top-left corner cell */}
              <th className="px-2.5 py-1.5 text-xs font-semibold text-slate-500 border border-white/5 bg-slate-900/50"></th>
              {col_labels.map((col, cIdx) => (
                <th 
                  key={cIdx} 
                  className="px-2.5 py-1.5 text-xs font-semibold text-slate-300 border border-white/5 bg-slate-900/50 font-mono"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.map((row, rIdx) => (
              <tr key={rIdx}>
                {/* Row Headers */}
                <td className="px-2.5 py-1.5 text-xs font-semibold text-slate-300 border border-white/5 bg-slate-900/50 text-left font-mono">
                  {row_labels[rIdx] || `Row ${rIdx}`}
                </td>
                {row.map((cellVal, cIdx) => {
                  const revealed = isCellRevealed(rIdx, cIdx)
                  const current = isCellCurrent(rIdx, cIdx)
                  
                  return (
                    <td 
                      key={cIdx} 
                      className={`px-3 py-2 text-xs font-mono border border-white/5 transition-all duration-300 relative ${
                        current 
                          ? 'bg-purple-500/20 text-white font-bold ring-2 ring-purple-500 ring-inset shadow-[0_0_15px_rgba(168,85,247,0.4)] z-20' 
                          : revealed 
                            ? 'bg-white/5 text-slate-200' 
                            : 'bg-white/[0.01] text-slate-600 select-none'
                      }`}
                    >
                      {revealed ? cellVal : '-'}
                      {current && (
                        <span className="absolute top-0 right-0 w-1.5 h-1.5 bg-purple-400 rounded-full animate-ping"></span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Simulation Control Panel */}
      <div className="flex flex-wrap items-center justify-between gap-3 mt-4 pt-3 border-t border-white/5 relative z-10">
        <div className="flex gap-2">
          <button 
            onClick={handlePrev} 
            disabled={currentStep < 0}
            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 disabled:opacity-40 disabled:hover:bg-white/5 text-slate-300 rounded-lg text-xs font-medium transition-all"
          >
            ◀ Back
          </button>
          <button 
            onClick={handleNext} 
            disabled={currentStep >= steps.length - 1}
            className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 disabled:hover:bg-purple-600 text-white rounded-lg text-xs font-medium transition-all shadow-md shadow-purple-600/20"
          >
            Next Step ▶
          </button>
          <button 
            onClick={handleReset}
            className="px-2.5 py-1.5 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-slate-300 rounded-lg text-xs font-medium transition-all"
          >
            Reset
          </button>
        </div>

        <button
          onClick={() => setIsPlaying((p) => !p)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            isPlaying 
              ? 'bg-red-500/20 border border-red-500/30 text-red-300' 
              : 'bg-green-500/20 border border-green-500/30 text-green-300'
          }`}
        >
          {isPlaying ? '⏸ Pause Auto' : '▶ Play Auto'}
        </button>

        <div className="text-[10px] text-slate-500 font-mono">
          Step: <span className="text-slate-300">{currentStep + 1}</span> / {steps.length}
        </div>
      </div>

      {/* Description Panel */}
      <div className="mt-4 p-3.5 bg-slate-950/60 border border-white/5 rounded-xl min-h-[50px] relative z-10">
        {activeStepDetail ? (
          <div>
            <div className="text-[10px] text-purple-400 font-mono font-medium mb-1">
              FITTING CELL [{activeStepDetail.cell[0]}, {activeStepDetail.cell[1]}] = {activeStepDetail.val}
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              {activeStepDetail.desc}
            </p>
          </div>
        ) : currentStep === -1 ? (
          <p className="text-xs text-slate-500 italic">
            Visualizer initialized. Click "Next Step" or "Play Auto" to start cell-by-cell calculations.
          </p>
        ) : (
          <p className="text-xs text-green-400 font-medium">
            🎉 Dynamic programming grid complete! All cells successfully filled.
          </p>
        )}
      </div>
    </div>
  )
}
