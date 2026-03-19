"""Prevent pytest from collecting e2e fixture test files.

The test files in this directory are designed to be discovered and run by
``pixie test``, not by pytest directly. They require specific environment
setup (PIXIE_ROOT, dataset directory overrides) that only the e2e test
runner in ``test_e2e_pixie_test.py`` provides.
"""

collect_ignore_glob = ["test_*.py"]
