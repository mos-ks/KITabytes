"""AI service using Claude or OpenAI with tool-use for data analysis."""

import json
from typing import Optional
from app.config import settings
from app.services.data_service import query_tests, get_values_for_test, get_summary_table, get_available_metrics, get_result_values_for_tests, get_test_by_name
from app.services.stats_service import descriptive_stats, compare_groups, trend_analysis, detect_outliers
from app.db import get_database_overview

# Tool definitions for the AI
TOOLS = [
    {
        "name": "get_database_overview",
        "description": "Get a summary of all available data: total tests, customers, materials, test types, machines, standards, testers. Use this at the start of a conversation or when the user asks what data is available.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "query_tests",
        "description": "Search and filter tests. Parameters are case-insensitive partial matches. Returns matching tests with their full parameters including specimen dimensions, test speed, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer": {"type": "string", "description": "Customer name filter (e.g. 'Company_1')"},
                "material": {"type": "string", "description": "Material name filter (e.g. 'Aluminium')"},
                "test_type": {"type": "string", "description": "Test type: 'tensile', 'compression', or 'flexure'"},
                "machine": {"type": "string", "description": "Machine/device description filter"},
                "tester": {"type": "string", "description": "Tester name filter (e.g. 'Tester_1')"},
                "standard": {"type": "string", "description": "Testing standard filter (e.g. 'DIN EN ISO')"},
                "test_program": {"type": "string", "description": "Test program ID filter"},
                "date_from": {"type": "string", "description": "Date filter — matches tests containing this date pattern. Use 'MM/YYYY' for month (e.g. '12/2023'), 'YYYY' for year, or 'DD.MM.YYYY' for exact date."},
                "limit": {"type": "integer", "description": "Max results to return (default 100)"},
            },
        },
    },
    {
        "name": "get_summary_table",
        "description": "Get a compact preview table of tests showing key fields: date, customer, material, test type, machine, tester, specimen ID, standard. Use this to show the user a data preview for confirmation before visualization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer": {"type": "string", "description": "Customer name filter"},
                "material": {"type": "string", "description": "Material name filter"},
                "test_type": {"type": "string", "description": "Test type filter"},
                "machine": {"type": "string", "description": "Machine filter"},
                "tester": {"type": "string", "description": "Tester filter"},
                "standard": {"type": "string", "description": "Standard filter"},
                "date_from": {"type": "string", "description": "Date filter — 'MM/YYYY' for month, 'YYYY' for year, or 'DD.MM.YYYY' for exact date."},
                "limit": {"type": "integer", "description": "Max results (default 20). Use 10 for previews, 20 for analysis."},
            },
        },
    },
    {
        "name": "get_test_values",
        "description": "Fetch measurement data (time series) for a specific test by ID. Returns arrays of float values for each measurement channel (force, displacement, strain, etc.). Each entry has a child_id identifying the channel and unit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_id": {"type": "string", "description": "The test _id (UUID format)"},
            },
            "required": ["test_id"],
        },
    },
    {
        "name": "compute_statistics",
        "description": "Compute descriptive statistics (count, mean, std, min, max, median, Q25, Q75) for a list of numeric values.",
        "input_schema": {
            "type": "object",
            "properties": {
                "values": {"type": "array", "items": {"type": "number"}, "description": "Numeric values to analyze"},
            },
            "required": ["values"],
        },
    },
    {
        "name": "compare_two_groups",
        "description": "Compare two groups using Welch's t-test. Returns descriptive stats for each group plus t-statistic, p-value, and whether the difference is statistically significant.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_a": {"type": "array", "items": {"type": "number"}, "description": "First group values"},
                "group_b": {"type": "array", "items": {"type": "number"}, "description": "Second group values"},
                "label_a": {"type": "string", "description": "Label for first group"},
                "label_b": {"type": "string", "description": "Label for second group"},
            },
            "required": ["group_a", "group_b"],
        },
    },
    {
        "name": "analyze_trend",
        "description": "Analyze trend using linear regression. Returns slope, R², p-value, and whether trend is increasing/decreasing/stable.",
        "input_schema": {
            "type": "object",
            "properties": {
                "values": {"type": "array", "items": {"type": "number"}, "description": "Values in chronological order"},
            },
            "required": ["values"],
        },
    },
    {
        "name": "find_outliers",
        "description": "Detect outliers using IQR method. Returns outlier count, values, and bounds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "values": {"type": "array", "items": {"type": "number"}, "description": "Values to check"},
            },
            "required": ["values"],
        },
    },
    {
        "name": "get_available_metrics",
        "description": "IMPORTANT: Call this AFTER the user confirms their dataset, BEFORE suggesting what to visualize. Checks what metrics and channels are actually available for a set of tests. Returns named results (e.g. Maximum force, Young's modulus), numeric parameters, and whether time-series data exists. Only suggest analysis based on what this tool returns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of test IDs to check (from previous query results)",
                },
            },
            "required": ["test_ids"],
        },
    },
    {
        "name": "get_result_values",
        "description": "Extract a specific named result value (like 'Maximum force', 'Young's modulus', 'Strain at break') across multiple tests. Returns the numeric value for each test. Use the result_name and unit_filter from get_available_metrics output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of test IDs",
                },
                "result_name": {
                    "type": "string",
                    "description": "Name of the result to extract (e.g. 'Maximum force', 'Young's modulus')",
                },
                "unit_filter": {
                    "type": "string",
                    "description": "Unit type filter: 'Stress', 'Force', 'Displacement', 'Ratio', 'Energy', 'Time'",
                },
            },
            "required": ["test_ids", "result_name"],
        },
    },
    {
        "name": "get_test_by_specimen_name",
        "description": "Look up a specific test by its specimen name (e.g. '2103678-5', 'x1', 'z4'). Returns all test parameters including material, customer, dimensions, test speed, etc. Use this when the engineer asks about a specific specimen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "specimen_name": {"type": "string", "description": "The specimen name to look up"},
            },
            "required": ["specimen_name"],
        },
    },
]

