import { useState, useCallback, useRef } from 'react'
import API from '../lib/api'
import toast from 'react-hot-toast'
import { supabase } from '../lib/supabaseClient'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useChat() {
  const [conversations, setConversations] = useState([])
  const [messages, setMessages] = useState([])
  const [activeConversation, setActiveConversation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  // Tracks whether the current AI message is still streaming
  const [streaming, setStreaming] = useState(false)

  const fetchConversations = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await API.get('/conversations')
      setConversations(data)
    } catch (err) {
      toast.error('Failed to load conversations')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchMessages = useCallback(async (conversationId) => {
    setLoading(true)
    try {
      const { data } = await API.get(`/conversations/${conversationId}/messages`)
      setMessages(data)
    } catch (err) {
      toast.error('Failed to load messages')
    } finally {
      setLoading(false)
    }
  }, [])

  const startConversation = useCallback(async (subject = 'general') => {
    try {
      const formData = new FormData()
      formData.append('subject', subject)
      const { data } = await API.post('/conversations', formData)
      setActiveConversation(data)
      setConversations((prev) => [data, ...prev])
      setMessages([])
      return data
    } catch (err) {
      toast.error('Failed to create conversation')
    }
  }, [])

  const sendMessage = useCallback(async ({ conversationId, content, imageFile }) => {
    setSending(true)
    setStreaming(true)

    const tempUserId = `${Date.now()}_u`
    const tempAiId   = `${Date.now()}_ai`
    const userMsg = { id: tempUserId, role: 'user', content }
    const aiMsg   = { id: tempAiId,   role: 'assistant', content: '', streaming: true, agentSteps: [] }

    setMessages((prev) => [...prev, userMsg, aiMsg])

    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token

      const formData = new FormData()
      formData.append('content', content || '')
      formData.append('conversationId', conversationId)
      if (imageFile) formData.append('image', imageFile)

      const response = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })

      if (!response.ok) {
        const errText = await response.text()
        throw new Error(errText || 'Stream request failed')
      }

      const reader  = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer    = ''
      let aiContent = ''
      let agentSteps = []

      // Read stream until [DONE]
      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete SSE lines from the buffer
        const lines = buffer.split('\n')
        // Keep the last (possibly incomplete) line in the buffer
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') break
          try {
            const parsed = JSON.parse(payload)
            
            // Handle agent status events
            if (parsed.type === 'agent_status' && parsed.data) {
              const { agent, label, status } = parsed.data
              
              // Update or add agent step
              const existingIdx = agentSteps.findIndex(s => s.agent === agent && s.status === 'running')
              if (status === 'done' && existingIdx >= 0) {
                agentSteps[existingIdx] = { ...agentSteps[existingIdx], status: 'done' }
              } else if (status === 'running') {
                agentSteps = [...agentSteps, { agent, label, status: 'running' }]
              }
              
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === tempAiId
                    ? { ...m, agentSteps: [...agentSteps] }
                    : m
                )
              )
            }
            // Handle content events
            else if (parsed.content) {
              aiContent += parsed.content
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === tempAiId
                    ? { ...m, content: aiContent, streaming: true }
                    : m
                )
              )
            }
          } catch { /* ignore malformed chunks */ }
        }
      }

      // Mark streaming finished on the AI message
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempAiId ? { ...m, streaming: false } : m
        )
      )

      // Refresh from DB in background to get real IDs + topic_tags
      setTimeout(() => fetchMessages(conversationId), 800)
    } catch (err) {
      toast.error('Failed to send message')
      console.error('[useChat] stream error:', err)
      setMessages((prev) => prev.filter((m) => m.id !== tempAiId))
    } finally {
      setSending(false)
      setStreaming(false)
    }
  }, [fetchMessages])

  const selectConversation = useCallback(async (conv) => {
    setActiveConversation(conv)
    await fetchMessages(conv.id)
  }, [fetchMessages])

  return {
    conversations,
    messages,
    activeConversation,
    loading,
    sending,
    streaming,
    fetchConversations,
    startConversation,
    sendMessage,
    selectConversation,
  }
}
