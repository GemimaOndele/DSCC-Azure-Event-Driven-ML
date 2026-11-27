"""Pure business logic for the DSCC event pipeline.

Azure SDK imports are deliberately confined to ``azure_clients.py`` so that the
contract, orchestration and retry logic can be unit-tested without a cloud
account. See ``functions/README.md``.
"""
