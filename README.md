# Proxima SDK

The official Python SDK for building AI agents on the **Proxima AIP** platform.

## Install

```bash
pip install proxima-sdk
```

## Quick Start

```python
from proxima_sdk import PlatformContext

def my_tool(params: dict, ctx: PlatformContext) -> dict:
    # Access knowledge bases
    data = ctx.knowledge.query("What invoices are overdue?")
    
    # Log actions for governance
    ctx.governance.log_action("queried_invoices")
    
    return {"answer": data.answer, "citations": data.citations}
```

## Testing

```python
from proxima_sdk.testing import mock_context

ctx = mock_context(sources={"invoices": [{"id": "INV-001", "amount": 5000}]})
result = my_tool({"query": "overdue"}, ctx)
```

## Documentation

Full docs at [docs.proximaintel.com/sdk](https://docs.proximaintel.com/sdk)
