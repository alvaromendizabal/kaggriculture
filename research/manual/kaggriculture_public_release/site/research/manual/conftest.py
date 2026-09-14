"""Historical standalone suites run with their package-specific commands.

The root baseline suite must not auto-import same-named tests from many independent
manual packages. This does not skip any root tests. See each package runbook.
"""
collect_ignore_glob = ["**/test_*.py"]
