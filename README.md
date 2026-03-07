# python-holons

**Python SDK for Organic Programming** — transport helpers, a full
`serve` runner, identity parsing, discovery, `connect()`, and Holon-RPC
client/server utilities.

## Install

```bash
pip install holons
# or from source
pip install -e .
```

## API surface

| Module | Description |
|--------|-------------|
| `holons.transport` | `listen(uri)`, `parse_uri(uri)`, `scheme(uri)` |
| `holons.serve` | `parse_flags(args)`, `run_with_options(uri, register_fn, ...)` |
| `holons.identity` | `parse_holon(path)` |
| `holons.discover` | `discover(root)`, `discover_local()`, `discover_all()`, `find_by_slug(slug)`, `find_by_uuid(prefix)` |
| `holons.connect` | `connect(target, opts=None)`, `disconnect(channel)`, `ConnectOptions` |
| `holons.grpcclient` | transport-aware gRPC dial helpers |
| `holons.holonrpc` | `HolonRPCClient` and `HolonRPCServer` |

## Current scope

- Native gRPC over `tcp://` and `unix://`
- In-process `mem://` adapter for tests and composition
- Discovery scans local, `$OPBIN`, and cache roots
- `connect()` resolves direct targets or slugs and can launch daemons
  over TCP or stdio
- Holon-RPC is implemented as JSON-RPC 2.0 over WebSocket

## Current gaps vs Go

- `grpcio` still does not expose a raw stdio transport, so stdio support
  remains process-bridge based rather than a direct HTTP/2 pipe binding.

## Test

```bash
python -m pytest tests/ -v
```
