"""
Table row serialization for pgvector preparation.

Converts DataFrame rows into text representations with metadata,
preparing them for downstream embedding and vector storage.
"""

from typing import List, Dict, Any, Union
import pandas as pd
from core.utils.metadata import table_metadata, infer_table_name


class TableRowSerializer:
    """
    Serializes table rows into text with metadata for embedding.
    
    Converts DataFrame rows to text representations without performing
    actual embedding, returning structured objects ready for pgvector.
    """
    
    def __init__(self, serialization_format: str = "key_value"):
        """
        Initialize the table row serializer.
        
        Args:
            serialization_format: Format for row serialization
                - "key_value": "Column1: Value1, Column2: Value2, ..."
                - "sentence": "The Column1 is Value1. The Column2 is Value2. ..."
                - "compact": "Column1=Value1|Column2=Value2|..."
        """
        self.serialization_format = serialization_format
    
    def serialize_row(self, 
                     row: pd.Series, 
                     table_name: str = None,
                     additional_context: Dict[str, Any] = None) -> str:
        """
        Serialize a DataFrame row to text.
        
        Args:
            row: DataFrame row (pandas Series)
            table_name: Name of the table (for context)
            additional_context: Additional key-value pairs to include
            
        Returns:
            Text representation of the row
        """
        parts = []
        
        # Add table context if available
        if table_name:
            parts.append(f"Table: {table_name}")
        
        # Add additional context
        if additional_context:
            for key, value in additional_context.items():
                if value is not None and str(value).strip():
                    parts.append(f"{key}: {value}")
        
        # Serialize the row based on format
        if self.serialization_format == "key_value":
            row_parts = []
            for col, val in row.items():
                # Skip None, NaN, or empty values
                if pd.notna(val) and str(val).strip():
                    # Clean column names (remove numbers, special chars if needed)
                    col_clean = str(col).strip()
                    val_clean = str(val).strip()
                    row_parts.append(f"{col_clean}: {val_clean}")
            
            if row_parts:
                parts.append(", ".join(row_parts))
        
        elif self.serialization_format == "sentence":
            row_parts = []
            for col, val in row.items():
                if pd.notna(val) and str(val).strip():
                    col_clean = str(col).strip()
                    val_clean = str(val).strip()
                    row_parts.append(f"The {col_clean} is {val_clean}")
            
            if row_parts:
                parts.append(". ".join(row_parts) + ".")
        
        elif self.serialization_format == "compact":
            row_parts = []
            for col, val in row.items():
                if pd.notna(val) and str(val).strip():
                    col_clean = str(col).strip()
                    val_clean = str(val).strip()
                    row_parts.append(f"{col_clean}={val_clean}")
            
            if row_parts:
                parts.append("|".join(row_parts))
        
        return " | ".join(parts) if parts else ""
    
    def serialize_dataframe(self,
                          df: pd.DataFrame,
                          company: str,
                          period: str,
                          table_name: str = None,
                          doc_type: str = "financial_report") -> List[Dict[str, Any]]:
        """
        Serialize all rows in a DataFrame with metadata.
        
        Args:
            df: DataFrame to serialize
            company: Company name
            period: Reporting period (e.g., "2025Q3")
            table_name: Name of the table (e.g., "income_statement")
            doc_type: Document type for metadata
            
        Returns:
            List of dictionaries with structure:
            {
                "text": <serialized_row>,
                "metadata": {
                    "company": <company>,
                    "period": <period>,
                    "table_name": <table_name>,
                    "row_id": <index>,
                    "doc_type": <doc_type>,
                    "type": "table_row"
                }
            }
        """
        if df is None or df.empty:
            return []
        
        # Infer table name if not provided
        if table_name is None:
            table_name = "financial_table"
        
        serialized_rows = []
        
        for idx, row in df.iterrows():
            # Serialize the row
            row_text = self.serialize_row(
                row, 
                table_name=table_name,
                additional_context={"period": period}
            )
            
            # Skip empty rows
            if not row_text or not row_text.strip():
                continue
            
            # Create row object with metadata
            row_obj = {
                "text": row_text,
                "metadata": table_metadata(
                    company=company,
                    period=period,
                    table_name=table_name,
                    row_id=int(idx) if isinstance(idx, (int, float)) else idx,
                    doc_type=doc_type
                )
            }
            
            serialized_rows.append(row_obj)
        
        return serialized_rows
    
    def serialize_dataframe_dict(self,
                                dataframes: Dict[str, pd.DataFrame],
                                company: str,
                                period: str,
                                doc_type: str = "financial_report") -> List[Dict[str, Any]]:
        """
        Serialize a dictionary of DataFrames.
        
        Args:
            dataframes: Dictionary mapping table names to DataFrames
                       e.g., {"income_statement": df1, "balance_sheet": df2}
            company: Company name
            period: Reporting period
            doc_type: Document type for metadata
            
        Returns:
            List of all serialized rows from all DataFrames
        """
        all_rows = []
        
        for table_name, df in dataframes.items():
            if df is not None and not df.empty:
                # Normalize table name
                normalized_name = infer_table_name(df_name=table_name)
                
                # Serialize this DataFrame
                rows = self.serialize_dataframe(
                    df=df,
                    company=company,
                    period=period,
                    table_name=normalized_name,
                    doc_type=doc_type
                )
                
                all_rows.extend(rows)
        
        return all_rows
    
    def serialize_tables_by_page(self,
                                tables_by_page: Dict[int, pd.DataFrame],
                                company: str,
                                period: str,
                                page_contexts: Dict[int, str] = None,
                                doc_type: str = "financial_report") -> List[Dict[str, Any]]:
        """
        Serialize tables indexed by page number.
        
        Args:
            tables_by_page: Dictionary mapping page numbers to DataFrames
            company: Company name
            period: Reporting period
            page_contexts: Optional text context for each page (for inferring table names)
            doc_type: Document type for metadata
            
        Returns:
            List of all serialized rows from all tables
        """
        all_rows = []
        
        for page_num, df in tables_by_page.items():
            if df is None or df.empty:
                continue
            
            # Try to infer table name from page context
            page_context = page_contexts.get(page_num) if page_contexts else None
            table_name = infer_table_name(page_context=page_context)
            
            # If we can't infer, use a generic name with page number
            if table_name == "financial_table":
                table_name = f"table_page_{page_num}"
            
            # Serialize this DataFrame
            rows = self.serialize_dataframe(
                df=df,
                company=company,
                period=period,
                table_name=table_name,
                doc_type=doc_type
            )
            
            all_rows.extend(rows)
        
        return all_rows


