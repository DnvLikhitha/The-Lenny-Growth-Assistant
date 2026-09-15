import React, { useState, useEffect, useRef } from 'react';

function parseMarkdownToHTML(markdown) {
  if (!markdown) return '';
  let html = markdown;
  html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  html = html.replace(/^### (.*$)/gim, '<h3 style="margin-top:16px; margin-bottom:8px; font-size:16px;">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 style="margin-top:20px; margin-bottom:10px; font-size:18px; border-bottom:1px solid #475569; padding-bottom:4px;">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 style="margin-top:24px; margin-bottom:12px; font-size:22px;">$1</h1>');
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
  html = html.replace(/^\s*\-\s+(.*$)/gim, '<li style="margin-left:20px;">$1</li>');
  html = html.replace(/\n\n/gim, '<br/><br/>');
  return html;
}

const API_BASE = "http://localhost:8001";

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [config, setConfig] = useState({ active_provider: "ollama", active_model: "llama3.1:8b" });
  const [artifact, setArtifact] = useState(null);
  const [artifactMode, setArtifactMode] = useState("rendered"); // rendered | raw
  const [status, setStatus] = useState("idle"); // idle | retrieving | streaming | generating
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchConfig();
    fetchSessions();
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      loadSession(activeSessionId);
    }
  }, [activeSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/config`);
      const data = await res.json();
      if (data.data) setConfig(data.data);
    } catch (e) {
      console.error("Failed to fetch config", e);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`);
      const data = await res.json();
      if (data.data) {
        setSessions(data.data);
        if (data.data.length > 0 && !activeSessionId) {
          setActiveSessionId(data.data[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to fetch sessions", e);
    }
  };

  const createNewSession = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: "New Chat" })
      });
      const data = await res.json();
      if (data.data) {
        setSessions([data.data, ...sessions]);
        setActiveSessionId(data.data.id);
        setMessages([]);
        setArtifact(null);
      }
    } catch (e) {
      console.error("Failed to create session", e);
    }
  };

  const loadSession = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${id}`);
      const data = await res.json();
      if (data.data) {
        setMessages(data.data.messages || []);
      }
    } catch (e) {
      console.error("Failed to load session", e);
    }
  };

  const handleSend = async (intent = "answer_question") => {
    if (!input.trim() || !activeSessionId) return;

    const userText = input;
    setInput("");
    setStatus("retrieving");

    // Append temporary user message
    const tempUserMsg = { id: Date.now().toString(), role: "user", content: userText };
    const tempAsstMsg = { id: (Date.now() + 1).toString(), role: "assistant", content: "", citations: [] };
    
    setMessages(prev => [...prev, tempUserMsg, tempAsstMsg]);

    try {
      if (intent === "write_ship30_essay") {
        setStatus("generating");
        const artRes = await fetch(`${API_BASE}/sessions/${activeSessionId}/artifacts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kind: "markdown", prompt: userText })
        });
        const artData = await artRes.json();
        if (artData.data) {
          setArtifact(artData.data);
          setStatus("idle");
          // Remove temp dummy assistant message and keep user message
          setMessages(prev => prev.filter(m => m.id !== tempAsstMsg.id));
        } else if (artData.error) {
          setStatus("idle");
          console.error("Artifact generation error:", artData.error);
        }
        fetchSessions();
        return;
      }

      // Standard SSE streaming chat
      const response = await fetch(`${API_BASE}/sessions/${activeSessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: userText, intent: intent })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (let line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.replace('data: ', ''));
              if (eventData.type === "retrieval") {
                setStatus("streaming");
                setMessages(prev => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  last.citations = eventData.chunks || [];
                  return updated;
                });
              } else if (eventData.type === "content") {
                assistantText += eventData.delta;
                setMessages(prev => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  last.content = assistantText;
                  return updated;
                });
              }
            } catch (err) {
              // Ignore non-json frame ends
            }
          }
        }
      }
      setStatus("idle");
      fetchSessions(); // Refresh list to get updated titles
    } catch (e) {
      console.error("Error during send", e);
      setStatus("idle");
    }
  };

  return (
    <div className="app-container">
      {/* 1. Session Rail */}
      <aside className="session-rail" aria-label="Session Navigation">
        <h2 style={{ fontSize: '18px', marginBottom: '16px' }}>Lenny Assistant</h2>
        <button className="send-btn" onClick={createNewSession} style={{ marginBottom: '20px', width: '100%', height: '40px' }}>
          + New Session
        </button>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto' }}>
          {sessions.map(s => (
            <div
              key={s.id}
              onClick={() => setActiveSessionId(s.id)}
              style={{
                padding: '10px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                backgroundColor: s.id === activeSessionId ? 'var(--bg-card)' : 'transparent',
                border: s.id === activeSessionId ? '1px solid var(--accent-color)' : '1px solid transparent'
              }}
            >
              <div style={{ fontWeight: '500', fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {s.title}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                {new Date(s.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* 2. Chat Zone */}
      <main className="chat-zone">
        <header className="header">
          <h3>Conversation</h3>
          <div className="provider-badge" aria-live="polite">
            Provider: {config.active_provider} ({config.active_model})
          </div>
        </header>

        <div className="messages-container" aria-live="polite">
          {messages.map((m, idx) => (
            <div key={m.id || idx} className={`message-bubble ${m.role}`}>
              <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
              
              {/* Citations List */}
              {m.citations && m.citations.length > 0 && (
                <div className="citations-list" aria-label="Citations">
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)', width: '100%' }}>Sources:</span>
                  {m.citations.map((c, cIdx) => (
                    <button key={cIdx} className="citation-chip" title={c.source_path}>
                      📍 {c.guest_name || 'Guest'} - {c.episode_title || 'Episode'} ({c.approx_timestamp || '00:00'})
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {status !== "idle" && (
            <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '13px' }}>
              {status === "retrieving" && "🔍 Retrieving transcript context..."}
              {status === "streaming" && "⚡ Generating grounded response..."}
              {status === "generating" && "📝 Writing Ship 30 essay artifact..."}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Controls */}
        <div className="input-area">
          <input
            type="text"
            className="chat-input"
            placeholder="Ask a product/growth question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend("answer_question")}
          />
          <button className="send-btn" onClick={() => handleSend("answer_question")}>Send</button>
          <button className="send-btn" style={{ backgroundColor: '#059669' }} onClick={() => handleSend("write_ship30_essay")}>
            Ship 30 Essay
          </button>
        </div>
      </main>

      {/* 3. Artifact Viewer */}
      {artifact && (
        <aside className="artifact-zone" aria-label="Artifact Viewer">
          <header className="header" style={{ justifyContent: 'space-between' }}>
            <h4 style={{ fontSize: '14px' }}>Artifact Viewer ({artifact.kind})</h4>
            <div>
              <button 
                style={{ padding: '4px 8px', fontSize: '12px', marginRight: '6px' }}
                onClick={() => setArtifactMode(artifactMode === "rendered" ? "raw" : "rendered")}
              >
                {artifactMode === "rendered" ? "View Raw" : "View Rendered"}
              </button>
              <button 
                style={{ padding: '4px 8px', fontSize: '12px' }}
                onClick={() => setArtifact(null)}
              >
                ✕
              </button>
            </div>
          </header>
          
          <div style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', fontSize: '12px', color: 'var(--text-secondary)' }}>
            Word Count: {artifact.word_count} | Structure Valid: {artifact.structure_valid ? "✅ PASS" : "❌ FAIL"}
          </div>

          <div style={{ flex: 1, padding: '12px', overflowY: 'auto' }}>
            {artifactMode === "raw" ? (
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '12px' }}>{artifact.content}</pre>
            ) : artifact.kind === "html" ? (
              <iframe
                title="Sandboxed Artifact Preview"
                className="artifact-iframe"
                sandbox="allow-same-origin"
                srcDoc={artifact.content}
              />
            ) : (
              <div 
                style={{ lineHeight: '1.6', fontSize: '14px' }}
                dangerouslySetInnerHTML={{ __html: parseMarkdownToHTML(artifact.content) }}
              />
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
