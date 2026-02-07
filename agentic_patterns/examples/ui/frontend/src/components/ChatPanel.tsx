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
  onStateChange: (state: State) => void
}

export function ChatPanel({ agent, onStateChange }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Reset messages when agent changes (backend URL changed)
  useEffect(() => {
    setMessages([])
  }, [agent])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || isRunning) return

    setIsRunning(true)
    agent.addMessage({ id: randomUUID(), role: 'user', content: text })
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
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <form className="input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={isRunning}
        />
        <button type="submit" disabled={isRunning || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
