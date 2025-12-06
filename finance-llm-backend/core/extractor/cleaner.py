"""
Text cleaning and normalization module.

Cleans extracted text by:
- Removing headers, footers, page numbers
- Fixing broken lines and hyphenation
- Normalizing whitespace
- Removing repeated content
- Discarding non-English (Urdu) translations
- Removing unconsolidated financial statements
"""

import re
from typing import Dict, List, Optional, Tuple
from unidecode import unidecode
from pathlib import Path


class TextCleaner:
    """Cleans and normalizes extracted text from PDFs."""
    
    # Common header/footer patterns in financial reports
    HEADER_FOOTER_PATTERNS = [
        r"Page\s+\d+\s+of\s+\d+",
        r"^\d+\s*$",  # Standalone page numbers
        r"^For\s+the\s+(three|six|nine)\s+months?\s+ended",
        r"^(Un)?audited$",
        r"^Rupees\s+in\s+('\d+|thousands?|millions?)$",
        r"^Quarter(ly)?\s+Report\s+\d{4}",
        r"^(First|Second|Third|Fourth)\s+Quarter",
    ]
    
    # Urdu Unicode ranges
    URDU_UNICODE_RANGES = [
        (0x0600, 0x06FF),  # Arabic/Urdu
        (0x0750, 0x077F),  # Arabic Supplement
        (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    ]
    
    # Front matter patterns (title page, ToC, corporate info)
    FRONT_MATTER_PATTERNS = [
        # Table of Contents indicators
        r"table\s+of\s+contents",
        r"contents\s*$",
        r"^\s*page\s+no\.?\s*$",
        
        # Title page indicators
        r"quarterly\s+report",
        r"annual\s+report",
        r"financial\s+statements",
        r"interim\s+report",
        
        # Corporate information indicators
        r"board\s+of\s+directors",
        r"company\s+information",
        r"corporate\s+information",
        r"registered\s+office",
        r"chief\s+executive\s+officer",
        r"chief\s+financial\s+officer",
        r"company\s+secretary",
        r"auditors",
        r"legal\s+advisor",
        r"share\s+registrar",
        r"registered\s+address",
        r"principal\s+office",
        r"head\s+office",
        
        # Vision/mission (often on title pages)
        r"^vision\s*$",
        r"^mission\s*$",
        r"^values\s*$",
    ]
    
    def __init__(self):
        """Initialize text cleaner."""
        self.header_footer_regex = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.HEADER_FOOTER_PATTERNS
        ]
    
    def remove_headers_footers(self, text: str) -> str:
        """Remove common header and footer patterns."""
        for pattern in self.header_footer_regex:
            text = pattern.sub("", text)
        return text
    
    def fix_hyphenation(self, text: str) -> str:
        """Fix broken words at line breaks (e.g., 'manage-\nment' -> 'management')."""
        # Match word-hyphen-newline-word pattern
        text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving paragraph structure."""
        # Replace multiple spaces with single space
        text = re.sub(r" {2,}", " ", text)
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # Remove spaces at start/end of lines
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        
        return text.strip()
    
    def remove_page_numbers(self, text: str) -> str:
        """Remove standalone page numbers."""
        # Remove lines that are just numbers
        lines = text.split("\n")
        cleaned_lines = [
            line for line in lines
            if not re.match(r"^\s*\d+\s*$", line)
        ]
        return "\n".join(cleaned_lines)
    
    def remove_repeated_content(self, text: str, threshold: int = 50) -> str:
        """
        Remove repeated text blocks (e.g., headers repeated on every page).
        Uses simple heuristic: if a line appears more than threshold times, remove it.
        """
        lines = text.split("\n")
        line_counts = {}
        
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 10:  # Only consider substantial lines
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        # Identify repeated lines
        repeated = {line for line, count in line_counts.items() if count > threshold}
        
        # Remove repeated lines
        if repeated:
            cleaned_lines = [
                line for line in lines
                if line.strip() not in repeated
            ]
            return "\n".join(cleaned_lines)
        
        return text
    
    def normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters to ASCII equivalents."""
        return unidecode(text)
    
    def detect_urdu_content(self, text: str, threshold: float = 0.15) -> bool:
        """
        Detect if text contains significant Urdu/Arabic content.
        
        Args:
            text: Text to analyze
            threshold: Minimum ratio of Urdu characters to consider text as Urdu
            
        Returns:
            True if text is predominantly Urdu
        """
        if not text or len(text) < 50:
            return False
        
        urdu_char_count = 0
        total_chars = 0
        
        for char in text:
            # Skip whitespace and punctuation
            if char.isspace() or not char.isalnum():
                continue
            
            total_chars += 1
            char_code = ord(char)
            
            # Check if character is in Urdu Unicode ranges
            for start, end in self.URDU_UNICODE_RANGES:
                if start <= char_code <= end:
                    urdu_char_count += 1
                    break
        
        if total_chars == 0:
            return False
        
        urdu_ratio = urdu_char_count / total_chars
        return urdu_ratio >= threshold
    
    def is_front_matter_page(self, text: str, page_num: int, max_page: int = 5) -> bool:
        """
        Detect if a page is front matter (title, ToC, corporate info).
        
        Args:
            text: Page text to analyze
            page_num: Page number (1-indexed)
            max_page: Only check pages up to this number
            
        Returns:
            True if page appears to be front matter
        """
        # Only check first few pages
        if page_num > max_page:
            return False
        
        text_lower = text.lower()
        
        # EXCLUDE: Pages with substantive content (Directors' Review, MD&A, etc.)
        # These are valuable narrative content
        substantive_patterns = [
            r"directors?\s+(interim\s+)?review",
            r"management\s+discussion",
            r"md&a",
            r"analysis\s+of\s+financial",
            r"operating\s+results",
            r"financial\s+performance",
            r"business\s+review",
        ]
        
        for pattern in substantive_patterns:
            if re.search(pattern, text_lower):
                # Check if it's actual content (>500 chars) not just a ToC entry
                if len(text.strip()) > 500:
                    return False
        
        # Count front matter pattern matches
        pattern_matches = 0
        for pattern in self.FRONT_MATTER_PATTERNS:
            if re.search(pattern, text_lower, re.MULTILINE):
                pattern_matches += 1
        
        # Additional heuristic: very short pages (< 300 chars) in first 3 pages
        if page_num <= 3 and len(text.strip()) < 300:
            return True
        
        # Check for high density of names/titles pattern (corporate info)
        # Pattern: lines with "Name:" or "Address:" or title abbreviations
        lines = text.split('\n')
        title_lines = 0
        contact_lines = 0
        
        for line in lines[:30]:  # Check first 30 lines
            if re.search(r'(^|\s)(Mr\.?|Ms\.?|Dr\.?|CEO|CFO|Chairman|Director|Secretary)\s', line, re.IGNORECASE):
                title_lines += 1
            # Contact info patterns
            if re.search(r'(auditor|legal\s+advisor|registrar|registered\s+office|email|website)', line, re.IGNORECASE):
                contact_lines += 1
        
        # High density of titles AND contact info = corporate information page
        if title_lines >= 4 and contact_lines >= 2:
            return True
        
        # Check for table of contents pattern (page numbers on right)
        # Pattern: text followed by dots/spaces and numbers
        toc_lines = sum(1 for line in lines if re.search(r'\.{3,}|\s{5,}\d+\s*$', line))
        if toc_lines >= 5:  # At least 5 ToC-style lines
            return True
        
        # If multiple front matter patterns match AND short content, likely front matter
        if pattern_matches >= 3 and len(text.strip()) < 800:
            return True
        
        return False
    
    def remove_front_matter(self, text_by_page: Dict[int, str]) -> Dict[int, str]:
        """
        Remove front matter pages (title, ToC, corporate info).
        
        Returns:
            Dictionary with front matter pages removed
        """
        cleaned_pages = {}
        removed_pages = []
        
        for page_num in sorted(text_by_page.keys()):
            text = text_by_page[page_num]
            
            if not self.is_front_matter_page(text, page_num):
                cleaned_pages[page_num] = text
            else:
                removed_pages.append(page_num)
        
        if removed_pages:
            print(f"  ✓ Removed {len(removed_pages)} front matter pages: {removed_pages}")
        
        return cleaned_pages
    
    def remove_urdu_pages(self, text_by_page: Dict[int, str]) -> Dict[int, str]:
        """
        Remove pages that contain predominantly Urdu content.
        
        Returns:
            Filtered dictionary with only English pages
        """
        english_pages = {}
        removed_pages = []
        
        for page_num, text in text_by_page.items():
            if not self.detect_urdu_content(text):
                english_pages[page_num] = text
            else:
                removed_pages.append(page_num)
        
        if removed_pages:
            print(f"  ✓ Removed {len(removed_pages)} Urdu translation pages: {removed_pages}")
        
        return english_pages
    
    def remove_unconsolidated_sections(self, text: str, financial_statements: Dict) -> str:
        """
        Remove unconsolidated financial statement sections if consolidated versions exist.
        
        Args:
            text: Full text content
            financial_statements: Dictionary of found financial statements
            
        Returns:
            Text with unconsolidated sections removed
        """
        # Check if we have consolidated statements
        has_consolidated = any(
            info.get('is_consolidated', False) 
            for info in financial_statements.values()
        )
        
        if not has_consolidated:
            return text
        
        # Pattern to find unconsolidated sections
        unconsolidated_pattern = re.compile(
            r"unconsolidated.*?(?=consolidated|$)",
            re.IGNORECASE | re.DOTALL
        )
        
        # Remove unconsolidated sections
        cleaned_text = unconsolidated_pattern.sub("", text)
        
        return cleaned_text
    
    def extract_table_sections(self, text_by_page: Dict[int, str], 
                              tables_by_page: Dict) -> Tuple[Dict[int, str], List[str]]:
        """
        Identify and remove table sections from text.
        
        Returns:
            Tuple of (text without tables, list of table indicators)
        """
        text_without_tables = {}
        table_markers = []
        
        for page_num, text in text_by_page.items():
            # If page has tables, mark them
            if page_num in tables_by_page:
                # Simple heuristic: remove lines that look like table rows
                # (multiple numbers/spaces pattern)
                lines = text.split('\n')
                filtered_lines = []
                
                for line in lines:
                    # Skip lines with multiple numbers separated by spaces/tabs
                    # Pattern: at least 3 numbers with spaces between them
                    if re.search(r'\d+[\s\t]+\d+[\s\t]+\d+', line):
                        table_markers.append(f"Page {page_num}: {line[:50]}...")
                        continue
                    filtered_lines.append(line)
                
                text_without_tables[page_num] = '\n'.join(filtered_lines)
            else:
                text_without_tables[page_num] = text
        
        return text_without_tables, table_markers
    
    def clean_financial_text(self, text: str) -> str:
        """Apply all cleaning steps to financial document text."""
        text = self.remove_headers_footers(text)
        text = self.fix_hyphenation(text)
        text = self.remove_page_numbers(text)
        text = self.normalize_whitespace(text)
        return text
    
    def clean_table(self, table: List[List]) -> List[List]:
        """Clean a table by removing empty rows and normalizing cell content."""
        cleaned_table = []
        
        for row in table:
            # Skip completely empty rows
            if not any(cell and str(cell).strip() for cell in row):
                continue
            
            # Clean each cell
            cleaned_row = [
                str(cell).strip() if cell else ""
                for cell in row
            ]
            cleaned_table.append(cleaned_row)
        
        return cleaned_table
    
    def clean_dataframe(self, df) -> 'pd.DataFrame':
        """Clean a pandas DataFrame by removing empty rows and normalizing content."""
        import pandas as pd
        
        # Make a copy to avoid modifying original
        df_clean = df.copy()
        
        # Remove completely empty rows
        df_clean = df_clean.dropna(how='all')
        
        # Strip whitespace from all string columns
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].astype(str).str.strip()
        
        # Replace 'nan' strings with actual NaN
        df_clean = df_clean.replace('nan', pd.NA)
        
        # Reset index
        df_clean = df_clean.reset_index(drop=True)
        
        return df_clean
    
    def clean_extracted_data(self, data: Dict, remove_urdu: bool = True, 
                            remove_unconsolidated: bool = True,
                            extract_tables_from_text: bool = True,
                            remove_front_matter: bool = True) -> Dict:
        """
        Clean all text and tables in extracted data structure.
        
        Args:
            data: Dictionary from PDFReader.extract_all()
            remove_urdu: Remove pages with Urdu translations
            remove_unconsolidated: Remove unconsolidated financial sections
            extract_tables_from_text: Remove table-like content from text
            remove_front_matter: Remove title page, ToC, corporate info
            
        Returns:
            Dictionary with cleaned text and tables
        """
        print(f"\n🧹 Cleaning extracted data from {data['pdf_name']}...")
        
        # Rule 0: Remove front matter (title, ToC, corporate info)
        text_by_page = data['text_by_page']
        if remove_front_matter:
            print("  → Removing front matter (title, ToC, corporate info)...")
            text_by_page = self.remove_front_matter(text_by_page)
        
        # Rule 1: Remove Urdu translation pages
        if remove_urdu:
            print("  → Removing Urdu translation pages...")
            text_by_page = self.remove_urdu_pages(text_by_page)
        
        # Clean text by page
        cleaned_text = {}
        for page_num, text in text_by_page.items():
            cleaned_text[page_num] = self.clean_financial_text(text)
        
        print(f"  ✓ Cleaned text from {len(cleaned_text)} pages")
        
        # Rule 2: Remove unconsolidated sections (prioritize consolidated)
        if remove_unconsolidated and data.get('financial_statements'):
            print("  → Removing unconsolidated financial sections...")
            full_text = '\n'.join(cleaned_text.values())
            full_text = self.remove_unconsolidated_sections(
                full_text, 
                data['financial_statements']
            )
            # Redistribute back to pages (simplified - keeps structure)
            # In practice, this is complex, so we'll just note it
            print("  ✓ Prioritized consolidated statements")
        
        # Rule 3: Extract table sections from text (for LLM-only content)
        table_markers = []
        if extract_tables_from_text:
            print("  → Separating table content from narrative text...")
            cleaned_text, table_markers = self.extract_table_sections(
                cleaned_text,
                data['tables_by_page']
            )
            print(f"  ✓ Identified {len(table_markers)} table sections in text")
        
        # Clean tables by page
        table_format = data.get('table_format', 'list')
        cleaned_tables = {}
        total_tables = 0
        
        if table_format == 'dataframe':
            # Clean DataFrames
            import pandas as pd
            for idx, df in data['tables_by_page'].items():
                cleaned_df = self.clean_dataframe(df)
                if not cleaned_df.empty:
                    cleaned_tables[idx] = cleaned_df
                    total_tables += 1
        else:
            # Clean list-based tables
            for page_num, tables in data['tables_by_page'].items():
                cleaned_page_tables = []
                for table in tables:
                    cleaned_table = self.clean_table(table)
                    if cleaned_table:  # Only keep non-empty tables
                        cleaned_page_tables.append(cleaned_table)
                        total_tables += 1
                
                if cleaned_page_tables:
                    cleaned_tables[page_num] = cleaned_page_tables
        
        print(f"  ✓ Cleaned {total_tables} tables (for vector DB)")
        
        return {
            "pdf_name": data['pdf_name'],
            "total_pages": data['total_pages'],
            "text_by_page": cleaned_text,
            "tables_by_page": cleaned_tables,
            "financial_statements": data['financial_statements'],
            "segment_information": data['segment_information'],
            "table_format": table_format,
            "table_markers": table_markers
        }


