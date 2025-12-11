"""
Document Processor module for PDF text extraction and chunking.
Handles PDF parsing, text extraction, and content chunking for vector storage.
"""

import os
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
from datetime import datetime
import uuid

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF is required. Install with: pip install PyMuPDF")


@dataclass
class DocumentChunk:
    """Represents a chunk of text from a document."""
    id: str
    doc_name: str
    doc_path: str
    chunk_index: int
    page_num: int
    total_pages: int
    content: str
    created_at: datetime


class DocumentProcessor:
    """
    Process PDF documents for vector storage.
    Extracts text, chunks content, and prepares for embedding.
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_length: int = 20
    ):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
            min_chunk_length: Minimum characters for a valid chunk
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        Extract text from a PDF file, page by page.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dicts with page_num and text content
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        pages = []
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                if text.strip():
                    pages.append({
                        "page_num": page_num,
                        "text": text,
                        "total_pages": len(doc)
                    })
            doc.close()
        except Exception as e:
            print(f"[DocumentProcessor] Error reading PDF {pdf_path}: {e}")
            raise
        
        return pages
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or len(text.strip()) < self.min_chunk_length:
            return []
        
        # Clean up text - normalize whitespace
        text = " ".join(text.split())
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk of text
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at a sentence boundary if not at the end
            if end < len(text):
                # Look for sentence endings
                last_period = chunk.rfind(". ")
                last_newline = chunk.rfind("\n")
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            if len(chunk.strip()) >= self.min_chunk_length:
                chunks.append(chunk.strip())
            
            # Move start position with overlap
            start = end - self.chunk_overlap if end < len(text) else len(text)
        
        return chunks
    
    def process_pdf(self, pdf_path: str) -> List[DocumentChunk]:
        """
        Process a PDF file and return document chunks.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of DocumentChunk objects
        """
        doc_name = os.path.basename(pdf_path)
        print(f"[DocumentProcessor] Processing: {doc_name}")
        
        # Extract text from PDF
        pages = self.extract_text_from_pdf(pdf_path)
        
        if not pages:
            print(f"[DocumentProcessor] No text extracted from {doc_name}")
            return []
        
        # Process each page
        chunks = []
        chunk_index = 0
        
        for page_data in pages:
            page_text = page_data["text"]
            page_num = page_data["page_num"]
            total_pages = page_data["total_pages"]
            
            # Chunk the page text
            text_chunks = self.chunk_text(page_text)
            
            for text_chunk in text_chunks:
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    doc_name=doc_name,
                    doc_path=pdf_path,
                    chunk_index=chunk_index,
                    page_num=page_num,
                    total_pages=total_pages,
                    content=text_chunk,
                    created_at=datetime.now()
                )
                chunks.append(chunk)
                chunk_index += 1
        
        print(f"[DocumentProcessor] Created {len(chunks)} chunks from {doc_name}")
        return chunks
    
    def process_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None
    ) -> Generator[DocumentChunk, None, None]:
        """
        Process all PDF files in a directory.
        
        Args:
            directory: Path to directory containing PDFs
            extensions: File extensions to process (default: ['.pdf'])
            
        Yields:
            DocumentChunk objects
        """
        if extensions is None:
            extensions = [".pdf"]
        
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"Directory not found: {directory}")
        
        print(f"[DocumentProcessor] Scanning directory: {directory}")
        
        processed_files = 0
        total_chunks = 0
        
        for filename in os.listdir(directory):
            if any(filename.lower().endswith(ext) for ext in extensions):
                file_path = os.path.join(directory, filename)
                try:
                    chunks = self.process_pdf(file_path)
                    processed_files += 1
                    total_chunks += len(chunks)
                    
                    for chunk in chunks:
                        yield chunk
                except Exception as e:
                    print(f"[DocumentProcessor] Error processing {filename}: {e}")
                    continue
        
        print(f"[DocumentProcessor] Completed: {processed_files} files, {total_chunks} chunks")
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return [".pdf"]
