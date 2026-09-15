import React, { useState, useEffect, useRef } from 'react';

function parseMarkdownToHTML(markdown) {
  if (!markdown) return '';
  let html = markdown;
  html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  html = html.replace(/^### (.*$)/gim, '<h3 style="margin-top:16px; margin-bottom:8px; font-size:16px; font-weight:700; color:#0f172a;">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 style="margin-top:20px; margin-bottom:10px; font-size:18px; font-weight:800; color:#0f172a; border-bottom:1px solid #e2e8f0; padding-bottom:6px;">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 style="margin-top:24px; margin-bottom:12px; font-size:22px; font-weight:800; color:#0f172a;">$1</h1>');
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong style="color:#0f172a;">$1</strong>');
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
  html = html.replace(/^\s*\-\s+(.*$)/gim, '<li style="margin-left:20px; margin-bottom:4px; color:#334155;">$1</li>');
  html = html.replace(/\n\n/gim, '<br/><br/>');
  return html;
}

const API_BASE = "http://localhost:8001";

const SUGGESTED_PROMPTS = [
  {
    title: "User Activation Levers",
    query: "How should top PMs think about user activation in PLG products?",
    desc: "Key tactics for driving early user value"
  },
  {
    title: "SaaS Pricing & Packaging",
    query: "What advice do guests give about pricing and packaging SaaS products?",
    desc: "Pricing models from growth leaders"
  },
  {
    title: "Product-Market Fit",
    query: "How do you determine product-market fit according to Lenny's guests?",
    desc: "Metrics and signals for PMF"
  },
  {
    title: "Early PM Hiring",
    query: "What are effective strategies for hiring early product managers?",
    desc: "Interviewing & evaluation techniques"
  }
];

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [config, setConfig] = useState({ active_provider: "ollama", active_model: "llama3.2:3b" });
  const [artifact, setArtifact] = useState(null);
  const [artifactMode, setArtifactMode] = useState("rendered"); // rendered | raw
  const [status, setStatus] = useState("idle"); // idle | retrieving | streaming | generating
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
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
  }, [messages, status]);

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

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.data?.deleted) {
        const remaining = sessions.filter(s => s.id !== sessionId);
        setSessions(remaining);
        if (activeSessionId === sessionId) {
          if (remaining.length > 0) {
            setActiveSessionId(remaining[0].id);
          } else {
            setActiveSessionId(null);
            setMessages([]);
            setArtifact(null);
          }
        }
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  const handleStartRename = (e, session) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditingTitle(session.title);
  };

  const handleSaveRename = async (sessionId) => {
    if (!editingTitle.trim()) {
      setEditingSessionId(null);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editingTitle })
      });
      const data = await res.json();
      if (data.data?.updated) {
        setSessions(sessions.map(s => s.id === sessionId ? { ...s, title: editingTitle } : s));
      }
    } catch (err) {
      console.error("Failed to rename session", err);
    } finally {
      setEditingSessionId(null);
    }
  };

  const handleSend = async (intent = "answer_question", customPrompt = null) => {
    const textToSend = customPrompt || input;
    if (!textToSend.trim() || !activeSessionId) return;

    if (!customPrompt) setInput("");
    setStatus("retrieving");

    const tempUserMsg = { id: Date.now().toString(), role: "user", content: textToSend };
    const tempAsstMsg = { id: (Date.now() + 1).toString(), role: "assistant", content: "", citations: [] };
    
    setMessages(prev => [...prev, tempUserMsg, tempAsstMsg]);

    try {
      if (intent === "write_ship30_essay") {
        setStatus("generating");
        const artRes = await fetch(`${API_BASE}/sessions/${activeSessionId}/artifacts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kind: "markdown", prompt: textToSend })
        });
        const artData = await artRes.json();
        if (artData.data) {
          setArtifact(artData.data);
          setStatus("idle");
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
        body: JSON.stringify({ content: textToSend, intent: intent })
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
      fetchSessions();
    } catch (e) {
      console.error("Error during send", e);
      setStatus("idle");
    }
  };

  return (
    <div className="app-container">
      {/* 1. Clean Session Rail */}
      <aside className="session-rail" aria-label="Session Navigation">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div className="brand-icon">L</div>
          <div>
            <div style={{ fontWeight: '800', fontSize: '15px', color: '#0f172a' }}>Lenny Growth</div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: '500' }}>AI Knowledge Assistant</div>
          </div>
        </div>

        <button className="new-session-btn" onClick={createNewSession} style={{ marginBottom: '20px' }}>
          <span>+</span> New Chat Session
        </button>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', overflowY: 'auto', flex: 1 }}>
          <div style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: '4px', paddingLeft: '4px' }}>
            Chat History
          </div>
          {sessions.map(s => (
            <div
              key={s.id}
              className={`session-item ${s.id === activeSessionId ? 'active' : ''}`}
              onClick={() => setActiveSessionId(s.id)}
            >
              <div className="session-item-header">
                {editingSessionId === s.id ? (
                  <input
                    type="text"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveRename(s.id);
                      if (e.key === 'Escape') setEditingSessionId(null);
                    }}
                    onBlur={() => handleSaveRename(s.id)}
                    autoFocus
                    style={{ fontSize: '13px', width: '100%', padding: '2px 4px', border: '1px solid #2563eb', borderRadius: '4px' }}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="session-item-title">{s.title}</div>
                )}

                {editingSessionId !== s.id && (
                  <div className="session-actions">
                    <button
                      className="session-action-btn"
                      title="Rename Session"
                      onClick={(e) => handleStartRename(e, s)}
                    >
                      ✏️
                    </button>
                    <button
                      className="session-action-btn delete"
                      title="Delete Session"
                      onClick={(e) => handleDeleteSession(e, s.id)}
                    >
                      🗑️
                    </button>
                  </div>
                )}
              </div>
              <div className="session-item-time">
                {new Date(s.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* 2. Main Chat Zone */}
      <main className="chat-zone">
        <header className="header">
          <div className="brand-title">
            <span>Conversational Workspace</span>
          </div>
          <div className="provider-badge" aria-live="polite">
            <div className="provider-dot" />
            <span>Provider: {config.active_provider} ({config.active_model})</span>
          </div>
        </header>

        <div className="messages-container" aria-live="polite">
          {messages.length === 0 ? (
            <div className="welcome-container">
              <div className="welcome-title">Welcome to Lenny's Growth Assistant</div>
              <div className="welcome-subtitle">
                Grounded intelligence trained on 260+ Lenny's Podcast transcripts. Ask product, growth, and strategy questions to get cited answers from top operators.
              </div>
              <div className="prompt-grid">
                {SUGGESTED_PROMPTS.map((p, idx) => (
                  <div key={idx} className="prompt-card" onClick={() => handleSend("answer_question", p.query)}>
                    <div className="prompt-card-title">{p.title}</div>
                    <div className="prompt-card-sub">{p.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div key={m.id || idx} className={`message-bubble ${m.role}`}>
                <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
                
                {/* Citation Chips */}
                {m.citations && m.citations.length > 0 && (
                  <div className="citations-container" aria-label="Citations">
                    <div className="citations-label">Grounded Sources</div>
                    <div className="citations-list">
                      {m.citations.map((c, cIdx) => (
                        <button key={cIdx} className="citation-chip" title={c.source_path}>
                          📍 {c.guest_name || 'Guest'} — {c.episode_title || 'Episode'} ({c.approx_timestamp || '00:00'})
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}

          {status !== "idle" && (
            <div style={{ color: '#64748b', fontSize: '13px', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 16px', backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', width: 'fit-content', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
              <span className="provider-dot" style={{ backgroundColor: '#2563eb' }} />
              {status === "retrieving" && "Searching 260+ transcript chunks..."}
              {status === "streaming" && "Generating grounded response..."}
              {status === "generating" && "Writing Ship 30 essay artifact..."}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Controls */}
        <div className="input-area-wrapper">
          <div className="input-area">
            <input
              type="text"
              className="chat-input"
              placeholder="Ask a product or growth question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend("answer_question")}
            />
            <button className="btn-send" onClick={() => handleSend("answer_question")}>
              Send
            </button>
            <button className="btn-essay" onClick={() => handleSend("write_ship30_essay")}>
              Ship 30 Essay
            </button>
          </div>
        </div>
      </main>

      {/* 3. Artifact Viewer Panel */}
      {artifact && (
        <aside className="artifact-zone" aria-label="Artifact Viewer">
          <header className="header" style={{ justifyContent: 'space-between', borderBottom: '1px solid #e2e8f0' }}>
            <div style={{ fontWeight: '700', fontSize: '14px', color: '#0f172a' }}>
              Artifact Viewer ({artifact.kind})
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                style={{ padding: '6px 12px', fontSize: '12px', fontWeight: '600', backgroundColor: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '6px', cursor: 'pointer', color: '#334155' }}
                onClick={() => setArtifactMode(artifactMode === "rendered" ? "raw" : "rendered")}
              >
                {artifactMode === "rendered" ? "View Raw Source" : "View Rendered"}
              </button>
              <button 
                style={{ padding: '6px 10px', fontSize: '12px', fontWeight: '700', backgroundColor: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '6px', cursor: 'pointer', color: '#64748b' }}
                onClick={() => setArtifact(null)}
              >
                ✕
              </button>
            </div>
          </header>
          
          <div style={{ padding: '12px 20px', borderBottom: '1px solid #e2e8f0', fontSize: '12.5px', color: '#64748b', display: 'flex', justifyContent: 'space-between', backgroundColor: '#f8fafc' }}>
            <span>Word Count: <strong>{artifact.word_count}</strong></span>
            <span>Structure: <strong>{artifact.structure_valid ? "✅ PASS" : "❌ FAIL"}</strong></span>
          </div>

          <div style={{ flex: 1, padding: '20px', overflowY: 'auto', backgroundColor: '#ffffff' }}>
            {artifactMode === "raw" ? (
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '12.5px', color: '#0f172a', backgroundColor: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                {artifact.content}
              </pre>
            ) : artifact.kind === "html" ? (
              <iframe
                title="Sandboxed Artifact Preview"
                className="artifact-iframe"
                sandbox="allow-same-origin"
                srcDoc={artifact.content}
              />
            ) : (
              <div 
                style={{ lineHeight: '1.7', fontSize: '14.5px', color: '#334155' }}
                dangerouslySetInnerHTML={{ __html: parseMarkdownToHTML(artifact.content) }}
              />
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