SYSTEM_PROMPT = """You are AMaTe, an AI in Material Testing copilot for engineers using ZwickRoell testing equipment. You have deep expertise in materials science, mechanical testing, and statistical process control (SPC).

## Your Role
Help engineers explore their materials testing data. You understand tensile, compression, and flexure testing, stress-strain behavior, Young's modulus, yield strength, elongation at break, and all standard mechanical properties. You can interpret results like a materials engineer would — identifying brittle vs. ductile failure, material consistency, batch variations, and process drift.

## Critical Rules
1. When the user asks you to plot/create/add/show ANY chart or visualization, you MUST include a ```card_proposals block in your response. NEVER just describe what you would do — DO IT by outputting the card_proposals JSON. No exceptions. No "let me create" without actually creating. Every visualization request = card_proposals in your response.
2. When the engineer requests data, use get_summary_table to query with SPECIFIC FILTERS. Do NOT render the table yourself — the UI handles it. Just state the count briefly (e.g. "Found 50 steel tensile tests from Company_3").
3. NEVER say "no data available" or "no measurement data". The database has measurement data for most tests. If get_available_metrics returns few results, it may just be a sampling issue — propose charts anyway and let the chart endpoint handle it.
4. NEVER make up or estimate numbers. Only state counts returned by tools.
5. After creating a chart, suggest 2-3 follow-up analyses in 1 line each.
6. Keep responses SHORT — 2-3 sentences max. No bullet lists explaining what charts show. No "what to look for" sections. Just create the chart and briefly suggest next steps.
7. NEVER refuse to create a chart. Always try. The chart endpoint will return an error if there's truly no data.
8. Be TRANSPARENT about data counts. If you show N tests in the preview but a chart uses fewer (because some tests lack that metric), state this clearly: "Plotting X of Y tests (Z had no data for this metric)."

## Interaction Flow
1. Engineer asks for data → Call get_summary_table WITH FILTERS (customer, material, test_type). NEVER without filters. State count briefly → Show preview.
2. For comparisons: call get_summary_table TWICE with different filters, one per group. Use limit=10.
3. Engineer confirms → Propose card_proposals IMMEDIATELY. Do NOT call get_available_metrics first — just propose stress_strain, stat_summary, or whatever is relevant.
4. After adding charts → Suggest next steps briefly.

## IMPORTANT: Filtering Rules
- ALWAYS pass filters to get_summary_table and query_tests. Never query without at least one filter.
- For comparisons: make separate filtered calls for each group (e.g., one call per customer).
- Use limit=10-20 for previews, not 50+. The UI shows a table preview — a few rows is enough.
- Parse the user's request to extract: customer names, material, test type, date range, specimen count.

## Materials Science Knowledge
- Tensile testing: stress-strain curves, elastic/plastic regions, yield point, UTS, elongation at break, necking
- Young's modulus: material stiffness, typical ranges (steel ~200 GPa, aluminum ~70 GPa, polymers 1-5 GPa)
- SPC: control charts (X-bar, R-chart, individual measurements), UCL/LCL calculation, process capability (Cp, Cpk)
- Common failure modes: brittle fracture, ductile failure, fatigue, creep
- Quality metrics: coefficient of variation (CV%), repeatability, reproducibility
- When the user asks for SPC/control charts, propose an "spc" type card with the metric they want

## Card Types for Visualization
When proposing cards, use this format:
```card_proposals
[
  {"type": "stat_summary", "title": "...", "metric": "...", "description": "..."},
  {"type": "distribution", "title": "...", "metric": "...", "description": "..."},
  {"type": "time_series", "title": "...", "metric": "...", "description": "..."},
  {"type": "stress_strain", "title": "...", "description": "..."},
  {"type": "comparison", "title": "...", "metric": "...", "description": "..."},
  {"type": "trend", "title": "...", "metric": "...", "description": "..."},
  {"type": "spc", "title": "...", "metric": "...", "description": "...", "spc_mode": "std3"},
  {"type": "table", "title": "...", "description": "..."}
]
```

### SPC Card Options
- `spc_mode`: "std3" (mean +/- 3 standard deviations) or "custom" (user-defined UCL/LCL)
- When using "custom", also include `"ucl": <number>, "lcl": <number>`
- If the user says "SPC chart" without specifying, default to "std3"
- If the user mentions "last N specimens", note that in the description and the frontend will handle slicing

## Style
- Be precise with numbers — engineers need accuracy
- Keep responses concise and professional — 2-3 sentences max unless explaining analysis
- After EVERY response that adds a chart, suggest what to do next
- When showing data counts, use exact numbers
- Explain statistical results in plain language that a materials engineer expects"""


