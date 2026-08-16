# L5: RAG pipeline

> Ground answers in your corpus, with provenance. Ring: context. Manual: [section 8](../../MANUAL.md#8-rag-pipeline-internals), [section 15](../../MANUAL.md#15-data-lifecycle-deletion-and-re-indexing).

## What this layer does

Parse documents into structure-aware chunks, embed them, retrieve by hybrid search, rerank, and assemble a context block where every passage carries its source. The baseline that earns the right to be called production RAG: hybrid (dense plus BM25) retrieval, a reranker, and citations the guard layer can check.

## How to choose

- Parsing: Docling for PDFs and office formats with layout; Unstructured for breadth of formats.
- Embeddings: BGE-M3 covers dense plus sparse in one multilingual model; Qwen3-Embedding when quality on the MTEB leaderboard justifies a larger model.
- Vector store: start with pgvector when keeping vectors beside relational data is useful. `indicative`: comfortable to around 10M vectors on one well-indexed node; move only when measured latency, filtering, index build time, or operations justify another engine.
- Reranker: evaluate a cross-encoder such as BGE-Reranker when retrieval misses matter; it often improves ranking quality, but the gain depends on the corpus, candidates, and latency budget.
- End-to-end platform instead of parts: RAGFlow.
- Variant patterns (GraphRAG, Self-RAG, RAPTOR, ColPali and the rest): adopt one when its failure mode appears, per [section 8.1](../../MANUAL.md#81-rag-variants-adopt-one-when-its-failure-mode-appears).

## The options

| Tool | Best for | Link |
|---|---|---|
| Docling | Layout-aware parsing | [github.com/docling-project/docling](https://github.com/docling-project/docling) |
| Unstructured | Breadth of file formats | [github.com/Unstructured-IO/unstructured](https://github.com/Unstructured-IO/unstructured) |
| BGE-M3 | Dense + sparse, 100+ languages | [huggingface.co/BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) |
| Qwen3-Embedding | Larger embedding option; evaluate on your corpus | [huggingface.co/Qwen/Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B) |
| BGE-Reranker | Cross-encoder reranking | [huggingface.co/BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) |
| Qdrant | Filtered hybrid search at scale | [github.com/qdrant/qdrant](https://github.com/qdrant/qdrant) |
| pgvector | Vectors inside Postgres | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) |
| Milvus | Very large corpora | [github.com/milvus-io/milvus](https://github.com/milvus-io/milvus) |
| LanceDB | Embedded, serverless | [github.com/lancedb/lancedb](https://github.com/lancedb/lancedb) |
| Chroma | Prototyping | [github.com/chroma-core/chroma](https://github.com/chroma-core/chroma) |
| Weaviate | Hybrid search built in, GraphQL API | [github.com/weaviate/weaviate](https://github.com/weaviate/weaviate) |
| RAGFlow | Batteries-included RAG platform | [github.com/infiniflow/ragflow](https://github.com/infiniflow/ragflow) |
| Ragas | RAG-specific eval metrics | [github.com/explodinggradients/ragas](https://github.com/explodinggradients/ragas) |

## Wiring it in

Retrieval runs scope-filtered: the entitlement from layer 0 is part of every query, so users only retrieve what they may see. Every chunk carries source, ingestion time, and embedder version; re-embedding is mandatory when the embedder changes ([section 25](../../MANUAL.md#25-versioning-and-change-control)). Deletion propagates to every derived copy ([section 15](../../MANUAL.md#15-data-lifecycle-deletion-and-re-indexing)).
