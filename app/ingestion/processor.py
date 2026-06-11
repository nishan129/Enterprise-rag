import os
import sys
import uuid
import json
import logfire
import vertexai


from typing import List
from google.cloud import storage
from qdrant_client import QdrantClient
from qdrant_client.http import models 

# Import local modules
from app.config import settings
from app.services.retrieval.embeddings import embed_text
from app.ingestion.loaders.pdf import parser_pdf
from app.ingestion.loaders.html import parser_html
from app.ingestion.loaders.office import parser_office
from app.ingestion.loaders.text import parser_text
from app.ingestion.chunking.splitter import chunk_text

# Initialize Logfire with the Enterprise Ingestion Service Name
logfire.configure(service_name="entreprise-ingestion-service")

# Initialize Vertex AI for Embeddings
vertexai.init(project="459810806586", location="us-central1")

# Initialize GCS Client
storage_client = storage.Client(project=settings.PROJECT_ID)

# Initialize Qdrant Client
qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

from fastapi import FastAPI, Request, BackgroundTasks
import tempfile

# Initialize FastApi for Webhook Mode
app = FastAPI()


def upload_to_gcs(data, bucket_name: str, destination_blob_name: str, is_json: bool = False):
    """Uploads a file or JSON data to GCS"""
    with logfire.span("☁️ GCS Upload", bucket=bucket_name, blob=destination_blob_name):
        try:
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            
            if is_json:
                blob.upload_from_string(json.dumps(data), content_type='application/json')
            else:
                blob.upload_from_filename(data)
            logfire.info(f"✅ File uploaded to GCS: {destination_blob_name}")
        except Exception as e:
            logfire.error(f"❌ GCS Upload Failed: {e}")
        
def process_file(file_path: str, filename: str, source_type:str, skip_raw_upload: bool = False):
    """
    Orchestrates the parsing, chunking, embedding, and indexing of a single file.
    """
    with logfire.span("📂 Processing File", filename=filename, source_type=source_type):
        try:
            # Step 1: Upload RAW file to GCS
            raw_gcs_path = f"{source_type}/{filename}"

            if skip_raw_upload:
                upload_to_gcs(file_path, settings.RAW_BUCKET, raw_gcs_path)
            else:
                logfire.info(f"⏯️ Skipping RAW upload for {filename} already in GCS")
        
            # Step 2: Extract Text based on extension
            ext = filename.lower().split('.')[-1]
            if ext == "pdf":
                full_text = parser_pdf(file_path)
            elif ext in ["html", "htm"]:
                full_text = parser_html(file_path)
            elif ext in ["docx", "xlsx", "pptx"]:
                full_text = parser_office(file_path)
            elif ext in ["txt", "md"]:
                full_text = parser_text(file_path)
            else:
                logfire.warning(f"⏩ Skipping unsupported file type: {ext}. Skipping file: {filename}")
                return
            
            if not full_text or not full_text.strip():
                logfire.warning(f"⚠️ No text extracted from file: {filename}. Skipping.")
                return
            
            # Step 3: Chunk Text
            chunks = chunk_text(full_text,chunk_size=1000)
            if not chunks:
                logfire.warning(f"⚠️ No chunks created from file: {filename}. Skipping.")
                return
            
            # Step 4: Upload PROCESSED metadata to GCP
            processed_data = {"filename": filename, "chunks": chunks, "source_type": source_type}
            processed_gcs_path = f"{source_type}/processed/{filename}.json"
            upload_to_gcs(processed_data, settings.PROCESSED_BUCKET, processed_gcs_path, is_json=True)


            # Step 5: Embed and Index in Qdrant
            logfire.span("🧠 Indexing & Vectorizing")

            embeddings = embed_text(chunks)

            points = [
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector = vector,
                    payload = {
                         "text": chunk,
                            "source": filename,
                            "source_type": source_type,
                            "raw_gcs_path": f"gs://{settings.RAW_BUCKET}/{raw_gcs_path}",
                    }
                    )
                    for chunk, vector in zip(chunks, embeddings)
            ]
            qdrant_client.upsert(
                 collection_name=settings.QDRANT_COLLECTION,
                    points=points,
                )
            logfire.info(f"✨ Indexed {len(points)} points to Qdrant from '{filename}'")

        except Exception as e:
            logfire.error(f"❌ Error processing file {filename}: {e}")
            raise e

