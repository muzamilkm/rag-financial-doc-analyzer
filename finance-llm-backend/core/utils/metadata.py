"""
Metadata helper functions for consistent metadata structures.

Provides standardized metadata builders for:
- Text chunks from narrative content
- Table rows from financial statements
"""

from typing import Dict, Any, Optional


def text_metadata(company: str, year: str, doc_type: str = "financial_report") -> Dict[str, Any]:
    """
    Create standardized metadata for text chunks.
    
    Args:
        company: Company name
        year: Year or reporting period (e.g., "2025", "2025Q3")
        doc_type: Type of document (default: "financial_report")
        
    Returns:
        Dictionary with standardized text chunk metadata
    """
    return {
        "company": company,
        "period": year,  # Use 'period' key for consistency
        "doc_type": doc_type,
        "type": "text_chunk"
    }


def table_metadata(
    company: str, 
    period: str, 
    table_name: str, 
    row_id: int,
    doc_type: str = "financial_report"
) -> Dict[str, Any]:
    """
    Create standardized metadata for table rows.
    
    Args:
        company: Company name
        period: Reporting period (e.g., "2025Q3", "2024FY")
        table_name: Name of the table (e.g., "income_statement", "balance_sheet")
        row_id: Row index in the table
        doc_type: Type of document (default: "financial_report")
        
    Returns:
        Dictionary with standardized table row metadata
    """
    return {
        "company": company,
        "period": period,
        "table_name": table_name,
        "row_id": row_id,
        "doc_type": doc_type,
        "type": "table_row"
    }


def extract_company_from_text(text: str) -> Optional[str]:
    """
    Extract company name from document text.
    
    Common patterns in financial reports:
    - Board of Directors sections
    - Corporate information
    - Statement headers
    
    Args:
        text: Document text to extract from
        
    Returns:
        Company name if found, None otherwise
    """
    import re
    
    # Pattern 1: Look for "Board of Directors" or "Chairman" with company name
    patterns = [
        r'Chairman[,\s]+Board of Directors\s+([A-Z][A-Za-z\s&]+?)(?:\n|Limited|Ltd)',
        r'President & Group (?:Chief Executive Officer|CEO)\s*\n\s*([A-Z][A-Za-z\s&]+?)(?:\n|Limited|Ltd)',
        r'CONDENSED.*?FINANCIAL STATEMENTS.*?(?:OF|FOR)\s+([A-Z][A-Za-z\s&]+?)(?:\n|Limited|Ltd)',
        r'(?:NARRATIVE TEXT|EXTRACTED TABLES):\s*\d+\.pdf',  # Fallback to PDF name pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            company = match.group(1).strip()
            # Clean up common suffixes and whitespace
            company = re.sub(r'\s+(Limited|Ltd|Corporation|Corp|Inc)\.?$', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+', ' ', company)
            return company.strip()
    
    return None


def extract_period_from_text(text: str) -> Optional[str]:
    """
    Extract reporting period from document text.
    
    Common patterns:
    - "For the nine months ended September 30, 2025"
    - "Quarter ended June 30, 2024"
    - "Year ended December 31, 2023"
    - "Report 2025"
    
    Args:
        text: Document text to extract from
        
    Returns:
        Period in format like "2025Q3", "2024FY", etc.
    """
    import re
    
    # Pattern 1: "nine/six/three months ended MONTH DD, YYYY"
    quarter_map = {
        'march': 'Q1',
        'june': 'Q2', 
        'september': 'Q3',
        'december': 'Q4'
    }
    
    months_pattern = r'(?:nine|six|three)\s+months?\s+ended?\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+(\d{4})'
    match = re.search(months_pattern, text, re.IGNORECASE)
    if match:
        month = match.group(1).lower()
        year = match.group(2)
        quarter = quarter_map.get(month, 'Q4')
        return f"{year}{quarter}"
    
    # Pattern 2: "September 30, 2025" or similar date patterns
    date_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+(\d{4})'
    match = re.search(date_pattern, text, re.IGNORECASE)
    if match:
        month = match.group(1).lower()
        year = match.group(2)
        quarter = quarter_map.get(month, 'Q4')
        return f"{year}{quarter}"
    
    # Pattern 3: "Report YYYY"
    report_pattern = r'Report\s+(\d{4})'
    match = re.search(report_pattern, text, re.IGNORECASE)
    if match:
        year = match.group(1)
        return f"{year}Q3"  # Default to Q3 if not specified
    
    # Pattern 4: "Year ended December 31, YYYY" or "FY YYYY"
    fy_pattern = r'year\s+ended.*?(\d{4})|FY\s*(\d{4})'
    match = re.search(fy_pattern, text, re.IGNORECASE)
    if match:
        year = match.group(1) or match.group(2)
        return f"{year}FY"
    
    return None


def infer_table_name(df_name: str = None, page_context: str = None) -> str:
    """
    Infer a standardized table name from context.
    
    Args:
        df_name: Key name from the DataFrame dictionary
        page_context: Text context from the page containing the table
        
    Returns:
        Standardized table name
    """
    import re
    
    # If we have a DataFrame name, use it
    if df_name:
        # Normalize the name
        name = df_name.lower().replace(' ', '_')
        name = re.sub(r'[^a-z0-9_]', '', name)
        return name
    
    # If we have page context, try to infer from common patterns
    if page_context:
        context_lower = page_context.lower()
        
        # Common financial statement patterns
        if 'statement of financial position' in context_lower or 'balance sheet' in context_lower:
            return 'balance_sheet'
        elif 'statement of profit' in context_lower or 'income statement' in context_lower or 'profit and loss' in context_lower:
            return 'income_statement'
        elif 'cash flow' in context_lower:
            return 'cash_flow_statement'
        elif 'statement of changes in equity' in context_lower or 'equity' in context_lower:
            return 'equity_statement'
        elif 'segment' in context_lower:
            return 'segment_information'
        elif 'comprehensive income' in context_lower:
            return 'comprehensive_income'
    
    # Default fallback
    return 'financial_table'
