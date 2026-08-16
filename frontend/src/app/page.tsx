'use client';

import React, { useState, useRef } from 'react';
import { Mic, MicOff, Send, Zap, ShieldCheck, Volume2, Sparkles } from 'lucide-react';
import { GoanBorderTape } from '@/components/GoanBorderTape';
import { Header } from '@/components/Header';
import { HeroLogo } from '@/components/HeroLogo';
import { Footer } from '@/components/Footer';

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
    <main className="min-h-screen bg-[#075E34] bg-[url('/Sun%20rise.png')] bg-top bg-no-repeat bg-cover text-[#FFE500] flex flex-col justify-between overflow-x-hidden relative select-none">
      {/* Top Traditional Goan Geometric Border Tape */}
      <GoanBorderTape />

      {/* Main Header Bar */}
      <Header />

      {/* Hero Section with Official Hacker House Goa Artwork */}
      <section className="relative w-full max-w-7xl mx-auto px-4 py-4 flex flex-col items-center justify-center">
        <div className="flex flex-wrap items-center justify-center gap-3 mb-2">
          <span className="badge badge-pink shadow-md">Team TechTadkaa</span>
          <span className="badge badge-yellow shadow-md">MSMARCO-XI Indic Corpus</span>
        </div>

        <HeroLogo size="md" />

        <h1 className="font-mono text-xl md:text-3xl font-black text-[#FFE500] text-center tracking-wider uppercase text-stroke-dark mt-2">
          Voice-Enabled RAG System
        </h1>
        <p className="font-mono text-xs md:text-sm text-[#FEFCE8]/80 text-center mt-2 max-w-2xl bg-[#044425]/80 px-4 py-2 rounded-lg border border-[#FFE500]/30 shadow-inner">
          Sarvam AI & ElevenLabs Voice Integration • Groq Llama 3.1
        </p>
      </section>

      {/* Main Dashboard Layout Container */}
      <div className="w-full max-w-7xl mx-auto px-4 py-6 flex-1 flex flex-col gap-8 z-10">
        
        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Left Column: Voice & Query Input */}
          <section className="flex flex-col gap-6">
            
            {/* Voice Mic Section */}
            <div className="glass-card postit-card p-6 md:p-8 text-center flex flex-col items-center justify-center relative overflow-hidden">
              <div className="flex items-center gap-2 mb-6 text-[#FFE500] font-mono font-bold text-lg">
                <Volume2 className="text-[#FFE500]" size={22} />
                <span>Speak in Hindi or English</span>
              </div>

              <button
                id="mic-recording-button"
                className={`mic-btn ${isRecording ? 'recording' : ''}`}
                onClick={isRecording ? stopRecording : startRecording}
                disabled={loading}
                title={isRecording ? 'Stop Recording' : 'Start Voice Input'}
              >
                {isRecording ? <MicOff size={36} /> : <Mic size={36} />}
              </button>

              <p className={`mt-5 font-mono text-xs md:text-sm font-bold ${isRecording ? 'text-[#FF1D78] animate-pulse' : 'text-[#FEFCE8]/80'}`}>
                {isRecording ? 'Listening... Click again to process' : 'Click microphone to record voice prompt'}
              </p>

              <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
                <button
                  type="button"
                  className={`badge transition-all cursor-pointer ${language === 'hi-IN' ? 'bg-[#FFE500] text-[#044425] border-[#FFE500]' : 'bg-transparent text-[#FFE500] border-[#FFE500]/40 hover:border-[#FFE500]'}`}
                  onClick={() => setLanguage('hi-IN')}
                >
                  Hindi (हिन्दी)
                </button>
                <button
                  type="button"
                  className={`badge transition-all cursor-pointer ${language === 'en-IN' ? 'bg-[#FFE500] text-[#044425] border-[#FFE500]' : 'bg-transparent text-[#FFE500] border-[#FFE500]/40 hover:border-[#FFE500]'}`}
                  onClick={() => setLanguage('en-IN')}
                >
                  English
                </button>
                <button
                  type="button"
                  className={`badge transition-all cursor-pointer ${language === 'mr-IN' ? 'bg-[#FFE500] text-[#044425] border-[#FFE500]' : 'bg-transparent text-[#FFE500] border-[#FFE500]/40 hover:border-[#FFE500]'}`}
                  onClick={() => setLanguage('mr-IN')}
                >
                  Marathi (मराठी)
                </button>
                <button
                  type="button"
                  className={`badge transition-all cursor-pointer ${language === 'bn-IN' ? 'bg-[#FFE500] text-[#044425] border-[#FFE500]' : 'bg-transparent text-[#FFE500] border-[#FFE500]/40 hover:border-[#FFE500]'}`}
                  onClick={() => setLanguage('bn-IN')}
                >
                  Bengali (বাংলা)
                </button>
                <button
                  type="button"
                  className={`badge transition-all cursor-pointer ${language === 'te-IN' ? 'bg-[#FFE500] text-[#044425] border-[#FFE500]' : 'bg-transparent text-[#FFE500] border-[#FFE500]/40 hover:border-[#FFE500]'}`}
                  onClick={() => setLanguage('te-IN')}
                >
                  Telugu (తెలుగు)
                </button>
                <button
                  type="button"
                  className={`badge transition-all cursor-pointer ${language === 'ta-IN' ? 'bg-[#FFE500] text-[#044425] border-[#FFE500]' : 'bg-transparent text-[#FFE500] border-[#FFE500]/40 hover:border-[#FFE500]'}`}
                  onClick={() => setLanguage('ta-IN')}
                >
                  Tamil (தமிழ்)
                </button>
              </div>
            </div>

            {/* Text Query Input Fallback */}
            <form className="glass-card postit-card p-6 flex flex-col gap-3" onSubmit={handleTextSubmit}>
              <h3 className="font-mono text-xs font-bold text-[#FFE500]/90 uppercase tracking-wider">
                Or type query manually:
              </h3>
              <div className="flex gap-3">
                <input
                  id="query-text-input"
                  type="text"
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  placeholder={language.startsWith('hi') ? 'अपना प्रश्न यहाँ टाइप करें...' : 'Type your question here...'}
                  className="flex-1 bg-[#044425] border-2 border-[#FFE500]/50 rounded-xl px-4 py-3 text-[#FEFCE8] font-mono text-sm placeholder-[#FEFCE8]/40 outline-none focus:border-[#FFE500] focus:ring-2 focus:ring-[#FFE500]/30 transition-all"
                />
                <button
                  id="submit-query-btn"
                  type="submit"
                  disabled={loading || !queryText.trim()}
                  className={`font-mono text-xs font-black px-6 py-3 rounded-xl border-2 uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer ${
                    queryText.trim()
                      ? 'bg-[#FFE500] hover:bg-[#FF1D78] text-[#044425] hover:text-[#FEFCE8] border-[#FFE500] hover:border-[#FF1D78] shadow-md hover:-translate-y-0.5'
                      : 'bg-[#044425]/60 text-[#FEFCE8]/40 border-[#FFE500]/20 cursor-not-allowed'
                  }`}
                >
                  <Send size={16} />
                  <span>{loading ? 'Processing...' : 'Search'}</span>
                </button>
              </div>
              {response && (
                <div className="mt-2 font-mono text-xs flex items-center justify-between text-[#FEFCE8]/80 bg-[#044425]/80 px-3 py-2 rounded-lg border border-[#FFE500]/20">
                  <span>
                    Last query: <span className="text-[#FFE500] font-bold">&ldquo;{response.query}&rdquo;</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setResponse(null)}
                    className="text-[#FF1D78] hover:underline font-bold ml-3 cursor-pointer"
                  >
                    ✕ Clear results
                  </button>
                </div>
              )}
            </form>
          </section>

          {/* Right Column: Latency Metrics & Response */}
          <section className="flex flex-col gap-6">
            
            {/* Latency Dashboard Panel */}
            <div className="glass-card postit-card p-6">
              <h2 className="font-mono text-base font-bold text-[#FFE500] flex items-center gap-2 mb-4 uppercase tracking-wider">
                <Zap className="text-[#FFE500]" size={20} />
                <span>Per-Stage Latency Breakdown</span>
              </h2>

              {response ? (
                <div className="grid grid-cols-2 gap-3 font-mono">
                  <div className="bg-[#044425]/90 p-3 rounded-xl border border-[#FFE500]/30 flex flex-col">
                    <span className="text-[11px] text-[#FEFCE8]/70 font-semibold">STT (Sarvam AI)</span>
                    <span className="text-base font-black text-[#FFE500] mt-1">{response.latency.stt_ms} ms</span>
                  </div>

                  <div className="bg-[#075E34] p-3 rounded-xl border-2 border-[#FFE500] shadow-[0_0_15px_rgba(255,229,0,0.25)] flex flex-col">
                    <span className="text-[11px] text-[#FFE500] font-bold uppercase">Retrieval Leg Target</span>
                    <span className="text-base font-black text-[#FFE500] mt-1">
                      {response.latency.retrieval_leg_ms} ms
                    </span>
                  </div>

                  <div className="bg-[#044425]/90 p-3 rounded-xl border border-[#FFE500]/30 flex flex-col">
                    <span className="text-[11px] text-[#FEFCE8]/70 font-semibold">LLM Generation (Groq)</span>
                    <span className="text-base font-black text-[#FF1D78] mt-1">{response.latency.generation_ms} ms</span>
                  </div>

                  <div className="bg-[#044425]/90 p-3 rounded-xl border border-[#FFE500]/30 flex flex-col">
                    <span className="text-[11px] text-[#FEFCE8]/70 font-semibold">Total E2E Pipeline</span>
                    <span className="text-base font-black text-[#FEFCE8] mt-1">{response.latency.total_e2e_ms} ms</span>
                  </div>
                </div>
              ) : (
                <p className="font-mono text-xs text-[#FEFCE8]/60 italic bg-[#044425]/50 p-4 rounded-xl border border-[#FFE500]/20 text-center">
                  Run a voice or text query to view live latency benchmarks.
                </p>
              )}
            </div>

            {/* Generated Answer & Guardrail Status */}
            <div className="glass-card postit-card p-6 flex flex-col gap-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h2 className="font-mono text-base font-bold text-[#FFE500] flex items-center gap-2 uppercase tracking-wider">
                  <Sparkles className="text-[#FF1D78]" size={20} />
                  <span>Generated Response</span>
                </h2>
                {response && (
                  <span className="badge badge-pink flex items-center gap-1">
                    <ShieldCheck size={14} />
                    <span>{response.guardrail.reasoning}</span>
                  </span>
                )}
              </div>

              <div className="bg-[#044425]/90 border border-[#FFE500]/30 p-4 rounded-xl min-h-[110px] flex items-center">
                {loading ? (
                  <p className="font-mono text-xs md:text-sm text-[#FFE500] animate-pulse">
                    Processing query through LangGraph pipeline...
                  </p>
                ) : response ? (
                  <p className="font-sans text-sm md:text-base text-[#FEFCE8] leading-relaxed">
                    {response.answer}
                  </p>
                ) : (
                  <p className="font-mono text-xs text-[#FEFCE8]/50 italic">
                    Waiting for query input...
                  </p>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* Bottom Traditional Goan Geometric Border Tape */}
      <GoanBorderTape className="mt-8" />

      {/* Goan Footer */}
      <Footer />
    </main>
  );
}
