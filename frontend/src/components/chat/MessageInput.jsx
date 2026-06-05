import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function MessageInput({ onSend, onUploadPdf, disabled, initialText = '' }) {
  const [text, setText] = useState('')
  const [imageFile, setImageFile] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const fileRef = useRef(null)
  const pdfRef = useRef(null)
  const textareaRef = useRef(null)

  const handlePdfSelect = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('File must be a PDF document')
      return
    }
    if (onUploadPdf) {
      onUploadPdf(file)
    }
    if (pdfRef.current) pdfRef.current.value = ''
  }

  // Seed input if OCR page forwarded a question
  useEffect(() => {
    if (initialText) {
      setText(initialText)
      setTimeout(() => {
        const el = textareaRef.current
        if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 160) + 'px' }
      }, 50)
    }
  }, [initialText])

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return
    setImageFile(file)
    setImagePreview(URL.createObjectURL(file))
  }

  const removeImage = () => {
    setImageFile(null)
    setImagePreview(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const handleSend = useCallback(() => {
    if (disabled || (!text.trim() && !imageFile)) return
    onSend({ content: text.trim(), imageFile })
    setText('')
    removeImage()
  }, [text, imageFile, disabled, onSend])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Auto-resize textarea
  const handleTextChange = (e) => {
    setText(e.target.value)
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 160) + 'px'
    }
  }

  const canSend = (text.trim() || imageFile) && !disabled

  return (
    <div className="border-t border-white/10 bg-surface-800/80 backdrop-blur-md p-4">
      {/* Image preview */}
      <AnimatePresence>
        {imagePreview && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="mb-3 relative inline-block"
          >
            <img
              src={imagePreview}
              alt="Preview"
              className="h-24 rounded-xl border border-white/10 object-cover"
            />
            <button
              onClick={removeImage}
              className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-600 transition-colors"
              aria-label="Remove image"
            >
              ✕
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-end gap-3">
        {/* Image upload button */}
        <button
          id="image-upload-btn"
          type="button"
          onClick={() => fileRef.current?.click()}
          className="flex-shrink-0 w-10 h-10 bg-surface-700 hover:bg-surface-600 border border-white/10 rounded-xl flex items-center justify-center text-slate-400 hover:text-white transition-all"
          title="Upload image"
          disabled={disabled}
        >
          📷
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleImageSelect}
        />

        {/* PDF upload button */}
        <button
          id="pdf-upload-btn"
          type="button"
          onClick={() => pdfRef.current?.click()}
          className="flex-shrink-0 w-10 h-10 bg-surface-700 hover:bg-surface-600 border border-white/10 rounded-xl flex items-center justify-center text-slate-400 hover:text-white transition-all"
          title="Upload PDF notes"
          disabled={disabled}
        >
          📁
        </button>
        <input
          ref={pdfRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handlePdfSelect}
        />

        {/* Text input */}
        <div className="flex-1 bg-surface-700 border border-white/10 rounded-2xl flex items-end gap-2 px-4 py-3 focus-within:border-brand-500/50 focus-within:ring-2 focus-within:ring-brand-500/20 transition-all">
          <textarea
            ref={textareaRef}
            id="chat-input"
            className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 resize-none outline-none text-sm leading-relaxed min-h-[24px] max-h-40"
            placeholder="Ask about Physics, Chemistry, or Maths..."
            value={text}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={disabled}
          />
        </div>

        {/* Send button */}
        <button
          id="send-message-btn"
          onClick={handleSend}
          disabled={!canSend}
          className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 active:scale-90 ${
            canSend
              ? 'bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/30'
              : 'bg-surface-700 text-slate-600 border border-white/5 cursor-not-allowed'
          }`}
          aria-label="Send message"
        >
          {disabled ? (
            <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-4 h-4 rotate-90" fill="currentColor" viewBox="0 0 24 24">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          )}
        </button>
      </div>
      <p className="text-xs text-slate-600 mt-2 text-center">
        Press Enter to send · Shift+Enter for new line · Upload images of problems
      </p>
    </div>
  )
}
