## Summary

<!-- One-paragraph description of what this PR does and why. -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactor / code cleanup (no functional changes)

## Related Issue

Closes #<!-- issue number -->

## Changes Made

<!-- Bullet-point list of what changed. Be specific enough that a reviewer can follow without reading every line. -->

-
-

## Testing

<!-- Describe how you tested this change. -->

- [ ] Ran `poetry run ruff check podcast_pipeline/` — no new errors
- [ ] Ran `poetry run ruff format --check podcast_pipeline/` — no formatting issues
- [ ] Ran `poetry run pytest tests/ -v` — all tests pass
- [ ] Manually tested with a real audio URL (describe below)

```
# Command used for manual test
poetry run podcast-pipeline -i "..." --provider ...
```

## Checklist

- [ ] My code follows the project's style guidelines
- [ ] I have updated the relevant documentation (README, docstrings, CONTRIBUTING)
- [ ] I have added tests for new behavior where applicable
- [ ] All existing tests still pass
- [ ] No new sensitive data (API keys, local paths) introduced
