"""
powerbi_exporter/theme_generator.py
====================================
Generates custom JSON theme file for Power BI.
"""
import json


def generate_theme_json() -> str:
    """
    Generates Power BI JSON Theme configuration string.
    """
    theme_data = {
        "name": "Maharah Corporate BI Theme",
        "dataColors": [
            "#1F6F2B",  # Primary Green
            "#0F4C81",  # Corporate Blue
            "#42A5F5",  # Light Blue
            "#7E57C2",  # Purple
            "#26A69A",  # Teal
            "#FF7043",  # Coral
            "#8D6E63",  # Brown
            "#78909C"   # Slate
        ],
        "good": "#2E7D32",
        "neutral": "#616161",
        "bad": "#C62828",
        "warning": "#E65100",
        "background": "#F8F9FA",
        "foreground": "#212529",
        "tableAccent": "#1F6F2B",
        "visualStyles": {
            "*": {
                "*": {
                    "fontFamily": ["Segoe UI", "Tahoma", "Arial"],
                    "fontSize": 10,
                    "border": [{
                        "show": True,
                        "color": {"solid": {"color": "#E0E0E0"}},
                        "radius": 4
                    }]
                }
            },
            "card": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
                    "labels": [{"color": {"solid": {"color": "#1F6F2B"}}, "fontSize": 18, "fontFamily": "Segoe UI"}],
                    "categoryLabels": [{"color": {"solid": {"color": "#616161"}}, "fontSize": 9}]
                }
            },
            "page": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": "#F8F9FA"}}, "transparency": 0}]
                }
            }
        }
    }
    return json.dumps(theme_data, indent=2, ensure_ascii=False)
