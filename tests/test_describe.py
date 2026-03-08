from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

import pytest

from holons.describe import build_response, holonmeta_pb2, holonmeta_pb2_grpc
from holons.grpcclient import dial_uri

_SDK_DIR = Path(__file__).resolve().parents[1]

_ECHO_PROTO = """\
syntax = "proto3";
package echo.v1;

// Echo echoes request payloads for documentation tests.
service Echo {
  // Ping echoes the inbound message.
  // @example {"message":"hello","sdk":"go-holons"}
  rpc Ping(PingRequest) returns (PingResponse);
}

message PingRequest {
  // Message to echo back.
  // @required
  // @example "hello"
  string message = 1;

  // SDK marker included in the response.
  // @example "go-holons"
  string sdk = 2;
}

message PingResponse {
  // Echoed message.
  string message = 1;

  // SDK marker from the server.
  string sdk = 2;
}
"""

_HOLON_YAML = """\
given_name: Echo
family_name: Server
motto: Reply precisely.
"""

_HELPER_SCRIPT = textwrap.dedent(
    """\
    import json
    import os
    import sys

    import grpc

    sys.path.insert(0, os.environ["HOLONS_SDK_DIR"])

    from holons.serve import run_with_options


    def _decode_request(raw):
        if not raw:
            return {}
        payload = json.loads(raw.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}


    def _encode_response(payload):
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")


    class EchoHandler(grpc.GenericRpcHandler):
        def service(self, handler_call_details):
            if handler_call_details.method != "/echo.v1.Echo/Ping":
                return None
            return grpc.unary_unary_rpc_method_handler(
                self._ping,
                request_deserializer=_decode_request,
                response_serializer=_encode_response,
            )

        def _ping(self, request, _context):
            return {
                "message": str(request.get("message", "")),
                "sdk": "python-holons",
            }


    def register(server):
        if os.environ.get("HOLONS_WITH_ECHO") == "1":
            server.add_generic_rpc_handlers([EchoHandler()])


    run_with_options(
        "tcp://127.0.0.1:0",
        register,
        reflect=False,
        on_listen=lambda uri: print(uri, flush=True),
    )
    """
)


def _write_echo_holon(root: Path, *, include_proto: bool = True) -> None:
    (root / "holon.yaml").write_text(_HOLON_YAML, encoding="utf-8")
    if not include_proto:
        return
    proto_path = root / "protos" / "echo" / "v1"
    proto_path.mkdir(parents=True, exist_ok=True)
    (proto_path / "echo.proto").write_text(_ECHO_PROTO, encoding="utf-8")


def _find_field(fields, name: str):
    for field in fields:
        if field.name == name:
            return field
    raise AssertionError(f"field {name!r} not found")


def _is_bind_denied(stderr: str) -> bool:
    text = stderr.lower()
    return "bind" in text and "operation not permitted" in text


def _start_describe_helper(
    workdir: Path,
    *,
    include_proto: bool,
    with_echo: bool,
) -> tuple[subprocess.Popen[str], str, Path]:
    _write_echo_holon(workdir, include_proto=include_proto)

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write(_HELPER_SCRIPT)
        script_path = Path(handle.name)

    env = dict(os.environ)
    env["HOLONS_SDK_DIR"] = str(_SDK_DIR)
    env["HOLONS_WITH_ECHO"] = "1" if with_echo else "0"
    env["PYTHONPATH"] = str(_SDK_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=workdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert proc.stdout is not None
    uri = proc.stdout.readline().strip()
    if uri:
        return proc, uri, script_path

    stderr = ""
    if proc.stderr is not None:
        stderr = proc.stderr.read()
    _stop_process(proc)
    script_path.unlink(missing_ok=True)

    if _is_bind_denied(stderr):
        pytest.skip("local bind denied in this environment")
    raise RuntimeError(f"describe helper failed to start: {stderr}")


def _stop_process(proc: subprocess.Popen[str]) -> int:
    if proc.poll() is not None:
        return int(proc.returncode)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    return int(proc.returncode)


def test_build_response_from_echo_proto(tmp_path: Path):
    _write_echo_holon(tmp_path, include_proto=True)

    response = build_response(tmp_path / "protos", tmp_path / "holon.yaml")

    assert response.slug == "echo-server"
    assert response.motto == "Reply precisely."
    assert len(response.services) == 1

    service = response.services[0]
    assert service.name == "echo.v1.Echo"
    assert service.description == "Echo echoes request payloads for documentation tests."
    assert len(service.methods) == 1

    method = service.methods[0]
    assert method.name == "Ping"
    assert method.description == "Ping echoes the inbound message."
    assert method.input_type == "echo.v1.PingRequest"
    assert method.output_type == "echo.v1.PingResponse"
    assert method.example_input == '{"message":"hello","sdk":"go-holons"}'

    message_field = _find_field(method.input_fields, "message")
    assert message_field.type == "string"
    assert message_field.number == 1
    assert message_field.description == "Message to echo back."
    assert message_field.label == holonmeta_pb2.FIELD_LABEL_OPTIONAL
    assert message_field.required is True
    assert message_field.example == '"hello"'


def test_serve_auto_registers_holonmeta_describe(tmp_path: Path):
    proc, uri, script_path = _start_describe_helper(
        tmp_path,
        include_proto=True,
        with_echo=True,
    )
    try:
        channel = dial_uri(uri)
        try:
            stub = holonmeta_pb2_grpc.HolonMetaStub(channel)
            response = stub.Describe(holonmeta_pb2.DescribeRequest(), timeout=5)
        finally:
            channel.close()
    finally:
        rc = _stop_process(proc)
        script_path.unlink(missing_ok=True)
        assert rc == 0

    assert response.slug == "echo-server"
    assert response.motto == "Reply precisely."
    assert [service.name for service in response.services] == ["echo.v1.Echo"]
    assert response.services[0].methods[0].name == "Ping"


def test_serve_describe_gracefully_handles_missing_protos(tmp_path: Path):
    proc, uri, script_path = _start_describe_helper(
        tmp_path,
        include_proto=False,
        with_echo=False,
    )
    try:
        channel = dial_uri(uri)
        try:
            stub = holonmeta_pb2_grpc.HolonMetaStub(channel)
            response = stub.Describe(holonmeta_pb2.DescribeRequest(), timeout=5)
        finally:
            channel.close()
    finally:
        rc = _stop_process(proc)
        script_path.unlink(missing_ok=True)
        assert rc == 0

    assert response.slug == "echo-server"
    assert response.motto == "Reply precisely."
    assert list(response.services) == []
