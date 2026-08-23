## Summary
<!-- What does this PR change, and why? -->

## Type of change
- [ ] Bug fix
- [ ] New feature / tool
- [ ] Refactor (no behaviour change)
- [ ] Documentation
- [ ] Tests

## What to verify
- [ ] `py -m py_compile vfp_common.py vfp_audit.py vfp_driver.py vfp_dbf_export.py vfp_indexer.py install.py`
- [ ] `py -m pytest tests/ -q`
- [ ] Read-only guarantee intact (no writes to the VFP project source)

## Notes
<!-- Edge cases, config changes, new dependencies, screenshots/output samples. -->
