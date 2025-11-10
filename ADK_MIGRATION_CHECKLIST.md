# ADK Migration Checklist

**Quick reference for implementing ADK integration**

---

## Pre-Migration (Week 0)

- [ ] Read `ADK_IMPLEMENTATION_PLAN.md` completely
- [ ] Review ADK documentation: https://google.github.io/adk-docs/
- [ ] Set up staging environment for testing
- [ ] Create backup branch: `git checkout -b pre-adk-backup`
- [ ] Communicate plan to team/stakeholders

---

## Phase 1: Setup (Days 1-3)

### Dependencies
- [ ] Add `google-adk>=1.0.0` to `creative-agent/pyproject.toml`
- [ ] Run `uv sync` to install
- [ ] Test import: `python -c "from google.adk.agents import LlmAgent"`

### Configuration
- [ ] Add `USE_ADK_ORCHESTRATION=false` to `.env`
- [ ] Add `ADK_ROLLOUT_PERCENTAGE=0` to `.env`
- [ ] Update `.env.example` with new variables
- [ ] Update `app/core/config.py` with ADK settings

### Documentation
- [ ] Update `creative-agent/README.md` with ADK section
- [ ] Document feature flags

---

## Phase 2: ADK Tools (Days 4-7)

### Create Files
- [ ] `creative-agent/app/agents/__init__.py`
- [ ] `creative-agent/app/agents/tools.py`
- [ ] `creative-agent/app/agents/coordinator.py`

### Implement Tools
- [ ] `generate_captions_tool` with `@Tool` decorator
- [ ] `generate_image_tool` with `@Tool` decorator
- [ ] `generate_video_tool` with `@Tool` decorator
- [ ] Test each tool independently

### Implement Coordinator
- [ ] `create_copy_agent()`
- [ ] `create_image_agent()`
- [ ] `create_video_agent()`
- [ ] `create_creative_coordinator()` with sub-agents
- [ ] `get_creative_coordinator()` singleton

### Verify
- [ ] No import errors when starting service
- [ ] Can create coordinator: `coordinator = get_creative_coordinator()`

---

## Phase 3: Integration (Days 8-10)

### Modify Consume Endpoint
- [ ] Create `_generate_assets_with_adk()` function
- [ ] Rename current logic to `_generate_assets_legacy()`
- [ ] Add feature flag check in `/consume` endpoint
- [ ] Implement URL extraction from ADK response

### Testing Switches
- [ ] Test with `USE_ADK_ORCHESTRATION=false` (legacy path)
- [ ] Test with `USE_ADK_ORCHESTRATION=true` (ADK path)
- [ ] Verify both produce same outputs

---

## Phase 4: Testing (Days 11-13)

### Unit Tests
- [ ] `tests/unit/test_adk_tools.py` created
- [ ] Test `generate_captions_tool`
- [ ] Test `generate_image_tool`
- [ ] Test `generate_video_tool` with size warning
- [ ] All tests passing: `pytest tests/unit/test_adk_tools.py`

### Integration Tests
- [ ] `tests/integration/test_adk_coordinator.py` created
- [ ] Test agent creation
- [ ] Test coordinator hierarchy
- [ ] Test singleton pattern

### E2E Tests
- [ ] E2E test with ADK orchestration (mock mode)
- [ ] E2E test with legacy orchestration (mock mode)
- [ ] E2E test with real services (staging)
- [ ] Compare results: ADK vs legacy

### Performance Benchmarks
- [ ] Measure execution time: ADK vs legacy
- [ ] Measure token usage: ADK vs legacy
- [ ] Measure cost per job: ADK vs legacy
- [ ] Document results in plan

---

## Phase 5: Evaluation (Days 14-15)

### Eval Sets
- [ ] Create `creative-agent/eval_sets/` directory
- [ ] Create `creative_coordinator_basic.evalset.json`
- [ ] Create `creative_coordinator_edge_cases.evalset.json`
- [ ] Run: `adk eval app/agents/coordinator.py eval_sets/*.json`
- [ ] Scores >80% quality threshold

