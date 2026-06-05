from sentence_transformers import SentenceTransformer
import logfire

model = None
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension


def get_embedding_model() -> SentenceTransformer:
    """Load model once and reuse (singleton)."""
    global model
    if model is None:
        logfire.info("🔄 Loading SentenceTransformer model...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logfire.info("✅ Model loaded successfully")
    return model


def embed_query(query: str) -> list[float]:
    """Embed a single query string for search/retrieval."""
    model = get_embedding_model()
    embedding = model.encode(query)
    logfire.info(f"✅ Query embedded | dim={len(embedding)}")
    return embedding.tolist()  # convert numpy array → list manually


def embed_text(texts: list[str]) -> list[list[float]]:
    """Embed a list of text chunks for ingestion."""
    if not texts:
        return []

    model = get_embedding_model()

    logfire.info(f"📦 Embedding {len(texts)} chunks...")
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True  # cosine similarity ready
    )

    result = embeddings.tolist()  # convert numpy array → list of lists manually
    logfire.info(f"✅ Embedded {len(result)} chunks | dim={len(result[0])}")
    return result