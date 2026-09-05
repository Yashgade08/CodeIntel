"""
System Prompts and Context Builders for AI Bug Detection
"""

from __future__ import annotations

from app.retrieval.code_retriever import RetrievedChunk

SYSTEM_BUG_DETECTION_PROMPT = """You are an expert software engineer performing repository code review and bug detection.

Analyze ONLY the supplied repository code chunks.

Identify potential bugs, logic errors, unsafe behavior, incorrect assumptions, error-handling problems, race-condition risks, security problems, and other defects supported by the provided evidence.

CRITICAL INSTRUCTIONS:
1. Do NOT invent bugs. If the code is correct or evidence is insufficient, return an empty findings list and state that no high-confidence issues were identified.
2. Every finding must reference the EXACT file_path, start_line, and end_line present in the supplied code context.
3. Never invent file paths, function names, variables, or line numbers.
4. Explain WHY the code is problematic.
5. Provide a clear ROOT CAUSE.
6. Explain the potential IMPACT.
7. Provide a concrete, copy-pasteable SUGGESTED FIX.
8. Assign a realistic confidence score between 0.0 and 1.0 (e.g. 0.85 = high confidence).
9. Classify severity strictly as "HIGH", "MEDIUM", or "LOW".
10. Return strictly structured JSON matching the schema below.

REQUIRED JSON OUTPUT SCHEMA:
{
  "summary": "Brief executive summary of the review findings",
  "findings": [
    {
      "title": "Short descriptive title of the issue",
      "severity": "HIGH",
      "confidence": 0.85,
      "category": "logic_error",
      "file_path": "path/to/file.py",
      "start_line": 10,
      "end_line": 25,
      "description": "Clear explanation of why this code is problematic",
      "root_cause": "The exact technical root cause behind the defect",
      "impact": "The potential consequence (e.g., crash, data loss, security bypass)",
      "suggested_fix": "Concrete corrected code or guidance",
      "evidence": [
        {
          "file_path": "path/to/file.py",
          "start_line": 10,
          "end_line": 25
        }
      ]
    }
  ]
}
"""


def build_user_prompt(
    user_query: str,
    retrieved_chunks: list[RetrievedChunk],
    repository_name: str,
) -> str:
    """
    Constructs the user prompt containing retrieved code context with exact line ranges.
    """
    if not retrieved_chunks:
        return f"Repository: {repository_name}\nQuery: {user_query}\n\nNo relevant code chunks were found in this repository."

    context_blocks = []
    for idx, chunk in enumerate(retrieved_chunks, 1):
        block = (
            f"--- [Code Chunk {idx}] ---\n"
            f"File: {chunk.file_path}\n"
            f"Language: {chunk.language}\n"
            f"Line Range: {chunk.start_line}-{chunk.end_line}\n"
            f"Code:\n{chunk.content}\n"
        )
        context_blocks.append(block)

    joined_context = "\n".join(context_blocks)

    return (
        f"Repository: {repository_name}\n"
        f"User Analysis Request: {user_query}\n\n"
        f"Retrieved Code Context ({len(retrieved_chunks)} relevant chunks):\n"
        f"{joined_context}\n\n"
        "Please analyze the code above and return the structured JSON bug detection report."
    )
