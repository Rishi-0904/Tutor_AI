import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import useAuthStore from '../../store/authStore'
import VisualizerContainer from '../visualizer/VisualizerContainer'

export default function MessageBubble({ message }) {
  const user = useAuthStore((s) => s.user)
  const isUser = message.role === 'user'

  const timeStr = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <div className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-semibold ${
          isUser
            ? 'bg-brand-500/30 border border-brand-500/40 text-brand-300'
            : 'bg-purple-500/20 border border-purple-500/30 text-purple-300'
        }`}
      >
        {isUser ? (user?.user_metadata?.full_name?.[0]?.toUpperCase() || 'U') : '🤖'}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        {/* Image attachment */}
        {message.image_url && (
          <img
            src={message.image_url}
            alt="Uploaded question"
            className="max-w-xs rounded-xl border border-white/10 object-contain bg-surface-700"
          />
        )}

        {/* Text content */}
        {message.content && (
          <div
            className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
              isUser
                ? 'bg-brand-500 text-white rounded-br-sm'
                : 'bg-surface-700 border border-white/10 text-slate-200 rounded-bl-sm'
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  code: ({ inline, className, children }) => {
                    const match = /language-(\w+)/.exec(className || '')
                    const lang = match ? match[1] : ''
                    if (!inline && ['visualizer_chart', 'visualizer_flow', 'visualizer_dp'].includes(lang)) {
                      return <VisualizerContainer type={lang} data={children} />
                    }
                    return inline ? (
                      <code className="bg-white/10 text-green-300 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
                    ) : (
                      <pre className="bg-surface-900 border border-white/10 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono text-slate-300">
                        <code>{children}</code>
                      </pre>
                    )
                  },
                  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>
        )}

        {/* Topic tags + timestamp */}
        <div className={`flex items-center gap-2 px-1 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          {message.topic_tags?.length > 0 && (
            <div className="flex gap-1">
              {message.topic_tags.slice(0, 3).map((tag) => (
                <span key={tag} className="text-xs bg-white/5 text-slate-500 px-1.5 py-0.5 rounded-full">
                  {tag}
                </span>
              ))}
            </div>
          )}
          {timeStr && <span className="text-xs text-slate-600">{timeStr}</span>}
        </div>
      </div>
    </div>
  )
}
