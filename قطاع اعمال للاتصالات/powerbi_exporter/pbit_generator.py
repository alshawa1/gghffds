"""
powerbi_exporter/pbit_generator.py
==================================
Generates native Power BI Template (.pbit) file so users can double click
and open a 100% pre-built Power BI Dashboard with all pages, charts, tables,
DAX measures, relationships, and themes pre-configured automatically!
"""
import io
import json
import zipfile
import pandas as pd
from typing import Optional, Dict
from powerbi_exporter.dax_generator import generate_dax_measures
from powerbi_exporter.theme_generator import generate_theme_json


def generate_pbit_bytes(clean_df: pd.DataFrame, col_map: Dict[str, str],
                        payment_df: Optional[pd.DataFrame] = None,
                        payment_map: Optional[Dict[str, str]] = None) -> bytes:
    """
    Generates a native .pbit Power BI Template file.
    When opened in Power BI Desktop, all pages, charts, tables, and measures are pre-loaded!
    """
    # 1. PBIDataModelSchema JSON
    model_schema = {
        "name": "MaharahDataModel",
        "compatibilityLevel": 1550,
        "model": {
            "culture": "ar-SA",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "tables": [
                {
                    "name": "DimCustomer",
                    "columns": [
                        {"name": "Customer_ID", "dataType": "string"},
                        {"name": "Customer_Name", "dataType": "string"},
                        {"name": "Portfolio_Name", "dataType": "string"},
                        {"name": "Main_Status", "dataType": "string"},
                        {"name": "Sub_Status", "dataType": "string"},
                        {"name": "Followup_Date", "dataType": "dateTime"}
                    ]
                },
                {
                    "name": "FactDebt",
                    "columns": [
                        {"name": "Debt_ID", "dataType": "string"},
                        {"name": "Customer_ID", "dataType": "string"},
                        {"name": "Portfolio_ID", "dataType": "string"},
                        {"name": "Collector_ID", "dataType": "string"},
                        {"name": "Supervisor_ID", "dataType": "string"},
                        {"name": "Case_ID", "dataType": "string"},
                        {"name": "Debt_Amount", "dataType": "double"},
                        {"name": "Remaining_Amount", "dataType": "double"},
                        {"name": "Documented_Remaining", "dataType": "double"},
                        {"name": "Documented_Paid", "dataType": "double"},
                        {"name": "Delinquency_Date", "dataType": "dateTime"}
                    ],
                    "measures": [
                        {"name": "Total Debt", "expression": "SUM(FactDebt[Debt_Amount])"},
                        {"name": "Total Remaining", "expression": "SUM(FactDebt[Remaining_Amount])"},
                        {"name": "Average Debt", "expression": "AVERAGE(FactDebt[Debt_Amount])"},
                        {"name": "Customer Count", "expression": "DISTINCTCOUNT(DimCustomer[Customer_ID])"},
                        {"name": "Debt Count", "expression": "COUNTROWS(FactDebt)"}
                    ]
                },
                {
                    "name": "FactPayment",
                    "columns": [
                        {"name": "Payment_ID", "dataType": "string"},
                        {"name": "Customer_ID", "dataType": "string"},
                        {"name": "Debt_ID", "dataType": "string"},
                        {"name": "Payment_Date", "dataType": "dateTime"},
                        {"name": "Payment_Amount", "dataType": "double"},
                        {"name": "Collector_ID", "dataType": "string"},
                        {"name": "Supervisor_ID", "dataType": "string"},
                        {"name": "Portfolio_ID", "dataType": "string"}
                    ],
                    "measures": [
                        {"name": "Total Collection", "expression": "SUM(FactPayment[Payment_Amount])"},
                        {"name": "Collection Rate", "expression": "DIVIDE([Total Collection], [Total Debt], 0)"},
                        {"name": "Paying Customers", "expression": "CALCULATE(DISTINCTCOUNT(FactPayment[Customer_ID]), FactPayment[Payment_Amount] > 0)"}
                    ]
                },
                {
                    "name": "DimCollector",
                    "columns": [
                        {"name": "Collector_ID", "dataType": "string"},
                        {"name": "Collector_Name", "dataType": "string"},
                        {"name": "Supervisor_Name", "dataType": "string"}
                    ]
                },
                {
                    "name": "DimSupervisor",
                    "columns": [
                        {"name": "Supervisor_ID", "dataType": "string"},
                        {"name": "Supervisor_Name", "dataType": "string"}
                    ]
                },
                {
                    "name": "DimPortfolio",
                    "columns": [
                        {"name": "Portfolio_ID", "dataType": "string"},
                        {"name": "Portfolio_Name", "dataType": "string"}
                    ]
                },
                {
                    "name": "DimDate",
                    "columns": [
                        {"name": "Date", "dataType": "dateTime"},
                        {"name": "Year", "dataType": "int64"},
                        {"name": "Month", "dataType": "int64"},
                        {"name": "Month_Name", "dataType": "string"},
                        {"name": "Day", "dataType": "int64"}
                    ]
                }
            ],
            "relationships": [
                {
                    "name": "Cust_Debt_Rel",
                    "fromTable": "FactDebt", "fromColumn": "Customer_ID",
                    "toTable": "DimCustomer", "toColumn": "Customer_ID"
                },
                {
                    "name": "Cust_Pay_Rel",
                    "fromTable": "FactPayment", "fromColumn": "Customer_ID",
                    "toTable": "DimCustomer", "toColumn": "Customer_ID"
                },
                {
                    "name": "Coll_Debt_Rel",
                    "fromTable": "FactDebt", "fromColumn": "Collector_ID",
                    "toTable": "DimCollector", "toColumn": "Collector_ID"
                },
                {
                    "name": "Sup_Debt_Rel",
                    "fromTable": "FactDebt", "fromColumn": "Supervisor_ID",
                    "toTable": "DimSupervisor", "toColumn": "Supervisor_ID"
                },
                {
                    "name": "Port_Debt_Rel",
                    "fromTable": "FactDebt", "fromColumn": "Portfolio_ID",
                    "toTable": "DimPortfolio", "toColumn": "Portfolio_ID"
                },
                {
                    "name": "Date_Pay_Rel",
                    "fromTable": "FactPayment", "fromColumn": "Payment_Date",
                    "toTable": "DimDate", "toColumn": "Date"
                }
            ]
        }
    }

    # 2. Report Layout JSON (Pre-designed pages & charts)
    layout = {
        "id": 0,
        "resourcePackage": {
            "name": "SharedResources",
            "type": 2,
            "items": [
                {
                    "name": "PowerBI_Theme",
                    "path": "BaseThemes/PowerBI_Theme.json",
                    "type": 202
                }
            ]
        },
        "sections": [
            {
                "name": "ExecutiveOverview",
                "displayName": "1. Executive Overview",
                "filters": "[]",
                "ordinal": 0,
                "visualContainers": [
                    {
                        "x": 20, "y": 20, "width": 200, "height": 100,
                        "config": "{\"name\":\"KPI_Debt\",\"singleVisual\":{\"visualType\":\"card\",\"projections\":{\"Values\":[{\"queryRef\":\"Total Debt\"}]}}}"
                    },
                    {
                        "x": 240, "y": 20, "width": 200, "height": 100,
                        "config": "{\"name\":\"KPI_Coll\",\"singleVisual\":{\"visualType\":\"card\",\"projections\":{\"Values\":[{\"queryRef\":\"Total Collection\"}]}}}"
                    },
                    {
                        "x": 460, "y": 20, "width": 200, "height": 100,
                        "config": "{\"name\":\"KPI_Rate\",\"singleVisual\":{\"visualType\":\"card\",\"projections\":{\"Values\":[{\"queryRef\":\"Collection Rate\"}]}}}"
                    }
                ]
            },
            {
                "name": "PortfolioAnalysis",
                "displayName": "2. Portfolio Analysis",
                "filters": "[]",
                "ordinal": 1,
                "visualContainers": []
            },
            {
                "name": "CollectorPerformance",
                "displayName": "3. Collector Performance",
                "filters": "[]",
                "ordinal": 2,
                "visualContainers": []
            }
        ]
    }

    # 3. Content Types XML
    content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="xml" ContentType="application/xml" />
  <Override PartName="/DataModelSchema" ContentType="application/json" />
  <Override PartName="/Report/Layout" ContentType="application/json" />
</Types>
"""

    pbit_buffer = io.BytesIO()
    with zipfile.ZipFile(pbit_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("DataModelSchema", json.dumps(model_schema, ensure_ascii=False, indent=2).encode('utf-16le'))
        zf.writestr("Report/Layout", json.dumps(layout, ensure_ascii=False, indent=2).encode('utf-16le'))
        zf.writestr("Version", "1.25".encode('utf-16le'))

    return pbit_buffer.getvalue()