def serialize_table_rows(dataframes: Union[Dict[str, pd.DataFrame], pd.DataFrame],
                        company: str,
                        period: str,
                        table_name: str = None,
                        serialization_format: str = "key_value") -> List[Dict[str, Any]]:
    """
    Convenience function to serialize table rows.
    
    Args:
        dataframes: Either a single DataFrame or a dictionary of DataFrames
        company: Company name
        period: Reporting period (e.g., "2025Q3")
        table_name: Table name (required if dataframes is a single DataFrame)
        serialization_format: Format for serialization
        
    Returns:
        List of serialized row objects ready for embedding
    """
    serializer = TableRowSerializer(serialization_format=serialization_format)
    
    if isinstance(dataframes, pd.DataFrame):
        # Single DataFrame
        if table_name is None:
            table_name = "financial_table"
        return serializer.serialize_dataframe(dataframes, company, period, table_name)
    
    elif isinstance(dataframes, dict):
        # Dictionary of DataFrames
        return serializer.serialize_dataframe_dict(dataframes, company, period)
    
    else:
        raise TypeError("dataframes must be a DataFrame or a dictionary of DataFrames")


def serialize_extracted_tables(tables_by_page: Dict[int, pd.DataFrame],
                               company: str,
                               period: str,
                               text_by_page: Dict[int, str] = None) -> List[Dict[str, Any]]:
    """
    Convenience function to serialize tables from PDF extraction output.
    
    Args:
        tables_by_page: Dictionary mapping page numbers to DataFrames
        company: Company name
        period: Reporting period
        text_by_page: Optional text content by page (for context)
        
    Returns:
        List of serialized row objects ready for embedding
    """
    serializer = TableRowSerializer(serialization_format="key_value")
    return serializer.serialize_tables_by_page(
        tables_by_page=tables_by_page,
        company=company,
        period=period,
        page_contexts=text_by_page
    )