@app.post("/")
async def eventarc_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Entery point for Google Cloud Eventarc triggers.
    """
    try:
        data = await request.json()

        bucket = data.get("bucket")
        name = data.get('name')

        if not bucket or not name:
            logfire.error("❌ Invalid Eventarc payload")
            return {"status":'error','message':'Invalid payload'}, 404
        
        logfire.info(f"📡 Eventarc Triggered: {name} in {bucket}")


        if bucket != settings.RAW_BUCKET:
            logfire.warning(f"Ingoring event from unauthorized bucked")
            return {"status":"ignored"}
        
        parts = name.split('/')
        source_type  = parts[0] if len(parts) > 1 else "general"
        filename = parts[-1]

        background_tasks.add_task(process_from_gcs, bucket,name,filename,source_type)

        return {'status':'accepted', 'file':name}
    
    except Exception as e:
        logfire.error(f"❌ Webhook Error: {e}")
        return {'status':'error'}, 500
    
async def process_from_gcs(bucket_name: str, blob_name:str, filename: str, source_type:str):
    """
    Downloads a file from GCS and triggers the processing pipeline
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
        try:
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.download_to_filename(temp_file.name)

            process_file(temp_file.name, filename, source_type, skip_raw_upload=True)
        finally:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)



def run_universal_ingestion(base_dir: str, explicit_source_type:str = None, wipe:bool = False):
    """
    Automatically scans the directory.
    If it has subfolders, maps them to source_types.
    If it has no subfolders, uses the explicit_source_type or infers from the folder name.
    """
    with logfire.span("🌍 Universal Ingestion Started", base_dir=base_dir):
        # Handle Collection Wipe
        if wipe:
            with logfire.span("🧹 Wiping Collection"):
                if qdrant_client.collection_exists(settings.QDRANT_COLLECTION):
                    qdrant_client.delete_collection(settings.QDRANT_COLLECTION)
                    logfire.info(f"🗑️ Collection '{settings.QDRANT_COLLECTION}' wiped successfully.")

        # Ensure Collection Exists
        if not qdrant_client.collection_exists(settings.QDRANT_COLLECTION):
            qdrant_client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=models.VectorParams(size= 384, distance=models.Distance.COSINE)
            )
            logfire.info(f"🆕 Created Collection '{settings.QDRANT_COLLECTION}' created successfully.")
        
        # Scan for subfolders
        subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

        if not subdirs:
            # If no subdirs, use explicit type of infer from the base directory name
            
            if explicit_source_type:
                source_type = explicit_source_type
            else:
                base_name = os.path.basename(os.path.normpath(base_dir)).lower()
                source_type = "true" if "true" in base_name else "noisy" if "noisy" in base_name else "general"

            logfire.info(f"📁 No subdirectories found. Processing {base_dir}")
            process_directory(base_dir, source_type)
        else:
            for subdir in subdirs:
                source_type = "true" if "true" in subdir.lower() else "noisy" if "noisy" in subdir.lower() else "general"
                dir_path = os.path.join(base_dir, subdir)
                process_directory(dir_path, source_type)


def process_directory(dir_path: str, source_type: str):
    """
    Processes all files in a specific directory.
    """
    with logfire.span("📁 Scanning Directory", dir_path=dir_path, source_type=source_type):
        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        logfire.info(f"🔍 Found {len(files)} files ")

        for filename in files:
            file_path = os.path.join(dir_path, filename)
            process_file(file_path, filename, source_type)


if __name__ == "__main__":
    # Usage: python -m app.ingestion.processor [dir_path] [source_type] [--wipe]

    wipe_requested = "--wipe" in sys.argv
    cleaned_args = [arg for arg in sys.argv if arg != "--wipe"]

    # Default to DATA/ if no path provided
    target_dir = cleaned_args[1] if len(cleaned_args) > 1 else "DATA"
    explicit_type = cleaned_args[2] if len(cleaned_args) > 2 else None

    if os.path.exists(target_dir):
        run_universal_ingestion(target_dir, explicit_source_type=explicit_type, wipe=wipe_requested)
        logfire.info("🏳️ Universal Ingestion JOB Completed Successfully")
    else:
        print(f"❌ Error: Path '{target_dir}' does not exist. Please provide a valid path.")

    