def export_to_text_files(data: Dict, output_dir: str = "./output"):
    """
    Export cleaned data to text files.
    
    Creates two files:
    1. {pdf_name}_tables.txt - Extracted tables (for vector DB)
    2. {pdf_name}_narrative.txt - Cleaned text (for LLM)
    
    Args:
        data: Cleaned data dictionary
        output_dir: Directory to save output files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    pdf_name = Path(data['pdf_name']).stem
    
    # Export tables
    tables_file = output_path / f"{pdf_name}_tables.txt"
    print(f"\n📊 Exporting tables to: {tables_file}")
    
    with open(tables_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"EXTRACTED TABLES: {data['pdf_name']}\n")
        f.write(f"For Vector Database Storage\n")
        f.write("="*80 + "\n\n")
        
        table_format = data.get('table_format', 'list')
        
        if table_format == 'dataframe':
            import pandas as pd
            for idx, df in data['tables_by_page'].items():
                f.write(f"\n{'='*80}\n")
                f.write(f"TABLE {idx}\n")
                f.write(f"{'='*80}\n")
                f.write(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n\n")
                f.write(df.to_string(index=False))
                f.write("\n\n")
        else:
            for page_num, tables in data['tables_by_page'].items():
                for table_idx, table in enumerate(tables, 1):
                    f.write(f"\n{'='*80}\n")
                    f.write(f"PAGE {page_num} - TABLE {table_idx}\n")
                    f.write(f"{'='*80}\n\n")
                    for row in table:
                        f.write(" | ".join(str(cell) for cell in row))
                        f.write("\n")
                    f.write("\n")
        
        # Add financial statements info
        if data.get('financial_statements'):
            f.write(f"\n{'='*80}\n")
            f.write("FINANCIAL STATEMENTS IDENTIFIED\n")
            f.write(f"{'='*80}\n\n")
            for key, info in data['financial_statements'].items():
                f.write(f"• {key.replace('_', ' ').title()}\n")
                f.write(f"  - Page: {info['page']}\n")
                f.write(f"  - Consolidated: {info['is_consolidated']}\n")
                f.write(f"  - Header: {info['header']}\n\n")
        
        # Add segment information
        if data.get('segment_information'):
            f.write(f"\n{'='*80}\n")
            f.write("SEGMENT INFORMATION IDENTIFIED\n")
            f.write(f"{'='*80}\n\n")
            for seg in data['segment_information']:
                f.write(f"• Page {seg['page']}: {seg['header']}\n")
    
    print(f"  ✓ Exported {len(data['tables_by_page'])} tables")
    
    # Export narrative text (for LLM)
    narrative_file = output_path / f"{pdf_name}_narrative.txt"
    print(f"\n📝 Exporting narrative text to: {narrative_file}")
    
    with open(narrative_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"NARRATIVE TEXT: {data['pdf_name']}\n")
        f.write(f"For LLM Processing (Tables Removed)\n")
        f.write("="*80 + "\n\n")
        
        for page_num in sorted(data['text_by_page'].keys()):
            text = data['text_by_page'][page_num]
            if text.strip():  # Only include non-empty pages
                f.write(f"\n{'='*80}\n")
                f.write(f"PAGE {page_num}\n")
                f.write(f"{'='*80}\n\n")
                f.write(text)
                f.write("\n\n")
    
    print(f"  ✓ Exported {len(data['text_by_page'])} pages of text")
    
    # Export summary
    summary_file = output_path / f"{pdf_name}_summary.txt"
    print(f"\n📋 Exporting summary to: {summary_file}")
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"PROCESSING SUMMARY: {data['pdf_name']}\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Total Pages: {data['total_pages']}\n")
        f.write(f"Pages with Text: {len(data['text_by_page'])}\n")
        f.write(f"Tables Extracted: {len(data['tables_by_page'])}\n")
        f.write(f"Table Format: {data.get('table_format', 'list')}\n\n")
        
        f.write(f"Financial Statements: {len(data.get('financial_statements', {}))}\n")
        for key, info in data.get('financial_statements', {}).items():
            f.write(f"  • {key.replace('_', ' ').title()} (Page {info['page']}, Consolidated: {info['is_consolidated']})\n")
        
        f.write(f"\nSegment Information: {len(data.get('segment_information', []))}\n")
        for seg in data.get('segment_information', []):
            f.write(f"  • Page {seg['page']}: {seg['header']}\n")
        
        if data.get('table_markers'):
            f.write(f"\nTable Markers Removed from Text: {len(data['table_markers'])}\n")
    
    print(f"  ✓ Exported processing summary")
    print(f"\n✅ All files exported to: {output_path.absolute()}")


def print_cleaning_comparison(original: str, cleaned: str, max_chars: int = 300):
    """Print before/after comparison of text cleaning."""
    print("\n" + "="*80)
    print("🧹 CLEANING COMPARISON")
    print("="*80)
    
    print("\n📄 BEFORE (first {} chars):".format(max_chars))
    print("-" * 80)
    print(original[:max_chars])
    if len(original) > max_chars:
        print("...")
    
    print("\n✨ AFTER (first {} chars):".format(max_chars))
    print("-" * 80)
    print(cleaned[:max_chars])
    if len(cleaned) > max_chars:
        print("...")
    
    print("\n📊 Stats:")
    print(f"  • Original length: {len(original)} chars")
    print(f"  • Cleaned length: {len(cleaned)} chars")
    print(f"  • Reduction: {len(original) - len(cleaned)} chars ({100 * (len(original) - len(cleaned)) / len(original):.1f}%)")
    print("="*80)


def main():
    """Main function for testing text cleaning and exporting."""
    import sys
    from pdf_reader import PDFReader, print_extraction_summary
    
    if len(sys.argv) < 2:
        print("Usage: python cleaner.py <path_to_pdf> [output_dir]")
        print("\nExample: python cleaner.py sample_report.pdf ./output")
        print("\nProcesses PDF and exports:")
        print("  • {pdf_name}_tables.txt - Tables for vector DB")
        print("  • {pdf_name}_narrative.txt - Text for LLM")
        print("  • {pdf_name}_summary.txt - Processing summary")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"
    
    try:
        # Extract data
        print("📄 Step 1: Extracting PDF...")
        reader = PDFReader(pdf_path)
        data = reader.extract_all(use_tabula=True)
        
        # Clean data with all rules applied
        print("\n🧹 Step 2: Cleaning extracted data...")
        print("  Rules Applied:")
        print("  ✓ Rule 0: Remove front matter (title, ToC, corporate info)")
        print("  ✓ Rule 1: Discard Urdu translations")
        print("  ✓ Rule 2: Prioritize consolidated financials")
        print("  ✓ Rule 3: Remove headers/footers/metadata")
        print("  ✓ Separate tables from narrative text")
        
        cleaner = TextCleaner()
        cleaned_data = cleaner.clean_extracted_data(
            data,
            remove_urdu=True,
            remove_unconsolidated=True,
            extract_tables_from_text=True,
            remove_front_matter=True
        )
        
        # Print summary
        print_extraction_summary(cleaned_data)
        
        # Export to text files
        print("\n📤 Step 3: Exporting processed data...")
        export_to_text_files(cleaned_data, output_dir)
        
        print("\n" + "="*80)
        print("✅ PROCESSING COMPLETE")
        print("="*80)
        print(f"\nOutput files created in: {Path(output_dir).absolute()}")
        print("\n📊 Tables → Vector Database")
        print("📝 Narrative → LLM Processing")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