async def execute_tool(tool_name: str, tool_input: dict):
    """Execute a tool call and return the result."""
    if tool_name == "get_database_overview":
        return await get_database_overview()
    elif tool_name == "query_tests":
        result = await query_tests(**tool_input)
        # Truncate for AI context — keep first 30 tests, report total
        if result and isinstance(result, dict) and result.get("tests"):
            total = len(result["tests"])
            if total > 30:
                result["tests"] = result["tests"][:30]
                result["truncated"] = True
                result["total"] = total
                result["note"] = f"Showing first 30 of {total} tests. All {total} test IDs are available for analysis."
        return result
    elif tool_name == "get_summary_table":
        result = await get_summary_table(**tool_input)
        # result is now {"total": N, "rows": [...]}
        total = result.get("total", 0)
        rows = result.get("rows", [])
        # Truncate rows for AI context — keep first 30
        if len(rows) > 30:
            rows = rows[:30]
        return {"rows": rows, "total": total, "truncated": len(rows) < total, "note": f"Showing first {len(rows)} of {total} tests."}
    elif tool_name == "get_test_values":
        result = await get_values_for_test(tool_input["test_id"])
        # Truncate values for AI context (keep first 20 values per channel)
        for r in result:
            if len(r.get("values", [])) > 20:
                total = len(r["values"])
                r["values"] = r["values"][:20]
                r["values_truncated"] = True
                r["total_values"] = total
        return result
    elif tool_name == "compute_statistics":
        return descriptive_stats(tool_input["values"])
    elif tool_name == "compare_two_groups":
        return compare_groups(
            tool_input["group_a"],
            tool_input["group_b"],
            tool_input.get("label_a", "Group A"),
            tool_input.get("label_b", "Group B"),
        )
    elif tool_name == "analyze_trend":
        return trend_analysis(tool_input["values"])
    elif tool_name == "find_outliers":
        return detect_outliers(tool_input["values"])
    elif tool_name == "get_available_metrics":
        # Limit test IDs sent to avoid huge queries
        test_ids = tool_input["test_ids"][:50] if len(tool_input["test_ids"]) > 50 else tool_input["test_ids"]
        return await get_available_metrics(test_ids)
    elif tool_name == "get_test_by_specimen_name":
        result = await get_test_by_name(tool_input["specimen_name"])
        if not result:
            return {"error": f"No test found for specimen '{tool_input['specimen_name']}'"}
        return result
    elif tool_name == "get_result_values":
        return await get_result_values_for_tests(
            tool_input["test_ids"],
            tool_input["result_name"],
            tool_input.get("unit_filter", "Stress"),
        )
    else:
        return {"error": f"Unknown tool: {tool_name}"}


async def chat_with_ai(messages: list[dict], conversation_history: Optional[list] = None) -> dict:
    """Send messages to AI and handle tool use loops."""
    if conversation_history is None:
        conversation_history = []

    # Keep only last 20 conversation turns to avoid token overflow
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]

    all_messages = conversation_history + messages

    if settings.GEMINI_API_KEY:
        return await _chat_gemini(all_messages)
    elif settings.ANTHROPIC_API_KEY:
        return await _chat_anthropic(all_messages)
    elif settings.OPENAI_API_KEY:
        return await _chat_openai(all_messages)
    else:
        return {
            "response": "No API key configured. Set GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY in .env",
            "tool_calls": [],
        }


