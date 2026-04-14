import re
from typing import List, Any
from .models import DistillContext, DecisionRecord


def extract_symbols_from_diff(diff: str) -> List[str]:
    """
    Extract symbols (classes, functions) that were added or modified in a git diff.
    This is a pragmatic regex-based approach for V1.
    """
    symbols = set()

    # Matches Python class definitions: class ClassName:
    class_pattern = re.compile(r"^\+\s*class\s+([a-zA-Z0-9_]+)[\s\(:]", re.MULTILINE)

    # Matches Python function definitions: def function_name(...):
    def_pattern = re.compile(r"^\+\s*def\s+([a-zA-Z0-9_]+)[\s\(]", re.MULTILINE)

    # Find all matches in lines that start with '+'
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            # Try to match class
            class_match = class_pattern.match(line)
            if class_match:
                symbols.add(class_match.group(1))

            # Try to match def
            def_match = def_pattern.match(line)
            if def_match:
                symbols.add(def_match.group(1))

    return list(symbols)


def distill_sessions_to_decision(
    context: DistillContext, llm_client: Any
) -> DecisionRecord:
    """
    Use LLM to distill session reasoning into a structured decision record.
    This is a pure function (besides the LLM call) that follows functional principles.
    """
    # Placeholder for LLM prompt logic
    # In V1, this would call the Anthropic API
    # For now, we return a mock record

    return DecisionRecord(
        commit_hash=context.commit_hash,
        summary="Automated distillation of commit reasoning",
        why="Reasoning distilled from agent sessions",
        alternatives_rejected=["Option A", "Option B"],
        constraints=["Preserve existing interface"],
        symbols=context.symbols,
        files=context.files,
    )
