#!/usr/bin/env python3
"""
Document Ingestion Script
Processes PDF files from the Files directory and stores them in Milvus for RAG.

Usage:
    python backend/ingest_documents.py [--files-dir PATH]
"""

import os
import sys
import argparse
from datetime import datetime

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from document_processor import DocumentProcessor
from vector_store import VectorStore


def ingest_documents(files_dir: str, verbose: bool = True):
    """
    Ingest all PDF documents from the specified directory.
    
    Args:
        files_dir: Path to directory containing PDF files
        verbose: Whether to print progress messages
    """
    # Load environment variables
    load_dotenv()
    
    if verbose:
        print("=" * 60)
        print("Document Ingestion Script")
        print("=" * 60)
        print(f"Files directory: {files_dir}")
        print()
    
    # Check if directory exists
    if not os.path.isdir(files_dir):
        print(f"Error: Directory not found: {files_dir}")
        sys.exit(1)
    
    # List PDF files
    pdf_files = [f for f in os.listdir(files_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("No PDF files found in the directory.")
        sys.exit(0)
    
    if verbose:
        print(f"Found {len(pdf_files)} PDF file(s):")
        for f in pdf_files:
            print(f"  - {f}")
        print()
    
    # Initialize components
    try:
        if verbose:
            print("Connecting to Milvus...")
        
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = os.getenv("MILVUS_PORT", "19530")
        
        vector_store = VectorStore(
            host=milvus_host,
            port=milvus_port,
            api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        if verbose:
            print(f"Connected to Milvus at {milvus_host}:{milvus_port}")
            print()
    except Exception as e:
        print(f"Error connecting to Milvus: {e}")
        print("Make sure Milvus is running. You can start it with:")
        print("  docker-compose up -d milvus-standalone")
        sys.exit(1)
    
    # Initialize document processor
    processor = DocumentProcessor(
        chunk_size=500,
        chunk_overlap=50
    )
    
    # Process documents
    total_chunks = 0
    successful_docs = 0
    failed_docs = []
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(files_dir, pdf_file)
        
        try:
            if verbose:
                print(f"Processing: {pdf_file}...")
            
            chunks = processor.process_pdf(pdf_path)
            
            if not chunks:
                print(f"  Warning: No chunks extracted from {pdf_file}")
                continue
            
            # Store chunks in vector store
            stored = 0
            for chunk in chunks:
                success = vector_store.add_document_chunk(
                    chunk_id=chunk.id,
                    doc_name=chunk.doc_name,
                    chunk_index=chunk.chunk_index,
                    page_num=chunk.page_num,
                    content=chunk.content,
                    created_at=chunk.created_at.isoformat()
                )
                if success:
                    stored += 1
            
            if verbose:
                print(f"  Stored {stored}/{len(chunks)} chunks")
            
            total_chunks += stored
            successful_docs += 1
            
        except Exception as e:
            print(f"  Error processing {pdf_file}: {e}")
            failed_docs.append(pdf_file)
    
    # Flush to persist
    vector_store.flush_documents()
    
    # Print summary
    if verbose:
        print()
        print("=" * 60)
        print("Ingestion Complete")
        print("=" * 60)
        print(f"Documents processed: {successful_docs}/{len(pdf_files)}")
        print(f"Total chunks stored: {total_chunks}")
        
        if failed_docs:
            print(f"Failed documents: {', '.join(failed_docs)}")
        
        # Show stats
        stats = vector_store.get_stats()
        print()
        print("Vector Store Stats:")
        print(f"  Total document chunks: {stats.get('total_document_chunks', 0)}")
        print(f"  Total chat messages: {stats.get('total_messages', 0)}")
    
    vector_store.close()
    return total_chunks


def main():
    parser = argparse.ArgumentParser(
        description="Ingest PDF documents into Milvus for RAG"
    )
    parser.add_argument(
        "--files-dir",
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "Files"),
        help="Path to directory containing PDF files (default: ../Files)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress messages"
    )
    
    args = parser.parse_args()
    
    ingest_documents(
        files_dir=args.files_dir,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
