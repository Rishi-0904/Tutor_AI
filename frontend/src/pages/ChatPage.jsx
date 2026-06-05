import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useChat } from '../hooks/useChat'
import ConversationList from '../components/chat/ConversationList'
import ChatWindow from '../components/chat/ChatWindow'
import MessageInput from '../components/chat/MessageInput'
import SubjectBadge from '../components/shared/SubjectBadge'
import WhiteboardDrawer from '../components/chat/WhiteboardDrawer'
import API from '../lib/api'
import toast from 'react-hot-toast'

export default function ChatPage() {
  const {
    conversations, messages, activeConversation, loading, sending,
    fetchConversations, startConversation, sendMessage, selectConversation,
  } = useChat()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [ocrPrefill, setOcrPrefill] = useState('')
  const [whiteboardOpen, setWhiteboardOpen] = useState(false)

  useEffect(() => {
    fetchConversations()
    // Pick up any question forwarded from the OCR page
    const prefill = sessionStorage.getItem('ocr_prefill')
    if (prefill) {
      setOcrPrefill(prefill)
      sessionStorage.removeItem('ocr_prefill')
    }
  }, [])

  const handleNewChat = async () => { await startConversation('general') }

  const handleSend = async ({ content, imageFile }) => {
    if (!activeConversation) {
      toast.error('Please start a new chat first.')
      return
    }
    await sendMessage({ conversationId: activeConversation.id, content, imageFile })
  }

  const handleUploadPdf = async (file) => {
    if (!activeConversation) return
    const formData = new FormData()
    formData.append('file', file)
    
    const loadingToast = toast.loading('Uploading and indexing PDF notes...')
    try {
      await API.post('/ocr/pdf/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      toast.dismiss(loadingToast)
      toast.success('PDF uploaded successfully! Indexing is running in background.')
    } catch (err) {
      toast.dismiss(loadingToast)
      toast.error('Failed to upload PDF notes')
      console.error(err)
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden h-full relative bg-slate-950">
      {/* Dynamic Background */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-900/20 via-slate-900 to-black z-0 pointer-events-none"></div>
      
      <motion.aside
        animate={{ width: sidebarOpen ? 280 : 0, opacity: sidebarOpen ? 1 : 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="relative z-10 glass-panel border-r border-white/5 flex-shrink-0 overflow-hidden bg-slate-950/40 backdrop-blur-xl"
      >
        <div className="w-[280px] h-full">
          <ConversationList
            conversations={conversations}
            activeId={activeConversation?.id}
            onSelect={selectConversation}
            onNew={handleNewChat}
            loading={loading && conversations.length === 0}
          />
        </div>
      </motion.aside>
      <div className="flex-1 flex flex-col overflow-hidden relative z-10 bg-slate-950/20">
        <div className="h-16 border-b border-white/5 bg-slate-900/30 backdrop-blur-md flex items-center px-6 gap-4 shadow-sm">
          <button onClick={() => setSidebarOpen((p) => !p)} className="text-slate-400 hover:text-white transition-colors p-2 rounded-lg hover:bg-white/5">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          {activeConversation ? (
            <>
              <p className="text-base font-medium truncate flex-1 text-slate-200 tracking-wide">{activeConversation.title}</p>
              <button 
                onClick={() => setWhiteboardOpen((p) => !p)}
                className="mr-2 px-3 py-1.5 bg-white/5 hover:bg-brand-500/20 border border-white/10 hover:border-brand-500/30 text-slate-300 hover:text-brand-300 text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-all duration-300 shadow-sm"
              >
                ✏️ Whiteboard
              </button>
              <SubjectBadge subject={activeConversation.subject} />
            </>
          ) : (
            <p className="text-sm italic text-slate-500">Start a new chat to begin your learning journey ✨</p>
          )}
        </div>
        <ChatWindow messages={messages} sending={sending} />
        <div className="bg-gradient-to-t from-slate-950 to-transparent pt-4 pb-0 mb-0">
          <MessageInput 
            onSend={handleSend} 
            onUploadPdf={handleUploadPdf} 
            disabled={sending || !activeConversation} 
          />
        </div>
      </div>
      <AnimatePresence>
        {whiteboardOpen && activeConversation && (
          <WhiteboardDrawer
            isOpen={whiteboardOpen}
            onClose={() => setWhiteboardOpen(false)}
            conversationId={activeConversation.id}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
