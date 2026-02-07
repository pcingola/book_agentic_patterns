import { HttpAgent, randomUUID } from '@ag-ui/client'
import type { Message, State } from '@ag-ui/core'
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

function getTextContent(msg: Message): string {
  if (typeof msg.content === 'string') return msg.content
  if (Array.isArray(msg.content)) {
    return msg.content.filter((c) => c.type === 'text').map((c) => c.text).join('')
  }
  return ''
}

interface ChatPanelProps {
  agent: HttpAgent
  backendUrl: string
  onStateChange: (state: State) => void
}

export function ChatPanel({ agent, backendUrl, onStateChange }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const [feedbackGiven, setFeedbackGiven] = useState<Record<string, string>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Reset messages when agent changes (backend URL changed)
  useEffect(() => {
    setMessages([])
  }, [agent])

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      setPendingFiles((prev) => [...prev, ...Array.from(e.target.files!)])
    }
    e.target.value = ''
  }

  function removeFile(index: number) {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index))
  }

  async function submitFeedback(messageId: string, feedbackType: string) {
    setFeedbackGiven((prev) => ({ ...prev, [messageId]: feedbackType }))
    try {
      await fetch(`${backendUrl}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback_type: feedbackType }),
      })
    } catch (err) {
      console.error('Feedback submission failed:', err)
    }
  }

  async function uploadFiles(files: File[]): Promise<string> {
    const parts: string[] = []
    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(`${backendUrl}/upload`, { method: 'POST', body: formData })
      if (res.ok) {
        const data = await res.json()
        parts.push(`[Uploaded file: ${data.workspace_path}]\n${data.summary}`)
      } else {
        parts.push(`[Upload failed: ${file.name}]`)
      }
    }
    return parts.join('\n\n')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if ((!text && pendingFiles.length === 0) || isRunning) return

    setIsRunning(true)

    let messageText = text
    if (pendingFiles.length > 0) {
      const fileContext = await uploadFiles(pendingFiles)
      messageText = fileContext + (text ? `\n\n${text}` : '')
      setPendingFiles([])
    }

    agent.addMessage({ id: randomUUID(), role: 'user', content: messageText })
    setMessages([...agent.messages])
    setInput('')

    try {
      await agent.runAgent({}, {
        onMessagesChanged({ messages }) {
          setMessages([...messages])
        },
        onStateChanged({ state }) {
          onStateChange(state)
        },
      })
    } catch (err) {
      console.error('Agent run failed:', err)
    } finally {
      setIsRunning(false)
    }
  }

  function renderAssistantContent(msg: Message) {
    const text = getTextContent(msg)
    const hasToolCalls = 'toolCalls' in msg && msg.toolCalls?.length

    return (
      <>
        {text && (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '')
                const codeString = String(children).replace(/\n$/, '')
                if (match) {
                  return (
                    <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div">
                      {codeString}
                    </SyntaxHighlighter>
                  )
                }
                return <code className={className} {...props}>{children}</code>
              },
            }}
          >
            {text}
          </ReactMarkdown>
        )}
        {hasToolCalls && msg.toolCalls!.map((tc) => (
          <div key={tc.id} className="tool-call">
            <span className="tool-name">{tc.function.name}</span>({tc.function.arguments})
          </div>
        ))}
      </>
    )
  }

  return (
    <div className="chat-panel">
      <div className="message-list">
        {messages.length === 0 && (
          <p className="empty-chat">How can I help you?</p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.role}`}>
            <div className="message-role">{msg.role}</div>
            <div className="message-content">
              {msg.role === 'assistant' ? renderAssistantContent(msg) : getTextContent(msg)}
            </div>
            {msg.role === 'assistant' && (
              <div className="feedback-buttons">
                <button
                  className={`feedback-btn${feedbackGiven[msg.id] === 'thumbs_up' ? ' active' : ''}`}
                  onClick={() => submitFeedback(msg.id, 'thumbs_up')}
                  disabled={!!feedbackGiven[msg.id]}
                  title="Thumbs up"
                >+1</button>
                <button
                  className={`feedback-btn${feedbackGiven[msg.id] === 'thumbs_down' ? ' active' : ''}`}
                  onClick={() => submitFeedback(msg.id, 'thumbs_down')}
                  disabled={!!feedbackGiven[msg.id]}
                  title="Thumbs down"
                >-1</button>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      {pendingFiles.length > 0 && (
        <div className="file-tags">
          {pendingFiles.map((file, i) => (
            <span key={i} className="file-tag">
              {file.name}
              <button type="button" onClick={() => removeFile(i)}>x</button>
            </span>
          ))}
        </div>
      )}
      <form className="input-bar" onSubmit={handleSubmit}>
        <input type="file" ref={fileInputRef} onChange={handleFileSelect} multiple hidden />
        <button type="button" className="attach-btn" onClick={() => fileInputRef.current?.click()} disabled={isRunning} title="Attach file">
          +
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={isRunning}
        />
        <button type="submit" disabled={isRunning || (!input.trim() && pendingFiles.length === 0)}>
          Send
        </button>
      </form>
    </div>
  )
}
