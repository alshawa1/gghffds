"""
powerbi_exporter/packager.py
============================
Integrates Star Schema Builder, Validator, DAX Generator, Theme Generator,
and Documentation Generator to produce a ZIP archive bytes buffer.
"""
import io
import zipfile
import pandas as pd
from typing import Optional, Dict, Tuple, Any

from powerbi_exporter.builder import build_star_schema
from powerbi_exporter.validator import validate_package
from powerbi_exporter.dax_generator import generate_dax_measures
from powerbi_exporter.theme_generator import generate_theme_json
from powerbi_exporter.pbit_generator import generate_pbit_bytes
from powerbi_exporter.doc_generator import (
    generate_readme_text,
    generate_relationships_df,
    generate_data_dictionary_df,
    generate_data_model_doc_df
)


def create_powerbi_zip_package(
    clean_df: pd.DataFrame,
    col_map: Dict[str, str],
    payment_df: Optional[pd.DataFrame] = None,
    payment_map: Optional[Dict[str, str]] = None
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Creates complete Power BI-Ready ZIP Package.

    Returns:
        (zip_bytes, validation_report)
    """
    # 1. Build Star Schema DataFrames
    star_schema = build_star_schema(clean_df, col_map, payment_df, payment_map)

    # 2. Validate Star Schema
    val_report = validate_package(star_schema)

    # 3. Generate DAX Measures
    dax_files = generate_dax_measures()

    # 4. Generate Theme JSON & PBIT Template
    theme_json = generate_theme_json()
    pbit_bytes = generate_pbit_bytes(clean_df, col_map, payment_df, payment_map)

    # 5. Generate Documentation
    readme_text = generate_readme_text(val_report)
    rel_df = generate_relationships_df()
    dict_df = generate_data_dictionary_df()
    doc_df = generate_data_model_doc_df()

    # Helper function to convert DataFrame to Excel Bytes
    def df_to_excel_bytes(df_to_write: pd.DataFrame, sheet_name: str = 'Data') -> bytes:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
        return out.getvalue()

    # 6. Create ZIP Archive in Memory
    zip_buffer = io.BytesIO()
    prefix = "PowerBI_Export"

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # PBIT Native Template
        zf.writestr(f"{prefix}/Maharah_Executive_Dashboard.pbit", pbit_bytes)

        # A. Data/ Excel Files
        for table_name, table_df in star_schema.items():
            excel_bytes = df_to_excel_bytes(table_df, sheet_name=table_name)
            zf.writestr(f"{prefix}/Data/{table_name}.xlsx", excel_bytes)

        # B. DAX/ Text Files
        for file_name, dax_content in dax_files.items():
            zf.writestr(f"{prefix}/DAX/{file_name}", dax_content.encode('utf-8'))

        # C. Model/ Documentation Excel Files
        zf.writestr(f"{prefix}/Model/Relationships.xlsx", df_to_excel_bytes(rel_df, 'Relationships'))
        zf.writestr(f"{prefix}/Model/Data_Dictionary.xlsx", df_to_excel_bytes(dict_df, 'Data_Dictionary'))
        zf.writestr(f"{prefix}/Model/Data_Model_Documentation.xlsx", df_to_excel_bytes(doc_df, 'Model_Overview'))

        # D. Theme/ JSON File
        zf.writestr(f"{prefix}/Theme/PowerBI_Theme.json", theme_json.encode('utf-8'))

        # E. README.txt File
        zf.writestr(f"{prefix}/README.txt", readme_text.encode('utf-8'))

    zip_bytes = zip_buffer.getvalue()
    return zip_bytes, val_report


def create_combined_excel_workbook(
    clean_df: pd.DataFrame,
    col_map: Dict[str, str],
    payment_df: Optional[pd.DataFrame] = None,
    payment_map: Optional[Dict[str, str]] = None
) -> bytes:
    """
    Creates a single combined Excel workbook containing all Star Schema tables
    as separate sheets (DimCustomer, FactDebt, FactPayment, DimCollector...).
    Power BI can import this file directly with 1 click via Get Data -> Excel Workbook!
    """
    star_schema = build_star_schema(clean_df, col_map, payment_df, payment_map)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        for table_name, table_df in star_schema.items():
            table_df.to_excel(writer, sheet_name=table_name[:31], index=False)
    return out.getvalue()

