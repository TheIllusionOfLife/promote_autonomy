# ADK Evaluation Sets

This directory contains evaluation test sets for the ADK-based creative coordinator.

## Running Evaluations

```bash
# From creative-agent directory
adk eval app/agents/coordinator.py eval_sets/creative_coordinator_basic.evalset.json
```

## Eval Set Format

Each `.evalset.json` file contains:
- `name`: Descriptive name of the eval set
- `description`: What scenarios are covered
- `test_cases`: Array of test cases with:
  - `name`: Test case name
  - `input`: Input prompt for the agent
  - `expected_contains`: List of strings that should appear in the output

## Quality Thresholds

- **Target score**: >80% for basic scenarios
- **Acceptable score**: >70% for edge cases
- **Critical threshold**: <50% triggers investigation

## Test Coverage

### creative_coordinator_basic.evalset.json
Tests standard asset generation scenarios:
- Captions-only (Instagram style)
- Captions + image (Twitter)
- Complete campaign with captions + image + video

### Future Eval Sets
- `creative_coordinator_edge_cases.evalset.json`: Error handling, missing configs
- `creative_coordinator_platforms.evalset.json`: Multi-platform compatibility
- `creative_coordinator_performance.evalset.json`: Latency and token usage benchmarks
