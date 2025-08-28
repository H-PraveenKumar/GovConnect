"""
PDF service for text extraction and processing
"""
import fitz  # PyMuPDF
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams
import logging
import re
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFService:
    """Service for PDF processing and text extraction"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
    
    def extract_text_pymupdf(self, pdf_content: bytes) -> str:
        """Extract text using PyMuPDF (fitz) - faster and more reliable"""
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
            
            doc.close()
            
            # Clean up the extracted text
            cleaned_text = self._clean_text(text)
            logger.info(f"Successfully extracted text using PyMuPDF: {len(cleaned_text)} characters")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            raise
    
    def extract_text_pdfminer(self, pdf_content: bytes) -> str:
        """Extract text using pdfminer.six - fallback method"""
        try:
            # Configure layout analysis parameters
            laparams = LAParams(
                line_margin=0.5,
                word_margin=0.1,
                char_margin=2.0,
                boxes_flow=0.5,
                detect_vertical=True
            )
            
            # Extract text with custom parameters
            text = extract_text(
                stream=pdf_content,
                laparams=laparams
            )
            
            # Clean up the extracted text
            cleaned_text = self._clean_text(text)
            logger.info(f"Successfully extracted text using pdfminer: {len(cleaned_text)} characters")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"pdfminer extraction failed: {e}")
            raise
    
    def extract_text(self, pdf_content: bytes, method: str = "auto") -> str:
        """Extract text from PDF content using the best available method"""
        if method == "auto":
            # Try PyMuPDF first, fallback to pdfminer
            try:
                return self.extract_text_pymupdf(pdf_content)
            except Exception as e:
                logger.warning(f"PyMuPDF failed, trying pdfminer: {e}")
                try:
                    return self.extract_text_pdfminer(pdf_content)
                except Exception as e2:
                    logger.error(f"Both extraction methods failed: {e2}")
                    raise RuntimeError(f"PDF text extraction failed: {e2}")
        
        elif method == "pymupdf":
            return self.extract_text_pymupdf(pdf_content)
        
        elif method == "pdfminer":
            return self.extract_text_pdfminer(pdf_content)
        
        else:
            raise ValueError(f"Unknown extraction method: {method}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove common PDF artifacts
        text = re.sub(r'[^\w\s\-.,;:!?()[\]{}"\']', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def extract_metadata(self, pdf_content: bytes) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            
            metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
                "file_size": len(pdf_content)
            }
            
            doc.close()
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {e}")
            return {
                "page_count": 0,
                "file_size": len(pdf_content)
            }
    
    def extract_scheme_name(self, text: str) -> str:
        """Extract scheme name from PDF text"""
        # Look for common patterns in government scheme names
        patterns = [
            r'(?:Pradhan Mantri|PM)\s+([A-Z][A-Za-z\s]+?)(?:Scheme|Yojana|Program|Initiative)',
            r'([A-Z][A-Za-z\s]+?)(?:Scheme|Yojana|Program|Initiative)',
            r'(?:Government|Central|State)\s+([A-Z][A-Za-z\s]+?)(?:Scheme|Program)',
            r'([A-Z][A-Za-z\s]+?)\s+(?:Benefit|Support|Assistance|Grant)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scheme_name = match.group(1).strip()
                if len(scheme_name) > 5:  # Avoid very short matches
                    return scheme_name
        
        # Fallback: extract first meaningful title-like text
        lines = text.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if (len(line) > 10 and 
                line.isupper() or 
                line[0].isupper() and 
                not line.startswith('Page') and
                not line.isdigit()):
                return line[:100]  # Limit length
        
        return "Unknown Scheme"
    
    def extract_eligibility_section(self, text: str) -> str:
        """Extract eligibility-related text from PDF"""
        # Common keywords that indicate eligibility sections
        eligibility_keywords = [
            'eligibility', 'eligible', 'qualification', 'criteria',
            'requirements', 'who can apply', 'applicant must',
            'conditions', 'prerequisites', 'qualifying criteria'
        ]
        
        # Look for sections containing eligibility information
        text_lower = text.lower()
        eligibility_text = ""
        
        # Split text into paragraphs
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            if any(keyword in paragraph_lower for keyword in eligibility_keywords):
                eligibility_text += paragraph + "\n\n"
        
        # If no specific eligibility section found, look for common patterns
        if not eligibility_text:
            # Look for bullet points or numbered lists that might contain criteria
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if (line.startswith(('•', '-', '*', '1.', '2.', '3.')) and
                    any(keyword in line.lower() for keyword in ['age', 'income', 'caste', 'occupation', 'education'])):
                    # Include this line and a few following lines
                    eligibility_text += '\n'.join(lines[i:i+5]) + "\n\n"
        
        return eligibility_text.strip() if eligibility_text else text[:2000]  # Fallback to first 2000 chars
    
    def validate_pdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """Validate PDF file and return validation results"""
        try:
            # Check file size
            file_size = len(pdf_content)
            
            # Try to open PDF
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_count = len(doc)
            doc.close()
            
            # Check if text extraction works
            try:
                text = self.extract_text(pdf_content)
                text_length = len(text)
                text_extraction_success = True
            except Exception:
                text_length = 0
                text_extraction_success = False
            
            validation_result = {
                "is_valid": True,
                "file_size": file_size,
                "page_count": page_count,
                "text_extraction_success": text_extraction_success,
                "text_length": text_length,
                "errors": []
            }
            
            # Add warnings for potential issues
            if file_size > 50 * 1024 * 1024:  # 50MB
                validation_result["warnings"] = ["File size is large, may take time to process"]
            
            if page_count > 100:
                validation_result["warnings"] = ["Document has many pages, processing may be slow"]
            
            if text_length < 100:
                validation_result["warnings"] = ["Extracted text seems very short, may be image-based PDF"]
            
            return validation_result
            
        except Exception as e:
            return {
                "is_valid": False,
                "file_size": len(pdf_content),
                "page_count": 0,
                "text_extraction_success": False,
                "text_length": 0,
                "errors": [str(e)]
            }


# Global PDF service instance
pdf_service = PDFService()
