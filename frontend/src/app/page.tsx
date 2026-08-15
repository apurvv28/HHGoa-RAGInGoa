'use client';

import React, { useState, useRef } from 'react';
import { Mic, MicOff, Send, Zap, ShieldCheck, Database, Volume2, Sparkles, Layers } from 'lucide-react';

interface Chunk {
  chunk_id: string;
  doc_id: string;
  text: string;
  language: string;
  score: number;
}

interface Latency {
  stt_ms: number;
  query_embedding_ms: number;
  qdrant_search_ms: number;
  retrieval_leg_ms: number;
  guardrail_ms: number;
  generation_ms: number;
  tts_ms: number;
  total_e2e_ms: number;
}

interface Guardrail {
  is_safe: boolean;
  is_in_domain: boolean;
  is_grounded: boolean;
  confidence_score: number;
  reasoning: string;
}

interface QueryResponse {
  query: string;
  answer: string;
  retrieved_chunks: Chunk[];
  latency: Latency;
  guardrail: Guardrail;
}

export default function VoiceRAGPage() {
  const [queryText, setQueryText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [language, setLanguage] = useState('hi-IN');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

  // Handle Text Query Submission
  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = queryText.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setQueryText(''); // clear input immediately so placeholder shows
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_text: trimmed,
          language: language.startsWith('hi') ? 'hi' : 'en',
          top_k: 5
        })
      });
      const data: QueryResponse = await res.json();
      setResponse(data);
    } catch (err) {
      console.error('Error executing query:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle Microphone Audio Recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      let options = {};
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm')) {
        options = { mimeType: 'audio/webm' };
      } else if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/mp4')) {
        options = { mimeType: 'audio/mp4' };
      }

      mediaRecorderRef.current = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
        const ext = mimeType.includes('webm') ? 'webm' : 'wav';
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        await sendAudioToBackend(audioBlob, ext);
      };

      mediaRecorderRef.current.start(250);
      setIsRecording(true);
    } catch (err) {
      alert('Microphone permission denied or not available.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendAudioToBackend = async (blob: Blob, ext: string = 'webm') => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', blob, `recording.${ext}`);
      formData.append('language', language);
      formData.append('synthesize_voice', 'true');

      const res = await fetch(`${BACKEND_URL}/api/v1/voice/query`, {
        method: 'POST',
        body: formData
      });
      const data: QueryResponse = await res.json();
      setResponse(data);
      if (data.query) {
        setQueryText(data.query);
      }
    } catch (err) {
      console.error('Voice backend query failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 20px' }}>
      {/* Header Banner */}
      <header style={{ textAlign: 'center', marginBottom: '40px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <span className="badge badge-purple">Team TechTadkaa</span>
          <span className="badge badge-cyan">MSMARCO-XI Indic Corpus</span>
        </div>
        <h1 style={{ fontSize: '2.5rem', fontWeight: 800, background: 'linear-gradient(135deg, #00f2fe, #4facfe, #7f00ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Voice-Enabled RAG System
        </h1>
        <p style={{ color: 'var(--text-muted)', marginTop: '8px', fontSize: '1.05rem' }}>
          Sub-100ms Retrieval Leg | Sarvam AI & ElevenLabs Voice Integration | Groq Llama 3.1
        </p>
      </header>

      {/* Main Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '28px' }}>
        {/* Left Column: Voice & Query Input */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Voice Mic Section */}
          <div className="glass-card" style={{ padding: '32px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Volume2 color="var(--primary-cyan)" size={22} /> Speak in Hindi or English
            </h2>

            <button
              id="mic-recording-button"
              className={`mic-btn ${isRecording ? 'recording' : ''}`}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={loading}
              title={isRecording ? 'Stop Recording' : 'Start Voice Input'}
            >
              {isRecording ? <MicOff size={36} /> : <Mic size={36} />}
            </button>

            <p style={{ marginTop: '16px', fontSize: '0.9rem', color: isRecording ? '#ff0055' : 'var(--text-muted)' }}>
              {isRecording ? 'Listening... Click again to process' : 'Click microphone to record voice prompt'}
            </p>

            <div style={{ marginTop: '20px', display: 'flex', gap: '12px' }}>
              <button
                className={`badge ${language === 'hi-IN' ? 'badge-cyan' : ''}`}
                style={{ cursor: 'pointer', background: language === 'hi-IN' ? undefined : 'transparent' }}
                onClick={() => setLanguage('hi-IN')}
              >
                Hindi (हिन्दी)
              </button>
              <button
                className={`badge ${language === 'en-IN' ? 'badge-cyan' : ''}`}
                style={{ cursor: 'pointer', background: language === 'en-IN' ? undefined : 'transparent' }}
                onClick={() => setLanguage('en-IN')}
              >
                English
              </button>
            </div>
          </div>

          {/* Text Query Input Fallback */}
          <form className="glass-card" onSubmit={handleTextSubmit} style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '12px', color: 'var(--text-muted)' }}>Or type query manually:</h3>
            <div style={{ display: 'flex', gap: '12px' }}>
              <input
                id="query-text-input"
                type="text"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                placeholder={language.startsWith('hi') ? 'अपना प्रश्न यहाँ टाइप करें...' : 'Type your question here...'}
                style={{
                  flex: 1,
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '10px',
                  padding: '12px 16px',
                  color: '#fff',
                  fontSize: '1rem',
                  outline: 'none'
                }}
              />
              <button
                id="submit-query-btn"
                type="submit"
                disabled={loading || !queryText.trim()}
                style={{
                  background: queryText.trim()
                    ? 'linear-gradient(135deg, var(--primary-cyan), var(--primary-blue))'
                    : 'rgba(255,255,255,0.1)',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '0 20px',
                  color: queryText.trim() ? '#000' : '#666',
                  fontWeight: 700,
                  cursor: queryText.trim() ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s'
                }}
              >
                <Send size={18} /> {loading ? 'Processing...' : 'Search'}
              </button>
            </div>
            {response && (
              <p style={{ marginTop: '8px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Last query: <span style={{ color: 'var(--primary-cyan)' }}>&ldquo;{response.query}&rdquo;</span>
                <button
                  type="button"
                  onClick={() => setResponse(null)}
                  style={{ marginLeft: '10px', color: '#ff6b6b', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.8rem' }}
                >
                  ✕ Clear results
                </button>
              </p>
            )}
          </form>
        </section>

        {/* Right Column: Latency Metrics & Response */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Latency Dashboard Panel */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap color="var(--primary-cyan)" size={22} /> Per-Stage Latency Breakdown
            </h2>

            {response ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>STT (Sarvam AI)</span>
                  <p className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--primary-cyan)' }}>
                    {response.latency.stt_ms} ms
                  </p>
                </div>

                <div style={{ background: 'rgba(0, 242, 254, 0.1)', padding: '12px', borderRadius: '10px', border: '1px solid var(--primary-cyan)' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Retrieval Leg Target</span>
                  <p className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--accent-green)' }}>
                    {response.latency.retrieval_leg_ms} ms
                    <span style={{ fontSize: '0.7rem', marginLeft: '6px', color: '#888' }}>( {'<100ms'} )</span>
                  </p>
                </div>

                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>LLM Generation (Groq)</span>
                  <p className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#c084fc' }}>
                    {response.latency.generation_ms} ms
                  </p>
                </div>

                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Total E2E Pipeline</span>
                  <p className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                    {response.latency.total_e2e_ms} ms
                  </p>
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
                Run a voice or text query to view live latency benchmarks.
              </p>
            )}
          </div>

          {/* Generated Answer & Guardrail Status */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h2 style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles color="var(--primary-purple)" size={22} /> Generated Response
              </h2>
              {response && (
                <span className={`badge ${response.guardrail.is_grounded ? 'badge-green' : ''}`}>
                  <ShieldCheck size={14} style={{ display: 'inline', marginRight: '4px' }} />
                  {response.guardrail.reasoning}
                </span>
              )}
            </div>

            <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '16px', borderRadius: '12px', minHeight: '90px' }}>
              {loading ? (
                <p style={{ color: 'var(--primary-cyan)' }}>Processing query through LangGraph pipeline...</p>
              ) : response ? (
                <p style={{ fontSize: '1.05rem', lineHeight: '1.6' }}>{response.answer}</p>
              ) : (
                <p style={{ color: 'var(--text-muted)' }}>Waiting for query input...</p>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* Bottom Section: Retrieved Context Chunks Transparency Inspector */}
      {response && response.retrieved_chunks && response.retrieved_chunks.length > 0 && (
        <section className="glass-card" style={{ marginTop: '36px', padding: '28px' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database color="var(--primary-cyan)" size={22} /> Retrieved Passages Inspector (Qdrant Vector DB)
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {response.retrieved_chunks.map((chunk, idx) => (
              <div key={chunk.chunk_id || idx} style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.07)', borderRadius: '12px', padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--primary-cyan)' }}>
                    [{chunk.doc_id}] Chunk #{idx + 1}
                  </span>
                  <span className="badge badge-green" style={{ fontSize: '0.7rem' }}>
                    Score: {chunk.score.toFixed(4)}
                  </span>
                </div>
                <p style={{ fontSize: '0.9rem', color: '#e2e8f0', lineHeight: '1.5' }}>{chunk.text}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
