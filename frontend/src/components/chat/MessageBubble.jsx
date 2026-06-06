import { memo, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import useAuthStore from '../../store/authStore'
import VisualizerContainer from '../visualizer/VisualizerContainer'

// Streaming cursor — blinks while AI is still generating
const StreamingCursor = () => (
  <span
    aria-hidden="true"
    style={{
      display: 'inline-block',
      width: '2px',
      height: '1em',
      background: 'currentColor',
      marginLeft: '2px',
      verticalAlign: 'text-bottom',
      borderRadius: '1px',
      animation: 'blink-cursor 0.8s step-end infinite',
    }}
  />
)

// Custom code block — handles visualizer fences separately
const CodeBlock = ({ inline, className, children }) => {
  const match = /language-(\w+)/.exec(className || '')
  const lang = match ? match[1] : ''

  if (!inline && ['visualizer_chart', 'visualizer_flow', 'visualizer_dp'].includes(lang)) {
    return <VisualizerContainer type={lang} data={children} />
  }

  if (inline) {
    return (
      <code className="bg-white/10 text-emerald-300 px-1.5 py-0.5 rounded text-xs font-mono">
        {children}
      </code>
    )
  }

  return (
    <pre className="bg-black/30 border border-white/10 rounded-xl p-4 my-3 overflow-x-auto text-xs font-mono text-slate-300 leading-relaxed">
      <code>{children}</code>
    </pre>
  )
}

// Memoised markdown body — only re-renders when content actually changes
const MarkdownBody = memo(({ content, isStreaming }) => (
  <ReactMarkdown
    remarkPlugins={[remarkMath]}
    rehypePlugins={[rehypeKatex]}
    components={{
      p: ({ children }) => (
        <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
      ),
      code: CodeBlock,
      strong: ({ children }) => (
        <strong className="font-semibold text-white">{children}</strong>
      ),
      em: ({ children }) => (
        <em className="text-slate-300 italic">{children}</em>
      ),
      h1: ({ children }) => (
        <h1 className="text-lg font-bold text-white mt-4 mb-2">{children}</h1>
      ),
      h2: ({ children }) => (
        <h2 className="text-base font-bold text-white mt-3 mb-1.5">{children}</h2>
      ),
      h3: ({ children }) => (
        <h3 className="text-sm font-semibold text-slate-200 mt-2 mb-1">{children}</h3>
      ),
      ul: ({ children }) => (
        <ul className="list-disc list-inside space-y-1 my-2 text-slate-300">{children}</ul>
      ),
      ol: ({ children }) => (
        <ol className="list-decimal list-inside space-y-1 my-2 text-slate-300">{children}</ol>
      ),
      blockquote: ({ children }) => (
        <blockquote className="border-l-2 border-indigo-500/50 pl-4 my-3 text-slate-400 italic">
          {children}
        </blockquote>
      ),
      hr: () => <hr className="border-white/10 my-4" />,
      table: ({ children }) => (
        <div className="overflow-x-auto my-3">
          <table className="w-full text-xs border-collapse">{children}</table>
        </div>
      ),
      th: ({ children }) => (
        <th className="border border-white/10 px-3 py-1.5 bg-white/5 text-left font-semibold text-slate-200">
          {children}
        </th>
      ),
      td: ({ children }) => (
        <td className="border border-white/10 px-3 py-1.5 text-slate-300">{children}</td>
      ),
    }}
  >
    {content}
  </ReactMarkdown>
))
MarkdownBody.displayName = 'MarkdownBody'

export default function MessageBubble({ message }) {
  const user = useAuthStore((s) => s.user)
  const isUser = message.role === 'user'
  const isStreaming = message.streaming === true
  const bubbleRef = useRef(null)

  const timeStr = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  // Auto-scroll to keep the bottom of this bubble visible while streaming
  useEffect(() => {
    if (isStreaming && bubbleRef.current) {
      bubbleRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [message.content, isStreaming])

  return (
    <div
      ref={bubbleRef}
      className={`flex items-end gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div
        className={`w-9 h-9 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-semibold shadow-lg ${
          isUser
            ? 'bg-gradient-to-tr from-indigo-500/40 to-purple-500/40 border border-indigo-400/40 text-indigo-200'
            : 'bg-gradient-to-tr from-violet-500/20 to-purple-500/20 border border-purple-400/30 text-purple-200'
        }`}
      >
        {isUser ? (user?.user_metadata?.full_name?.[0]?.toUpperCase() || 'U') : '✦'}
      </div>

      {/* Bubble */}
      <div className={`max-w-[78%] flex flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Image attachment */}
        {message.image_url && (
          <img
            src={message.image_url}
            alt="Uploaded question"
            className="max-w-xs rounded-2xl border border-white/10 object-contain bg-surface-700 shadow-lg"
          />
        )}

        {/* Text content */}
        {(message.content || isStreaming) && (
          <div
            className={`px-5 py-3.5 rounded-2xl text-sm leading-relaxed shadow-lg transition-shadow ${
              isUser
                ? 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-br-sm'
                : [
                    'bg-surface-800/70 backdrop-blur-md',
                    'border border-white/8 text-slate-200 rounded-bl-sm',
                    isStreaming ? 'border-indigo-500/30 shadow-[0_0_16px_rgba(99,102,241,0.12)]' : '',
                  ].join(' ')
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : message.content ? (
              <>
                <MarkdownBody content={message.content} isStreaming={isStreaming} />
                {isStreaming && <StreamingCursor />}
              </>
            ) : (
              // Empty content but streaming = waiting for first token
              <div className="flex gap-1.5 items-center h-4">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Topic tags + timestamp */}
        <div className={`flex items-center gap-2 px-1 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          {!isStreaming && message.topic_tags?.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {message.topic_tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded-full font-medium"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
          {timeStr && !isStreaming && (
            <span className="text-[10px] text-slate-600">{timeStr}</span>
          )}
          {isStreaming && (
            <span className="text-[10px] text-indigo-500/60 animate-pulse">generating…</span>
          )}
        </div>
      </div>
    </div>
  )
}
