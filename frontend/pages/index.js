import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Square, Bot, User, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isDark, setIsDark] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const abortRef = useRef(null);

  // Dark mode detection
  useEffect(() => {
    const match = window.matchMedia("(prefers-color-scheme: dark)");
    setIsDark(match.matches);
    const handler = (e) => setIsDark(e.matches);
    match.addEventListener("change", handler);
    return () => match.removeEventListener("change", handler);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Send message handler
  const sendMessage = useCallback(async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage = { role: "user", text: input.trim() };
    const id = Date.now();
    
    setMessages((prev) => [
      ...prev,
      userMessage,
      { role: "bot", id, text: "", isStreaming: true }
    ]);
    setInput("");
    setIsStreaming(true);
    setError(null);

    abortRef.current = new AbortController();

    try {
      const res = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userMessage.text }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const data = await res.json();
      
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? { ...m, text: data.answer, sources: data.sources, isStreaming: false }
            : m
        )
      );
    } catch (err) {
      if (err.name === "AbortError") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === id
              ? { ...m, text: "Response generation stopped.", isStreaming: false }
              : m
          )
        );
      } else {
        console.error("Error:", err);
        setError("Unable to connect to server. Please try again.");
        setMessages((prev) =>
          prev.map((m) =>
            m.id === id
              ? {
                  ...m,
                  text: "I apologize, but I'm unable to connect to the server at the moment. Please check your connection and try again.",
                  isStreaming: false,
                  isError: true
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [input, isStreaming]);

  // Stop generation handler
  const stopGeneration = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      setIsStreaming(false);
    }
  };

  // Handle Enter key
  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Theme configuration
  const theme = {
    bg: isDark ? "#0f172a" : "#ffffff",
    surfaceBg: isDark ? "#1e293b" : "#f8fafc",
    chatBg: isDark ? "#0f172a" : "#ffffff",
    text: isDark ? "#f8fafc" : "#0f172a",
    textSecondary: isDark ? "#94a3b8" : "#64748b",
    userBg: isDark ? "#2563eb" : "#3b82f6",
    botBg: isDark ? "#1e293b" : "#ffffff",
    border: isDark ? "#334155" : "#e2e8f0",
    inputBg: isDark ? "#1e293b" : "#ffffff",
    accent: "#3b82f6",
    accentDark: "#2563eb",
    errorBg: isDark ? "#7f1d1d" : "#fee2e2",
    errorText: isDark ? "#fca5a5" : "#dc2626",
  };

  return (
    <div
      style={{
        background: theme.bg,
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: theme.surfaceBg,
          borderBottom: `1px solid ${theme.border}`,
          padding: "12px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "50%",
              background: `linear-gradient(135deg, ${theme.accent}, ${theme.accentDark})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Bot size={22} color="white" />
          </div>
          <div>
            <h1
              style={{
                margin: 0,
                fontSize: "18px",
                fontWeight: 600,
                color: theme.text,
              }}
            >
              VIT-AP University Assistant
            </h1>
            <p
              style={{
                margin: 0,
                fontSize: "13px",
                color: theme.textSecondary,
              }}
            >
              Powered by AI • Always here to help
            </p>
          </div>
        </div>
        <button
          onClick={() => setIsDark(!isDark)}
          style={{
            background: "transparent",
            border: `1px solid ${theme.border}`,
            borderRadius: "8px",
            padding: "8px 12px",
            color: theme.text,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "14px",
            transition: "all 0.2s",
          }}
        >
          {isDark ? "☀️ Light" : "🌙 Dark"}
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            background: theme.errorBg,
            color: theme.errorText,
            padding: "12px 24px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "14px",
          }}
        >
          <AlertCircle size={18} />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: "auto",
              background: "transparent",
              border: "none",
              color: theme.errorText,
              cursor: "pointer",
              fontSize: "18px",
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Chat Area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          background: theme.chatBg,
          padding: "24px",
          paddingBottom: "200px",
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              gap: "16px",
              color: theme.textSecondary,
            }}
          >
            <div
              style={{
                width: "80px",
                height: "80px",
                borderRadius: "50%",
                background: "linear-gradient(135deg, #3b82f6, #2563eb)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity: 0.9,
              }}
            >
              <Bot size={40} color="white" />
            </div>
            <h2
              style={{
                margin: 0,
                fontSize: "24px",
                fontWeight: 600,
                color: theme.text,
              }}
            >
              Welcome to VIT-AP Assistant
            </h2>
            <p
              style={{
                margin: 0,
                fontSize: "15px",
                textAlign: "center",
                maxWidth: "500px",
                lineHeight: "1.6",
              }}
            >
              Ask me anything about courses, admissions, fees, campus life, or university policies. 
                I am here to provide accurate information based on official documentation.
            </p>
          </div>
        ) : (
          <div style={{ maxWidth: "900px", margin: "0 auto" }}>
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: "16px",
                  marginBottom: "24px",
                  flexDirection: m.role === "user" ? "row-reverse" : "row",
                }}
              >
                {/* Avatar */}
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    background: m.role === "user" ? theme.userBg : theme.botBg,
                    border: m.role === "bot" ? `1px solid ${theme.border}` : "none",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  {m.role === "user" ? (
                    <User size={18} color="white" />
                  ) : (
                    <Bot size={18} color={isDark ? "#e5e5e5" : "#171717"} />
                  )}
                </div>

                {/* Message */}
                <div style={{ flex: 1, maxWidth: "75%" }}>
                  <div
                    style={{
                      background: m.role === "user" ? theme.userBg : theme.botBg,
                      color: m.role === "user" ? "white" : theme.text,
                      padding: "16px 20px",
                      borderRadius: "16px",
                      border: m.role === "bot" ? `1px solid ${theme.border}` : "none",
                      boxShadow:
                        m.role === "bot"
                          ? isDark
                            ? "0 2px 4px rgba(0,0,0,0.3)"
                            : "0 2px 8px rgba(0,0,0,0.05)"
                          : "0 2px 4px rgba(0,0,0,0.1)",
                    }}
                  >
                    {m.isStreaming && !m.text ? (
                      <div style={{ display: "flex", gap: "4px", padding: "4px 0" }}>
                        {[0, 0.2, 0.4].map((delay, idx) => (
                          <div
                            key={idx}
                            style={{
                              width: "8px",
                              height: "8px",
                              borderRadius: "50%",
                              background: theme.textSecondary,
                              animation: "pulse 1.4s infinite",
                              animationDelay: `${delay}s`,
                            }}
                          />
                        ))}
                      </div>
                    ) : (
                      <div
                        style={{
                          lineHeight: "1.7",
                          fontSize: "15px",
                        }}
                      >
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => (
                              <p style={{ margin: "0.75em 0", lineHeight: "1.7" }}>
                                {children}
                              </p>
                            ),
                            h1: ({ children }) => (
                              <h1
                                style={{
                                  fontSize: "1.5em",
                                  fontWeight: 600,
                                  margin: "1em 0 0.5em",
                                }}
                              >
                                {children}
                              </h1>
                            ),
                            h2: ({ children }) => (
                              <h2
                                style={{
                                  fontSize: "1.3em",
                                  fontWeight: 600,
                                  margin: "1em 0 0.5em",
                                }}
                              >
                                {children}
                              </h2>
                            ),
                            h3: ({ children }) => (
                              <h3
                                style={{
                                  fontSize: "1.1em",
                                  fontWeight: 600,
                                  margin: "1em 0 0.5em",
                                }}
                              >
                                {children}
                              </h3>
                            ),
                            ul: ({ children }) => (
                              <ul
                                style={{
                                  margin: "0.75em 0",
                                  paddingLeft: "1.5em",
                                  listStyle: "disc",
                                }}
                              >
                                {children}
                              </ul>
                            ),
                            ol: ({ children }) => (
                              <ol
                                style={{
                                  margin: "0.75em 0",
                                  paddingLeft: "1.5em",
                                  listStyle: "decimal",
                                }}
                              >
                                {children}
                              </ol>
                            ),
                            li: ({ children }) => (
                              <li
                                style={{
                                  margin: "0.5em 0",
                                  paddingLeft: "0.5em",
                                }}
                              >
                                {children}
                              </li>
                            ),
                            code: ({ inline, children }) =>
                              inline ? (
                                <code
                                  style={{
                                    background: isDark
                                      ? "rgba(255,255,255,0.1)"
                                      : "rgba(0,0,0,0.05)",
                                    padding: "0.2em 0.4em",
                                    borderRadius: "4px",
                                    fontSize: "0.9em",
                                    fontFamily:
                                      "Menlo, Monaco, Consolas, 'Courier New', monospace",
                                  }}
                                >
                                  {children}
                                </code>
                              ) : (
                                <pre
                                  style={{
                                    background: isDark
                                      ? "rgba(255,255,255,0.05)"
                                      : "rgba(0,0,0,0.03)",
                                    padding: "1em",
                                    borderRadius: "8px",
                                    overflow: "auto",
                                    margin: "1em 0",
                                  }}
                                >
                                  <code
                                    style={{
                                      fontFamily:
                                        "Menlo, Monaco, Consolas, 'Courier New', monospace",
                                      fontSize: "0.9em",
                                    }}
                                  >
                                    {children}
                                  </code>
                                </pre>
                              ),
                            table: ({ children }) => (
                              <div style={{ overflowX: "auto", margin: "1em 0" }}>
                                <table
                                  style={{
                                    borderCollapse: "collapse",
                                    width: "100%",
                                    fontSize: "14px",
                                  }}
                                >
                                  {children}
                                </table>
                              </div>
                            ),
                            th: ({ children }) => (
                              <th
                                style={{
                                  border: `1px solid ${theme.border}`,
                                  padding: "10px 12px",
                                  background: isDark
                                    ? "rgba(255,255,255,0.05)"
                                    : "rgba(0,0,0,0.03)",
                                  fontWeight: 600,
                                  textAlign: "left",
                                }}
                              >
                                {children}
                              </th>
                            ),
                            td: ({ children }) => (
                              <td
                                style={{
                                  border: `1px solid ${theme.border}`,
                                  padding: "10px 12px",
                                }}
                              >
                                {children}
                              </td>
                            ),
                            strong: ({ children }) => (
                              <strong style={{ fontWeight: 600 }}>{children}</strong>
                            ),
                            a: ({ href, children }) => (
                              <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                  color: theme.accent,
                                  textDecoration: "none",
                                  fontWeight: 500,
                                }}
                              >
                                {children}
                              </a>
                            ),
                          }}
                        >
                          {m.text}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {/* Sources Display */}
                  {m.sources && m.sources.length > 0 && (
                    <div
                      style={{
                        marginTop: "8px",
                        fontSize: "12px",
                        color: theme.textSecondary,
                        paddingLeft: "12px",
                      }}
                    >
                      <details>
                        <summary style={{ cursor: "pointer", userSelect: "none" }}>
                          📚 Sources ({m.sources.length})
                        </summary>
                        <ul style={{ marginTop: "8px", paddingLeft: "20px" }}>
                          {m.sources.map((src, idx) => (
                            <li key={idx} style={{ marginBottom: "4px" }}>
                              {src.source} (relevance: {(src.score * 100).toFixed(1)}%)
                            </li>
                          ))}
                        </ul>
                      </details>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div
        style={{
          background: theme.surfaceBg,
          borderTop: `1px solid ${theme.border}`,
          padding: "16px 24px",
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          boxShadow: isDark
            ? "0 -10px 20px rgba(0,0,0,0.2)"
            : "0 -10px 20px rgba(0,0,0,0.05)",
        }}
      >
        <div
          style={{
            maxWidth: "900px",
            margin: "0 auto",
            width: "100%",
          }}
        >
          {/* Input Row */}
          <div
            style={{
              display: "flex",
              gap: "12px",
              alignItems: "flex-end",
              marginBottom: "12px",
            }}
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about courses, fees, admissions..."
              rows={1}
              disabled={isStreaming}
              style={{
                flex: 1,
                padding: "12px 16px",
                borderRadius: "12px",
                border: `1px solid ${theme.border}`,
                background: theme.inputBg,
                color: theme.text,
                fontSize: "15px",
                resize: "none",
                fontFamily: "inherit",
                outline: "none",
                maxHeight: "120px",
                minHeight: "48px",
                opacity: isStreaming ? 0.6 : 1,
              }}
              onInput={(e) => {
                e.target.style.height = "48px";
                e.target.style.height = e.target.scrollHeight + "px";
              }}
            />
            {isStreaming ? (
              <button
                onClick={stopGeneration}
                style={{
                  background: "#ef4444",
                  color: "white",
                  border: "none",
                  borderRadius: "12px",
                  padding: "12px 20px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontSize: "15px",
                  fontWeight: 500,
                  minHeight: "48px",
                  transition: "all 0.2s",
                }}
              >
                <Square size={18} />
                Stop
              </button>
            ) : (
              <button
                onClick={sendMessage}
                disabled={!input.trim()}
                style={{
                  background: input.trim()
                    ? "linear-gradient(135deg, #3b82f6, #2563eb)"
                    : theme.border,
                  color: "white",
                  border: "none",
                  borderRadius: "12px",
                  padding: "12px 20px",
                  cursor: input.trim() ? "pointer" : "not-allowed",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontSize: "15px",
                  fontWeight: 500,
                  minHeight: "48px",
                  transition: "all 0.2s",
                  opacity: input.trim() ? 1 : 0.5,
                }}
              >
                <Send size={18} />
                Send
              </button>
            )}
          </div>

          {/* Disclaimer */}
          <div
            style={{
              padding: "8px 12px",
              borderRadius: "8px",
              fontSize: "13px",
              color: theme.textSecondary,
              background: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
              border: `1px solid ${theme.border}`,
              textAlign: "center",
            }}
          >
            <p style={{ margin: 0 }}>
              For the most current information, please visit{" "}
              <a
                href="https://vitap.ac.in/"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: theme.accent,
                  textDecoration: "none",
                  fontWeight: 500,
                  transition: "color 0.2s",
                }}
                onMouseEnter={(e) => (e.target.style.color = theme.accentDark)}
                onMouseLeave={(e) => (e.target.style.color = theme.accent)}
              >
                vitap.ac.in
              </a>
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
