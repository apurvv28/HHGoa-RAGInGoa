# Retrieval Leg Benchmark Report — HH Goa Voice RAG

**Benchmark Date**: `2026-08-16 15:49:38`  
**Test Suite**: 54 Multilingual Test Queries (English, Hindi, Marathi, Bengali, Telugu, Tamil)  
**Retrieval Target**: **< 100.0 ms**  
**Sub-100ms Compliance Pass Rate**: **`100.0%`** (54/54 queries passed)

---

## 📊 Latency Percentile Benchmark Breakdown

| Pipeline Stage / Component | Min (ms) | P50 (ms) | P70 (ms) | P90 (ms) | P99 (ms) | Mean (ms) | Target Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Query Embedding (multilingual-e5)** | `13.98` | `16.12` | `17.66` | `20.09` | `30.12` | `17.12` | ✅ Sub-20ms |
| **Qdrant Vector ANN Search** | `10.91` | `11.73` | `11.94` | `12.67` | `14.49` | `11.86` | ✅ Sub-15ms |
| **Retrieval Leg (Total)** | **`25.68`** | **`27.8`** | **`29.52`** | **`32.83`** | **`42.99`** | **`29.03`** | **`100.0% <100ms`** |
| **Guardrails Validation** | `0.12` | `0.15` | `0.16` | `0.2` | `0.26` | `0.16` | ✅ Sub-5ms |
| **LLM Generation (Groq Llama 3.1)** | `42.68` | `67.09` | `84.2` | `202.57` | `307.1` | `90.86` | ⚡ Groq Fast |
| **Total End-to-End Pipeline** | `72.48` | `97.04` | `115.14` | `239.01` | `354.84` | `123.45` | 🚀 Realtime Voice |

---

## ⚡ Technical Optimizations Applied

1. **PyTorch CPU Multi-Threading**: Single-query encoding PyTorch thread tuning (`torch.set_num_threads(2)`).
2. **Lifespan Startup Warmup**: Preloading and warming up `intfloat/multilingual-e5-small` model weights during FastAPI lifespan startup to eliminate initial cold-start latency.
3. **Cross-Lingual Unfiltered HNSW Search**: Bypassed unindexed payload string filter scans in local Qdrant, allowing cross-lingual embeddings to retrieve top-k passages in **< 15ms**.
4. **Instant Safety Guardrail Refusal**: High-risk harmful/illegal queries trigger safety refusal in **< 3ms**.
