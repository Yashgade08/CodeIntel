"""
Prompt templates for Codebase Copilot.
Separated from application logic for clean architectural boundaries.
"""

from __future__ import annotations

from typing import Any, Sequence

COPILOT_SYSTEM_PROMPT = """You are CodeIntel Copilot — an expert AI codebase assistant and software architect.

You answer questions about GitHub repositories strictly based on the provided source code, documentation, repository structure, and dependency information.

CRITICAL RULES YOU MUST FOLLOW AT ALL TIMES:
1. GROUNDING: Ground every assertion in the retrieved code evidence provided.
2. CITATIONS: Always cite exact file paths and line ranges using the format [file_path:start_line-end_line] (e.g. [auth/service.py:42-78]).
3. FACTS vs INFERENCE: Clearly distinguish between observed Facts (code present in citations) and Inferences (architectural predictions/deductions).
4. NO FABRICATION: Do NOT invent, assume, or hallucinate non-existent files, classes, or code logic.
5. INSUFFICIENT EVIDENCE: If the retrieved code evidence is missing or insufficient to answer the question confidently, respond with:
"I couldn't find enough evidence in this repository to answer confidently."
"""


def build_copilot_prompt(
    user_query: str,
    retrieved_chunks: Sequence[Any],
    repo_structure: str | None = None,
    dependencies: str | None = None,
    conversation_history: Sequence[dict[str, str]] | None = None,
) -> str:
    """
    Assemble structured prompt containing evidence blocks, citations, structure, dependencies, and history.
    """
    sections: list[str] = []

    # 1. Conversation History (if present)
    if conversation_history:
        history_text = "\n".join(
            f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
            for msg in conversation_history[-6:]
        )
        sections.append(f"### Recent Conversation History:\n{history_text}")

    # 2. Repository Structure & Dependencies (if present)
    if repo_structure:
        sections.append(f"### Repository Structure:\n```text\n{repo_structure}\n```")
    if dependencies:
        sections.append(f"### Code Dependencies:\n```text\n{dependencies}\n```")

    # 3. Retrieved Code & Document Evidence
    evidence_blocks: list[str] = []
    for chunk_tuple in retrieved_chunks:
        chunk = chunk_tuple[0] if isinstance(chunk_tuple, (list, tuple)) else chunk_tuple
        citation = getattr(chunk, "citation_str", f"{getattr(chunk, 'file_path', 'file')}:{getattr(chunk, 'start_line', 1)}-{getattr(chunk, 'end_line', 1)}")
        content = getattr(chunk, "content", str(chunk))
        evidence_blocks.append(f"Source: [{citation}]\n```\n{content}\n```")

    if evidence_blocks:
        sections.append("### Retrieved Code & Document Evidence:\n" + "\n\n".join(evidence_blocks))
    else:
        sections.append("### Retrieved Code & Document Evidence:\nNo relevant evidence found.")

    # 4. User Question
    sections.append(f"### User Query:\n{user_query}")

    return "\n\n".join(sections)
