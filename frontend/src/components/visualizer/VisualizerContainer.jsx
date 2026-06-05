import React from 'react'
import FunctionPlot from './FunctionPlot'
import Flowchart from './Flowchart'
import DPTable from './DPTable'

export default function VisualizerContainer({ type, data }) {
  let parsedData = null
  let parseError = null

  try {
    // Standard cleanup of markdown text
    const cleanJson = typeof data === 'string' ? data.trim() : JSON.stringify(data)
    parsedData = JSON.parse(cleanJson)
  } catch (err) {
    parseError = err.message
  }

  if (parseError) {
    return (
      <div className="p-4 bg-slate-900/80 border border-red-500/20 rounded-xl my-4 text-xs">
        <div className="text-red-400 font-semibold mb-1">Visualization Parsing Error</div>
        <pre className="text-[10px] text-slate-500 overflow-x-auto whitespace-pre-wrap">{parseError}</pre>
      </div>
    )
  }

  switch (type) {
    case 'visualizer_chart':
      return <FunctionPlot data={parsedData} />
    case 'visualizer_flow':
      return <Flowchart data={parsedData} />
    case 'visualizer_dp':
      return <DPTable data={parsedData} />
    default:
      return (
        <div className="p-4 bg-slate-900 border border-white/5 rounded-xl my-4 text-xs text-slate-400 italic">
          Unsupported visual type: {type}
        </div>
      )
  }
}
