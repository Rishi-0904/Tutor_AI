import React from 'react'
import ReactFlow, { Controls, Background } from 'reactflow'
import 'reactflow/dist/style.css'

export default function Flowchart({ data }) {
  const { title, nodes = [], edges = [] } = data

  if (nodes.length === 0) {
    return (
      <div className="p-4 bg-slate-900 border border-white/10 rounded-xl text-slate-400 text-xs text-center">
        Empty diagram structure.
      </div>
    )
  }

  // Frontend Auto-Layout: Group nodes by level to position them vertically and horizontally
  const levels = {}
  nodes.forEach((node) => {
    const lvl = node.level !== undefined ? node.level : 0
    if (!levels[lvl]) levels[lvl] = []
    levels[lvl].push(node)
  })

  const reactFlowNodes = []
  const canvasWidth = 600
  const rowHeight = 110

  Object.keys(levels).forEach((lvlStr) => {
    const lvl = parseInt(lvlStr, 10)
    const rowNodes = levels[lvl]
    const rowCount = rowNodes.length

    rowNodes.forEach((node, idx) => {
      // Position nodes: center each row horizontally
      // Spacing nodes 200px apart horizontally, centering around (canvasWidth / 2)
      const horizontalSpacing = 180
      const x = (canvasWidth / 2) + (idx - (rowCount - 1) / 2) * horizontalSpacing - 75 // shift half node width (75px)
      const y = 30 + lvl * rowHeight

      reactFlowNodes.push({
        id: node.id,
        data: {
          label: (
            <div className="px-3 py-2 text-left bg-slate-900/90 hover:bg-slate-950 border border-indigo-500/30 hover:border-indigo-400 rounded-xl shadow-[0_4px_20px_rgba(99,102,241,0.15)] text-slate-200 backdrop-blur-md transition-all duration-300">
              <div className="font-semibold text-xs text-brand-300 border-b border-white/5 pb-1 mb-1 truncate">
                {node.label}
              </div>
              {node.description && (
                <div className="text-[9px] leading-snug text-slate-400 max-h-16 overflow-y-auto">
                  {node.description}
                </div>
              )}
            </div>
          )
        },
        position: { x, y },
        type: 'default',
        style: {
          background: 'none',
          border: 'none',
          padding: 0,
          width: 150
        }
      })
    })
  })

  // Format edges to look beautiful with glowing arrows and smooth curves
  const reactFlowEdges = edges.map((edge) => ({
    id: edge.id || `e-${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    label: edge.label || '',
    animated: true,
    style: { stroke: '#818cf8', strokeWidth: 1.5 },
    labelStyle: { fill: '#a78bfa', fontSize: 9, fontWeight: 500, fillOpacity: 0.8 },
    labelBgPadding: [4, 2],
    labelBgBorderRadius: 4,
    labelBgStyle: { fill: '#0f172a', fillOpacity: 0.85, stroke: 'rgba(255,255,255,0.05)' }
  }))

  return (
    <div className="my-4 bg-slate-900/40 border border-white/10 rounded-2xl overflow-hidden shadow-2xl relative">
      <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/5 to-purple-500/5 pointer-events-none z-10"></div>
      
      {/* Title Header */}
      <div className="px-5 py-3 border-b border-white/5 bg-slate-900/70 backdrop-blur-md flex justify-between items-center relative z-20">
        <h4 className="text-sm font-semibold text-slate-200 truncate pr-4">
          🗺️ Concept Flow: <span className="text-indigo-300 font-medium">{title}</span>
        </h4>
        <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-500/30 flex-shrink-0">
          Flowchart
        </span>
      </div>

      {/* React Flow Viewport Container */}
      <div className="h-[280px] w-full relative z-20">
        <ReactFlow
          nodes={reactFlowNodes}
          edges={reactFlowEdges}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.5}
          maxZoom={1.5}
          nodesConnectable={false}
          nodesDraggable={true}
          className="bg-slate-950/10"
        >
          <Background color="rgba(255,255,255,0.08)" gap={16} size={1} />
          <Controls 
            className="react-flow-controls border border-white/10 bg-slate-900 rounded-lg overflow-hidden shadow-2xl" 
            showInteractive={false}
          />
        </ReactFlow>
      </div>

      <div className="px-5 py-2.5 bg-slate-950/20 border-t border-white/5 text-[10px] text-slate-500 italic relative z-20">
        💡 Drag nodes to rearrange the map. Zoom using mouse wheel or control pad.
      </div>
    </div>
  )
}
