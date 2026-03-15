Analyze the SQL query results and decide if a chart would be helpful to visualize the data. If yes, return a JSON chart specification. If the data is not suitable for a chart (e.g., a single scalar value, text-only results, or just one row with one column), return exactly: NO_CHART

Rules:
- Return ONLY valid JSON or the text NO_CHART — no explanation, no markdown fences, no comments
- Choose the best chart type: "bar", "line", "pie", "doughnut"
- Use "bar" for comparisons across categories (e.g., sales by branch, count by product)
- Use "line" for time series or trends (e.g., monthly revenue, daily visits)
- Use "pie" or "doughnut" for proportions/distributions with few categories (max 8 slices)
- Keep labels short and readable
- Extract numeric data directly from the results — never invent numbers

JSON format:
{{
  "type": "bar",
  "title": "Ventas por sucursal",
  "labels": ["CDMX", "Guadalajara", "Monterrey"],
  "datasets": [
    {{
      "label": "Total ventas",
      "data": [7046, 6897, 5598]
    }}
  ]
}}

For multiple datasets (e.g., comparing two metrics):
{{
  "type": "bar",
  "title": "...",
  "labels": ["..."],
  "datasets": [
    {{"label": "Ventas", "data": [1, 2, 3]}},
    {{"label": "Transacciones", "data": [10, 20, 30]}}
  ]
}}

Question: {question}

SQL executed:
{sql}

Results:
{result}
