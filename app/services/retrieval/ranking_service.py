import time
import logfire
from flashrank import Ranker, RerankRequest


# Lazy initialization - Ranker is loaded on first use to ensure logfire
_ranker = None

def _get_ranker() -> Ranker:
    """
    Initializes the FlashRank engine lazily.
    FlashRanker uses a local ONNX model (ms-marco-MiniLM-L-6-V2) for ultra fast rank.
    """

    global _ranker
    if _ranker is None:
        logfire.info("🧠 Initializing FlashRank Model (TinyBERT)")
        try:
            # We use a specific cache directory to avoid permissions 
            _ranker = Ranker(cache_dir="/tmp/flashrank")
        except Exception:
            _ranker = Ranker()
    
    return _ranker


def rerank_documents(query: str, documents: list[str], top_n: int = 5) -> list[str]:
    """
    Refines retrieval results by re-scoring documents against the query semantically.

    Why FlashRank?
    Standard vector search (Cosine Similarity) is fast but mathemtical "fuzzy".
    FlashRank uses a Cross-Encoder approch which is much more precise but usually slow.
    FlashRank solves this by using highly optimized, quantized ONNX models locally.
    """
    if not documents:
        return []
    
    start_time = time.time()
    logfire.info(f"📡 [Reranker] Sending {len(documents)} docs to FlashRank Cross-Encoder...")

    try:
        ranker = _get_ranker()

        # FlashRank expects a list of dictionaries with 'id' and 'text' 
        passages = [
            {"id":i, "text":doc}
            for i, doc in enumerate(documents)
        ]

        request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(request)

        # Results are returned sorted by highest seamnatic score first
        reranked_docs = []
        for res in results[:top_n]:
            reranked_docs.append(res['text'])

        dureation = time.time() - start_time
        top_score = results[0]['score'] if results else "N/A"
        logfire.info(f"✅ [Reranker] Done in {dureation:.2f}s, Top se")
        return reranked_docs
    except Exception as e:
        logfire.error(f"❌ [Reranker] Semantic Reranking Failed: {e}")
        # Fallback to the orifinal output Qdrant order to ensure the user 
        return documents[:top_n]