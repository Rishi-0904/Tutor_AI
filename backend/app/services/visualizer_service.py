import json
import math
from typing import Dict, Any, List
from app.core.config import settings
from google import genai as google_genai
from google.genai import types

def evaluate_math_expression(expression: str) -> List[Dict[str, float]]:
    """
    Calculates x, y coordinates from -10 to 10 for plotting.
    Replaces common math operators with python equivalents.
    """
    points = []
    expr_clean = (
        expression.replace("^", "**")
        .replace("sin", "math.sin")
        .replace("cos", "math.cos")
        .replace("tan", "math.tan")
        .replace("pi", "math.pi")
        .replace("log", "math.log")
        .replace("exp", "math.exp")
        .replace("sqrt", "math.sqrt")
    )
    
    # Generate 150 points for high-definition curves
    for x_idx in range(-100, 101):
        x = x_idx / 10.0
        try:
            # Evaluate y with safe math functions
            y = eval(expr_clean, {"x": x, "math": math})
            if isinstance(y, (int, float)) and not math.isnan(y) and not math.isinf(y):
                # Clamp y to prevent extreme scales
                if -100 <= y <= 100:
                    points.append({"x": round(x, 2), "y": round(y, 4)})
        except:
            continue
            
    return points[:150]

def generate_visual_data(prompt: str, subject: str) -> Dict[str, Any]:
    """
    Categorizes the user request and generates structured semantic JSON data.
    """
    fallback_response = {
        "type": "error",
        "message": "Unable to load visualization due to configuration issues."
    }
    
    api_key = settings.gemini_api_key
    if not api_key:
        print("[Visualizer] Gemini API key missing. Returning error response.")
        return fallback_response
        
    print(f"[Visualizer] Processing request: '{prompt}' for subject '{subject}'...")
    
    client = google_genai.Client(api_key=api_key)
    
    system_prompt = f"""You are an expert IIT-JEE tutor. The student wants to visualize something: "{prompt}".
Classify the request into one of three visual types:
1. "function_plot": Mathematical plots (graphs of equations like y=sin(x), curves, parabola, hyperbola, etc.).
2. "flowchart": Concept maps, process charts, logic flowcharts, data structure trees (binary trees, graphs, DFS/BFS traversals, photosynthesis, reaction mechanisms).
3. "dp_table": Dynamic programming table calculations (Knapsack, Fibonacci, LCS, Matrix Chain, coin change).

Return a valid JSON object matching the schema for that visual type:

If "function_plot":
{{
  "type": "function_plot",
  "expression": "The clean mathematical expression in python terms, using variable x, e.g. 'math.sin(x)' or 'x**2 - 4*x'"
}}

If "flowchart":
{{
  "type": "flowchart",
  "title": "A descriptive title",
  "nodes": [
    {{
      "id": "node_id_1",
      "label": "Brief Node Label",
      "description": "Optional description of what happens at this node",
      "level": 0 // Semantic depth hierarchy (0 = root, 1 = next layer, 2 = child layer) for auto-layout
    }}
  ],
  "edges": [
    {{
      "id": "edge_id_1",
      "source": "node_id_1",
      "target": "node_id_2",
      "label": "Optional edge connection label"
    }}
  ]
}}

If "dp_table":
{{
  "type": "dp_table",
  "problem": "Name of the DP problem",
  "row_labels": ["Row label 0", "Row label 1", ...],
  "col_labels": ["Col label 0", "Col label 1", ...],
  "grid": [[0, 0, ...], [0, 1, ...]], // Full filled 2D matrix of cell values (numbers or strings)
  "explanation": "Brief overview of the recurrence relation, e.g., dp[i] = dp[i-1] + dp[i-2]",
  "steps": [
    {{
      "cell": [0, 1], // Row index, Column index
      "val": 1, // Value filled in this cell
      "desc": "Explanation of how this cell is filled, showing calculation details"
    }}
  ]
}}

Return ONLY a raw JSON output matching the chosen schema. Do not output code fences or markdown blocks.
"""
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=system_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        if response and response.text:
            data = json.loads(response.text.strip())
            
            # Post-process mathematical curves to calculate coordinate arrays
            if data.get("type") == "function_plot":
                expr = data.get("expression", "x")
                data["points"] = evaluate_math_expression(expr)
                
            print(f"[Visualizer] Generation complete. Type: {data.get('type')}")
            return data
            
    except Exception as e:
        print(f"[Visualizer] Error during generation: {e}")
        
    return fallback_response
