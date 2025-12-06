"""
PDF text and table extraction module.

Extracts text and tables from PDF files with support for:
- Financial statements (prioritizing consolidated versions)
- Segment information tables
- Structured table extraction using multiple libraries
"""

import fitz  # PyMuPDF
import pdfplumber
import tabula
import pandas as pd
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class PDFReader:
    """Extracts text and tables from PDF financial reports."""
    
    # Financial statement patterns (prioritize consolidated)
    FINANCIAL_STATEMENT_PATTERNS = [
        r"consolidated\s+condensed\s+interim\s+statement\s+of\s+financial\s+position",
        r"consolidated\s+statement\s+of\s+financial\s+position",
        r"statement\s+of\s+financial\s+position",
        r"consolidated\s+statement\s+of\s+profit\s+or\s+loss",
        r"statement\s+of\s+profit\s+or\s+loss",
        r"profit\s+and\s+loss\s+account",
        r"consolidated\s+statement\s+of\s+cash\s+flows",
        r"statement\s+of\s+cash\s+flows",
        r"cash\s+flow\s+statement",
    ]
    
    # Segment information patterns
    SEGMENT_PATTERNS = [
        r"segment\s+information",
        r"operating\s+segment\s+results",
        r"segment\s+details",
        r"segmental\s+analysis",
        r"business\s+segment",
    ]
    
    def __init__(self, pdf_path: str):
        """Initialize PDF reader with file path."""
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def extract_text_pymupdf(self) -> Dict[int, str]:
        """Extract raw text from all pages using PyMuPDF."""
        text_by_page = {}
        
        with fitz.open(self.pdf_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                text_by_page[page_num] = text
        
        return text_by_page
    
    def extract_tables_pdfplumber(self) -> Dict[int, List[List]]:
        """Extract tables from all pages using pdfplumber."""
        tables_by_page = {}
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if tables:
                    tables_by_page[page_num] = tables
        
        return tables_by_page
    
    def extract_tables_tabula(self, silent: bool = True) -> Dict[int, pd.DataFrame]:
        """
        Extract tables from all pages using tabula-py.
        Returns pandas DataFrames for easier manipulation.
        
        Args:
            silent: If True, suppresses Java warnings from tabula
        """
        tables_dict = {}
        
        try:
            # Extract all tables from PDF as list of DataFrames
            # pages='all' extracts from all pages
            # multiple_tables=True returns list per page if multiple tables exist
            # silent=True suppresses Java warnings
            dfs = tabula.read_pdf(
                str(self.pdf_path),
                pages='all',
                multiple_tables=True,
                pandas_options={'header': None},  # Don't assume first row is header
                silent=silent,
                encoding='utf-8',
                java_options=["-Dfile.encoding=UTF-8"]
            )
            
            if dfs:
                # Tabula returns flat list, we need to map back to pages
                # For now, store sequentially with index
                for idx, df in enumerate(dfs, start=1):
                    if not df.empty:
                        tables_dict[idx] = df
            
        except UnicodeDecodeError as e:
            print(f"  ⚠ Tabula encoding error: {e}")
            print(f"  → Retrying with latin-1 encoding...")
            try:
                dfs = tabula.read_pdf(
                    str(self.pdf_path),
                    pages='all',
                    multiple_tables=True,
                    pandas_options={'header': None},
                    silent=silent,
                    encoding='latin-1'
                )
                
                if dfs:
                    for idx, df in enumerate(dfs, start=1):
                        if not df.empty:
                            tables_dict[idx] = df
                    print(f"  ✓ Successfully extracted with latin-1 encoding")
            except Exception as e2:
                print(f"  ⚠ Tabula fallback failed: {e2}")
        
        except Exception as e:
            print(f"  ⚠ Tabula extraction failed: {e}")
        
        return tables_dict
    
    def extract_tables_from_page_tabula(self, page_num: int, silent: bool = True) -> List[pd.DataFrame]:
        """Extract tables from a specific page using tabula-py."""
        try:
            dfs = tabula.read_pdf(
                str(self.pdf_path),
                pages=page_num,
                multiple_tables=True,
                pandas_options={'header': None},
                silent=silent,
                encoding='utf-8'
            )
            return [df for df in dfs if not df.empty]
        except UnicodeDecodeError:
            try:
                dfs = tabula.read_pdf(
                    str(self.pdf_path),
                    pages=page_num,
                    multiple_tables=True,
                    pandas_options={'header': None},
                    silent=silent,
                    encoding='latin-1'
                )
                return [df for df in dfs if not df.empty]
            except Exception as e:
                print(f"  ⚠ Tabula extraction failed for page {page_num}: {e}")
                return []
        except Exception as e:
            print(f"  ⚠ Tabula extraction failed for page {page_num}: {e}")
            return []
    
    def find_financial_statements(self, text_by_page: Dict[int, str]) -> Dict[str, Dict]:
        """
        Find financial statement sections in the document.
        Prioritizes consolidated versions over unconsolidated.
        """
        found_statements = {}
        
        for page_num, text in text_by_page.items():
            text_lower = text.lower()
            
            for pattern in self.FINANCIAL_STATEMENT_PATTERNS:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                
                for match in matches:
                    statement_name = match.group(0)
                    
                    # Create a key based on statement type
                    if "financial position" in statement_name:
                        key = "statement_of_financial_position"
                    elif "profit" in statement_name or "loss" in statement_name:
                        key = "statement_of_profit_or_loss"
                    elif "cash flow" in statement_name:
                        key = "statement_of_cash_flows"
                    else:
                        continue
                    
                    # Check if consolidated
                    is_consolidated = "consolidated" in statement_name
                    
                    # Only replace if new one is consolidated or we don't have one yet
                    if key not in found_statements or is_consolidated:
                        found_statements[key] = {
                            "page": page_num,
                            "header": statement_name,
                            "is_consolidated": is_consolidated,
                            "position": match.start()
                        }
        
        return found_statements
    
    def find_segment_information(self, text_by_page: Dict[int, str]) -> List[Dict]:
        """Find segment information sections in the document."""
        found_segments = []
        
        for page_num, text in text_by_page.items():
            text_lower = text.lower()
            
            for pattern in self.SEGMENT_PATTERNS:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                
                for match in matches:
                    found_segments.append({
                        "page": page_num,
                        "header": match.group(0),
                        "position": match.start()
                    })
        
        return found_segments
    
    def extract_table_at_page(self, page_num: int) -> List[List]:
        """Extract all tables from a specific page."""
        with pdfplumber.open(self.pdf_path) as pdf:
            if page_num <= len(pdf.pages):
                page = pdf.pages[page_num - 1]
                return page.extract_tables() or []
        return []
    
    def extract_all(self, use_tabula: bool = True) -> Dict:
        """
        Extract all relevant information from PDF.
        Returns structured data with text, tables, and identified sections.
        
        Args:
            use_tabula: If True, uses tabula-py for table extraction (returns DataFrames).
                       If False, uses pdfplumber (returns nested lists).
        """
        print(f"📄 Processing PDF: {self.pdf_path.name}")
        
        # Extract raw text
        print("  → Extracting text...")
        text_by_page = self.extract_text_pymupdf()
        print(f"  ✓ Extracted text from {len(text_by_page)} pages")
        
        # Extract tables
        if use_tabula:
            print("  → Extracting tables (tabula-py → DataFrames)...")
            tables_data = self.extract_tables_tabula()
            print(f"  ✓ Found {len(tables_data)} tables as DataFrames")
        else:
            print("  → Extracting tables (pdfplumber)...")
            tables_data = self.extract_tables_pdfplumber()
            print(f"  ✓ Found tables on {len(tables_data)} pages")
        
        # Find financial statements
        print("  → Identifying financial statements...")
        financial_statements = self.find_financial_statements(text_by_page)
        print(f"  ✓ Found {len(financial_statements)} financial statements")
        
        # Find segment information
        print("  → Identifying segment information...")
        segment_info = self.find_segment_information(text_by_page)
        print(f"  ✓ Found {len(segment_info)} segment sections")
        
        return {
            "pdf_name": self.pdf_path.name,
            "total_pages": len(text_by_page),
            "text_by_page": text_by_page,
            "tables_by_page": tables_data,
            "financial_statements": financial_statements,
            "segment_information": segment_info,
            "table_format": "dataframe" if use_tabula else "list"
        }


def print_extraction_summary(data: Dict):
    """Print a summary of extracted data."""
    print("\n" + "="*80)
    print(f"📊 EXTRACTION SUMMARY: {data['pdf_name']}")
    print("="*80)
    
    print(f"\n📄 Total Pages: {data['total_pages']}")
    print(f"📋 Tables Extracted: {len(data['tables_by_page'])}")
    print(f"🔧 Table Format: {data.get('table_format', 'list')}")
    
    print(f"\n💰 Financial Statements Found: {len(data['financial_statements'])}")
    for key, info in data['financial_statements'].items():
        consolidated = "✓ CONSOLIDATED" if info['is_consolidated'] else "✗ Not Consolidated"
        print(f"  • {key.replace('_', ' ').title()}")
        print(f"    - Page: {info['page']}")
        print(f"    - Status: {consolidated}")
        print(f"    - Header: {info['header']}")
    
    print(f"\n📊 Segment Information Found: {len(data['segment_information'])}")
    for seg in data['segment_information']:
        print(f"  • Page {seg['page']}: {seg['header']}")
    
    # Sample table info
    print(f"\n📈 Tables Preview:")
    table_format = data.get('table_format', 'list')
    for idx, (key, table) in enumerate(sorted(data['tables_by_page'].items())[:5], 1):
        if table_format == 'dataframe':
            print(f"  • Table {idx}: {table.shape[0]} rows × {table.shape[1]} columns")
            print(f"    Preview:\n{table.head(3).to_string(index=False)}")
        else:
            print(f"  • Page {key}: {len(table)} table(s)")
        if idx < 5 and idx < len(data['tables_by_page']):
            print()
    
    if len(data['tables_by_page']) > 5:
        print(f"  • ... and {len(data['tables_by_page']) - 5} more tables")
    
    print("\n" + "="*80)


def main():
    """Main function for testing PDF extraction."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_reader.py <path_to_pdf>")
        print("\nExample: python pdf_reader.py sample_report.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    try:
        # Extract data
        reader = PDFReader(pdf_path)
        data = reader.extract_all()
        
        # Print summary
        print_extraction_summary(data)
        
        # Optional: Print first page sample
        print("\n📝 First Page Text Sample (first 500 chars):")
        print("-" * 80)
        first_page_text = data['text_by_page'].get(1, "")
        print(first_page_text[:500])
        if len(first_page_text) > 500:
            print("...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
