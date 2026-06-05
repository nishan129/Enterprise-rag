from typing import List
import logfire

def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """
    Splits text by paragraphs, with fallback character-level splitting
    for paragraphs that exceed chunk_size.
    """

    with logfire.span("✂️ Text Chunking", text_length=len(text)):
        if not text.strip():
            return []

        def split_large_paragraph(para: str) -> List[str]:
            """Fallback: split oversized paragraphs by sentences or chars."""
            sub_chunks = []
            
            # Try sentence-level split first
            sentences = para.replace(". ", ".\n").split("\n")
            current = ""
            
            for sentence in sentences:
                if len(current) + len(sentence) < chunk_size:
                    current += sentence + " "
                else:
                    if current.strip():
                        sub_chunks.append(current.strip())
                    # If single sentence is still too big, hard split by chars
                    if len(sentence) >= chunk_size:
                        for i in range(0, len(sentence), chunk_size):
                            sub_chunks.append(sentence[i:i + chunk_size])
                    else:
                        current = sentence + " "

            if current.strip():
                sub_chunks.append(current.strip())

            return sub_chunks

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for p in paragraphs:
            # ✅ If paragraph itself exceeds chunk_size, split it first
            if len(p) >= chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.extend(split_large_paragraph(p))

            elif len(current_chunk) + len(p) < chunk_size:
                current_chunk += p + "\n\n"

            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        valid_chunks = [c for c in chunks if c.strip()]
        
        # ✅ Safety net — hard truncate anything still too large
        safe_chunks = []
        for chunk in valid_chunks:
            if len(chunk) > chunk_size * 2:
                for i in range(0, len(chunk), chunk_size):
                    safe_chunks.append(chunk[i:i + chunk_size])
            else:
                safe_chunks.append(chunk)

        logfire.info(f"✅ Generated {len(safe_chunks)} chunks")
        return safe_chunks