### Observability
- [ ] Add structured logging for ADK path
- [ ] Log execution time, errors, outputs
- [ ] Create Cloud Monitoring dashboard
- [ ] Set up alerts for error rate, latency

---

## Phase 6: Deployment (Days 16-20)

### Staging Deployment
- [ ] Deploy to staging with `USE_ADK_ORCHESTRATION=true`
- [ ] Deploy to staging with `ADK_ROLLOUT_PERCENTAGE=100`
- [ ] Run full test suite in staging
- [ ] Monitor for 3 days (error rate, latency, cost)

### Production Canary (10%)
- [ ] Deploy to production with `ADK_ROLLOUT_PERCENTAGE=10`
- [ ] Monitor for 1 week:
  - [ ] Error rate <3%
  - [ ] Latency <60s avg
  - [ ] Cost per job <$0.06
- [ ] Review logs daily
- [ ] No critical issues

### Production Ramp (50%)
- [ ] Increase to `ADK_ROLLOUT_PERCENTAGE=50`
- [ ] Monitor for 1 week (same metrics)
- [ ] Compare ADK vs legacy cohorts
- [ ] No critical issues

### Production Full (100%)
- [ ] Set `USE_ADK_ORCHESTRATION=true`
- [ ] Set `ADK_ROLLOUT_PERCENTAGE=100`
- [ ] Monitor for 2 weeks
- [ ] All metrics within targets

### Rollback Plan
- [ ] Document rollback procedure
- [ ] Test rollback in staging
- [ ] Create rollback runbook
- [ ] Define rollback triggers

---

## Post-Migration (Week 7+)

### Cleanup
- [ ] Remove legacy orchestration code (after 1 month of stable ADK)
- [ ] Remove feature flags (USE_ADK_ORCHESTRATION)
- [ ] Update documentation to reflect ADK-only
- [ ] Archive legacy implementation for reference

### Enhancements
- [ ] (Optional) Add ADK to Strategy Agent
- [ ] (Optional) Implement brand agent (roadmap Phase 3.3)
- [ ] (Optional) Set up ADK Dev UI
- [ ] (Optional) Multi-variant generation for A/B testing

### Continuous Improvement
- [ ] Review ADK eval scores monthly
- [ ] Optimize prompts based on eval results
- [ ] Monitor ADK GitHub for updates
- [ ] Update ADK version quarterly

---

## Rollback Triggers

If any of these occur, execute rollback:

- [ ] ❌ Error rate >5% (compared to legacy)
- [ ] ❌ P95 latency >120s (>2x legacy)
- [ ] ❌ Cost per job >$0.075 (>1.5x legacy)
- [ ] ❌ Critical bug in ADK path
- [ ] ❌ ADK framework instability

**Rollback command:**
```bash
gcloud run services update creative-agent \
  --region=us-central1 \
  --set-env-vars=USE_ADK_ORCHESTRATION=false
```

---

## Key Metrics Dashboard

Track these metrics throughout migration:

| Metric | Legacy | ADK (10%) | ADK (50%) | ADK (100%) | Target |
|--------|--------|-----------|-----------|------------|--------|
| Avg Execution Time | 45s | ___ | ___ | ___ | <60s |
| P95 Latency | 75s | ___ | ___ | ___ | <100s |
| Error Rate | 2% | ___ | ___ | ___ | <3% |
| Cost/Job | $0.05 | ___ | ___ | ___ | <$0.06 |
| Token Usage | 5K | ___ | ___ | ___ | <7K |

---

## Sign-off Checklist

Before declaring migration complete:

- [ ] ✅ All phases completed
- [ ] ✅ All unit tests passing (>90% coverage)
- [ ] ✅ All E2E tests passing
- [ ] ✅ Production at 100% ADK for 2 weeks
- [ ] ✅ No P0/P1 incidents related to ADK
- [ ] ✅ Metrics within targets
- [ ] ✅ Documentation updated
- [ ] ✅ Team trained on ADK debugging
- [ ] ✅ Stakeholders informed

**Migration completed by**: _________________
**Date**: _________________
**Sign-off**: _________________

---

**Document Version**: 1.0
**Last Updated**: November 10, 2025
