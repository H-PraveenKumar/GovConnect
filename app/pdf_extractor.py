import hashlib
import logging
from typing import Optional, Tuple
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from io import StringIO
from app.config import settings

logger = logging.getLogger(__name__)


class PDFExtractor:
    """PDF text extraction utility with PyMuPDF primary and pdfminer fallback"""
    
    @staticmethod
    def compute_sha256(pdf_bytes: bytes) -> str:
        """Compute SHA256 hash of PDF bytes for idempotency"""
        return hashlib.sha256(pdf_bytes).hexdigest()
    
    @staticmethod
    def extract_text_pymupdf(pdf_bytes: bytes) -> Optional[str]:
        """Extract text using PyMuPDF (fitz) - DISABLED (requires build tools)"""
        logger.warning("PyMuPDF not available - using pdfminer.six only")
        return None
    
    @staticmethod
    def extract_text_pdfminer(pdf_bytes: bytes) -> Optional[str]:
        """Extract text using pdfminer.six as fallback"""
        try:
            from io import BytesIO
            
            resource_manager = PDFResourceManager()
            fake_file_handle = StringIO()
            converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
            
            pdf_file = BytesIO(pdf_bytes)
            pages = PDFPage.get_pages(pdf_file, maxpages=settings.max_pdf_pages)
            
            from pdfminer.pdfinterp import PDFPageInterpreter
            interpreter = PDFPageInterpreter(resource_manager, converter)
            
            for page in pages:
                interpreter.process_page(page)
            
            text = fake_file_handle.getvalue()
            fake_file_handle.close()
            converter.close()
            
            if not text or len(text.strip()) == 0:
                return None
                
            return PDFExtractor._normalize_text(text)
            
        except Exception as e:
            logger.warning(f"pdfminer extraction failed: {e}")
            return None
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize whitespace and clean up text"""
        import re
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Preserve bullet points and line breaks for lists
        text = re.sub(r'([•·▪▫◦‣⁃])', r'\n\1', text)
        text = re.sub(r'(\d+\.\s)', r'\n\1', text)  # Numbered lists
        
        # Clean up excessive newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    @classmethod
    def extract_text(cls, pdf_bytes: bytes) -> Tuple[Optional[str], str]:
        """
        Extract text from PDF bytes with fallback strategy
        Returns: (extracted_text, sha256_hash)
        """
        sha256_hash = cls.compute_sha256(pdf_bytes)
        
        # Use pdfminer.six (PyMuPDF disabled due to build requirements)
        text = cls.extract_text_pdfminer(pdf_bytes)
        if text:
            logger.info("Successfully extracted text using pdfminer")
            return text, sha256_hash
        
        logger.error("Failed to extract text from PDF")
        return None, sha256_hash
