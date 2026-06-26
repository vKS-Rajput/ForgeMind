# ForgeMind Python Engineering Standards v1

> See the full Phase 0 Foundation document for complete details and rationale.

## Function Standards

| Rule | Standard |
| :--- | :--- |
| Max length | 25 lines of logic |
| Max parameters | 5 positional. Use dataclasses/Pydantic for more. |
| Naming | `snake_case`. Verb-first for actions, noun for accessors. |
| Docstrings | Required on all public functions. Google style. |
| Return type | Always annotated. Use `None` explicitly. |
| Side effects | Name to indicate (`save_`, `persist_`, `send_`). |

## Module Standards

| Rule | Standard |
| :--- | :--- |
| Max file size | 300 lines. Soft limit at 200. |
| Responsibility | Single. If docstring needs "and", split. |
| Import ordering | stdlib → third-party → local (ruff `I` rule) |
| Module docstring | Required. One-sentence purpose. |

## Data Model Standards

| Use Case | Tool |
| :--- | :--- |
| Domain entities | `@dataclass(frozen=True, slots=True)` |
| Value objects | `@dataclass(frozen=True)` or `NewType` |
| API schemas | `pydantic.BaseModel` |
| Configuration | `pydantic_settings.BaseSettings` |
| Port interfaces | `typing.Protocol` |

## Error Handling

- All exceptions inherit from `ForgeMindError`
- Every exception carries: `message`, `code`, `context`
- No bare `except:` — always specify the exception type
- Validate inputs at function entry, fail fast
- Every `except` block must re-raise or log at WARNING/ERROR

## Docstring Style

Google convention. Example:

```python
def extract_entities(text: str, min_confidence: float = 0.5) -> list[KnowledgeEntity]:
    """Extract named entities from text.

    Args:
        text: Source text. Must not be empty.
        min_confidence: Minimum confidence threshold.

    Returns:
        List of entities sorted by confidence (highest first).

    Raises:
        EntityExtractionError: If extraction pipeline fails.
        ValueError: If text is empty.
    """
```