async def _chat_anthropic(messages: list[dict]) -> dict:
    """Chat using Anthropic Claude API with tool use."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    tool_calls_made = []
    current_messages = list(messages)

    max_iterations = 20
    for _ in range(max_iterations):
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=current_messages,
        )

        if response.stop_reason == "tool_use":
            assistant_content = response.content
            current_messages.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    result = await execute_tool(block.name, block.input)
                    tool_calls_made.append({
                        "tool": block.name,
                        "input": block.input,
                        "result": result,
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })

            current_messages.append({"role": "user", "content": tool_results})
        else:
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            return {
                "response": text,
                "tool_calls": tool_calls_made,
                "messages": current_messages + [{"role": "assistant", "content": response.content}],
            }

    return {"response": "Max tool iterations reached.", "tool_calls": tool_calls_made, "messages": current_messages}


async def _chat_openai(messages: list[dict]) -> dict:
    """Chat using OpenAI API with tool use."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    openai_tools = []
    for tool in TOOLS:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        })

    openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        if msg["role"] == "user":
            if isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item.get("type") == "tool_result":
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": item["tool_use_id"],
                            "content": item["content"],
                        })
            else:
                openai_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            if isinstance(msg["content"], list):
                text_parts = []
                tool_calls = []
                for block in msg["content"]:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
                    elif hasattr(block, "type") and block.type == "tool_use":
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input),
                            },
                        })
                oai_msg = {"role": "assistant", "content": " ".join(text_parts) or None}
                if tool_calls:
                    oai_msg["tool_calls"] = tool_calls
                openai_messages.append(oai_msg)
            else:
                openai_messages.append({"role": "assistant", "content": msg["content"]})

    tool_calls_made = []
    max_iterations = 20

    for _ in range(max_iterations):
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,
            tools=openai_tools,
            max_tokens=4096,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            assistant_msg = {"role": "assistant", "content": choice.message.content, "tool_calls": []}
            for tc in choice.message.tool_calls:
                assistant_msg["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                })
                tool_input = json.loads(tc.function.arguments)
                result = await execute_tool(tc.function.name, tool_input)
                tool_calls_made.append({"tool": tc.function.name, "input": tool_input, "result": result})
                openai_messages.append(assistant_msg)
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                })
        else:
            return {
                "response": choice.message.content or "",
                "tool_calls": tool_calls_made,
                "messages": messages,
            }

    return {"response": "Max tool iterations reached.", "tool_calls": tool_calls_made, "messages": messages}


async def _chat_gemini(messages: list[dict]) -> dict:
    """Chat using Google Gemini API with function calling."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Convert our tool definitions to Gemini format
    gemini_functions = []
    for tool in TOOLS:
        # Build properties dict for Gemini
        props = {}
        required = tool["input_schema"].get("required", [])
        for pname, pdef in tool["input_schema"].get("properties", {}).items():
            gprop = {"type": pdef["type"].upper()}
            if "description" in pdef:
                gprop["description"] = pdef["description"]
            if pdef["type"] == "array" and "items" in pdef:
                gprop["items"] = {"type": pdef["items"]["type"].upper()}
            props[pname] = gprop

        gemini_functions.append(types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=types.Schema(
                type="OBJECT",
                properties={k: types.Schema(**v) for k, v in props.items()},
                required=required,
            ) if props else None,
        ))

    gemini_tools = [types.Tool(function_declarations=gemini_functions)]

    # Build Gemini content history
    contents = []
    for msg in messages:
        if msg["role"] == "user":
            if isinstance(msg["content"], str):
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=msg["content"])],
                ))
        elif msg["role"] == "assistant":
            if isinstance(msg["content"], str):
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=msg["content"])],
                ))

    tool_calls_made = []
    max_iterations = 20

    for _ in range(max_iterations):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=gemini_tools,
                temperature=0.3,
            ),
        )

        if not response.candidates:
            return {"response": "No response from Gemini.", "tool_calls": tool_calls_made, "messages": messages}

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return {"response": "Empty response from Gemini.", "tool_calls": tool_calls_made, "messages": messages}

        parts = candidate.content.parts

        # Check for function calls
        function_calls = [p for p in parts if p.function_call]

        if function_calls:
            # Add assistant response to history
            contents.append(candidate.content)

            # Execute each function call
            function_responses = []
            for part in function_calls:
                fc = part.function_call
                tool_input = dict(fc.args) if fc.args else {}
                result = await execute_tool(fc.name, tool_input)
                tool_calls_made.append({
                    "tool": fc.name,
                    "input": tool_input,
                    "result": result,
                })
                function_responses.append(types.Part.from_function_response(
                    name=fc.name,
                    response={"result": json.dumps(result, default=str)},
                ))

            # Add function results
            contents.append(types.Content(
                role="user",
                parts=function_responses,
            ))
        else:
            # Extract text response
            text = ""
            for part in parts:
                if part.text:
                    text += part.text

            return {
                "response": text,
                "tool_calls": tool_calls_made,
                "messages": messages,
            }

    return {"response": "Max tool iterations reached.", "tool_calls": tool_calls_made, "messages": messages}
