import os
from copy import deepcopy
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test-openworkflow.db"
Path("test-openworkflow.db").unlink(missing_ok=True)

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.services.workflow_engine as workflow_engine  # noqa: E402
from app.bootstrap import create_schema  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.workflow_engine import (  # noqa: E402
    execute_graph,
    execute_http_request,
    execute_node,
    validate_code_config,
    validate_document_config,
    validate_http_config,
    validate_knowledge_config,
    validate_llm_config,
)


@pytest.fixture(scope="module", autouse=True)
def schema():
    import asyncio

    asyncio.run(create_schema())
    yield
    asyncio.run(engine.dispose())
    Path("test-openworkflow.db").unlink(missing_ok=True)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value


def register(client: TestClient, email: str, name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery", "display_name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(session: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def test_multi_workspace_invitation_and_role_boundary(client: TestClient):
    owner = register(client, "owner@example.com", "Owner")
    member = register(client, "member@example.com", "Member")
    assert owner["user"]["is_platform_admin"] is True
    assert member["user"]["is_platform_admin"] is False
    assert owner["user"]["is_active"] is True
    assert member["user"]["is_active"] is True
    users = client.get("/api/v1/admin/users", headers=auth(owner))
    assert users.status_code == 200
    assert client.get("/api/v1/admin/users", headers=auth(member)).status_code == 403
    promoted = client.patch(
        f"/api/v1/admin/users/{member['user']['id']}",
        headers=auth(owner),
        json={"is_platform_admin": True},
    )
    assert promoted.status_code == 200
    assert promoted.json()["is_platform_admin"] is True
    assert client.get("/api/v1/admin/users", headers=auth(member)).status_code == 200
    disabled = client.patch(
        f"/api/v1/admin/users/{member['user']['id']}",
        headers=auth(owner),
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "correct-horse-battery"},
    ).status_code == 403
    assert client.get("/api/v1/auth/me", headers=auth(member)).status_code == 401
    enabled = client.patch(
        f"/api/v1/admin/users/{member['user']['id']}",
        headers=auth(owner),
        json={"is_active": True},
    )
    assert enabled.status_code == 200

    workspaces = client.get("/api/v1/workspaces", headers=auth(owner)).json()
    assert len(workspaces) == 1
    workspace_id = workspaces[0]["id"]
    created = client.post(
        "/api/v1/workspaces",
        headers=auth(owner),
        json={"name": "Shared AI Lab", "timezone": "Asia/Singapore"},
    )
    assert created.status_code == 201

    invitation = client.post(
        f"/api/v1/workspaces/{workspace_id}/invitations",
        headers=auth(owner),
        json={"email": "member@example.com", "role": "editor", "max_uses": 1},
    )
    assert invitation.status_code == 201, invitation.text
    accepted = client.post(
        f"/api/v1/workspaces/invitations/{invitation.json()['token']}/accept",
        headers=auth(member),
    )
    assert accepted.status_code == 200
    member_workspaces = client.get("/api/v1/workspaces", headers=auth(member)).json()
    assert any(item["id"] == workspace_id and item["role"] == "editor" for item in member_workspaces)


def test_versioned_script_and_workflow_publish(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    workspace_id = client.get("/api/v1/workspaces", headers=auth(session)).json()[0]["id"]
    script = client.post(
        f"/api/v1/workspaces/{workspace_id}/scripts",
        headers=auth(session),
        json={
            "name": "Greeting",
            "source_code": "def main(inputs, context):\n    return {'message': inputs['name']}",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            "output_schema": {"type": "object"},
        },
    )
    assert script.status_code == 201, script.text
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=auth(session),
        json={"name": "Greeting workflow"},
    )
    assert workflow.status_code == 201, workflow.text
    workflow_data = workflow.json()
    graph = workflow_data["draft_graph"]
    graph["nodes"].insert(
        1,
        {
            "id": "script-1",
            "type": "script",
            "position": {"x": 250, "y": 160},
            "data": {"label": "Greeting", "config": {"script_id": script.json()["id"]}},
        },
    )
    graph["edges"] = [
        {"id": "a", "source": "start", "target": "script-1"},
        {"id": "b", "source": "script-1", "target": "end"},
    ]
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow_data['id']}",
        headers=auth(session),
        json={"graph": graph, "expected_version": workflow_data["draft_version"]},
    )
    assert saved.status_code == 200, saved.text
    published = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow_data['id']}/publish",
        headers=auth(session),
        json={"change_note": "First release"},
    )
    assert published.status_code == 200, published.text
    reference = published.json()["resolved_references"]["script-1"]
    assert reference["version"] == 1


def test_workflow_environment_variables_are_encrypted_masked_and_resolved(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    workspace_id = client.get("/api/v1/workspaces", headers=auth(session)).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=auth(session),
        json={"name": "Environment workflow"},
    ).json()
    base = f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/environment-variables"
    greeting = client.post(base, headers=auth(session), json={"name": "GREETING", "value_type": "string", "value": "hello", "description": "Greeting text"})
    secret = client.post(base, headers=auth(session), json={"name": "API_SECRET", "value_type": "secret", "value": "never-return-this"})
    assert greeting.status_code == 201, greeting.text
    assert secret.status_code == 201, secret.text
    assert secret.json()["value"] == "••••••••"
    assert "never-return-this" not in client.get(base, headers=auth(session)).text

    graph = workflow["draft_graph"]
    start = next(node for node in graph["nodes"] if node["type"] == "start")
    start["data"]["config"]["triggers"] = ["api"]
    end = next(node for node in graph["nodes"] if node["type"] == "end")
    end["data"]["config"]["outputs"] = [
        {"name": "message", "type": "String", "value": "{{env.GREETING}}"},
        {"name": "user_id", "type": "String", "value": "{{sys.user_id}}"},
        {"name": "run_id", "type": "String", "value": "{{sys.workflow_run_id}}"},
        {"name": "timestamp", "type": "Number", "value": "{{sys.timestamp}}"},
    ]
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=auth(session),
        json={"graph": graph, "expected_version": workflow["draft_version"]},
    )
    assert saved.status_code == 200, saved.text
    run = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/run",
        headers=auth(session),
        json={"inputs": {"message": "ignored"}},
    )
    assert run.status_code == 200, run.text
    assert run.json()["outputs"]["message"] == "hello"
    assert run.json()["outputs"]["user_id"] == session["user"]["id"]
    assert run.json()["outputs"]["run_id"] == run.json()["id"]
    assert isinstance(run.json()["outputs"]["timestamp"], int)
    published = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/publish",
        headers=auth(session),
        json={"change_note": "Environment release"},
    )
    assert published.status_code == 200, published.text
    public_run = client.post(f"/v1/apps/{workflow['slug']}/run", json={"inputs": {"message": "ignored"}, "user": "public-user-1"})
    assert public_run.status_code == 200, public_run.text
    assert public_run.json()["outputs"]["message"] == "hello"
    assert public_run.json()["outputs"]["user_id"] == "public-user-1"
    assert public_run.json()["outputs"]["run_id"] == public_run.json()["run_id"]


def test_agent_script_tools_are_pinned_on_publish():
    graph = {
        "nodes": [
            {
                "id": "agent-1",
                "type": "agent",
                "data": {
                    "config": {
                        "tools": [
                            {
                                "id": "tool-1",
                                "type": "script",
                                "reference_id": "script-1",
                                "enabled": True,
                            }
                        ]
                    }
                },
            }
        ]
    }
    references = workflow_engine.resolve_script_references(
        graph, {"script-1": ("script-version-2", 2)}
    )
    assert references["agent-1:tool-1"] == {
        "kind": "agent_tool",
        "tool_id": "tool-1",
        "script_id": "script-1",
        "script_version_id": "script-version-2",
        "version": 2,
    }


def test_workspace_scope_blocks_foreign_script_access(client: TestClient):
    owner = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    member = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "correct-horse-battery"},
    ).json()
    owner_workspace = client.get("/api/v1/workspaces", headers=auth(owner)).json()[0]["id"]
    member_private = next(
        item["id"]
        for item in client.get("/api/v1/workspaces", headers=auth(member)).json()
        if item["role"] == "owner"
    )
    response = client.get(
        f"/api/v1/workspaces/{member_private}/scripts",
        headers=auth(owner),
    )
    assert response.status_code == 404
    assert owner_workspace != member_private


def test_protected_publish_accepts_scoped_api_key(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    workspace_id = client.get("/api/v1/workspaces", headers=auth(session)).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=auth(session),
        json={"name": "Protected workflow"},
    ).json()
    graph = workflow["draft_graph"]
    start = next(node for node in graph["nodes"] if node["type"] == "start")
    start["data"]["config"]["triggers"] = ["api"]
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=auth(session),
        json={"graph": graph, "expected_version": workflow["draft_version"]},
    )
    assert saved.status_code == 200, saved.text
    published = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/publish",
        headers=auth(session),
        json={"access": "protected"},
    )
    assert published.status_code == 200, published.text
    denied = client.post(f"/v1/apps/{workflow['slug']}/run", json={"inputs": {"value": 7}})
    assert denied.status_code == 401
    created = client.post(
        f"/api/v1/workspaces/{workspace_id}/api-keys",
        headers=auth(session),
        json={"name": "Production", "workflow_id": workflow["id"]},
    )
    assert created.status_code == 201, created.text
    key = created.json()["key"]
    allowed = client.post(
        f"/v1/apps/{workflow['slug']}/run",
        headers={"Authorization": f"Bearer {key}"},
        json={"inputs": {"value": 7}},
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "succeeded"


def test_start_node_uses_one_trigger_and_validates_inputs(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Multi trigger workflow"},
    ).json()
    graph = workflow["draft_graph"]
    start = next(node for node in graph["nodes"] if node["type"] == "start")
    start["data"]["config"] = {
        "triggers": ["api"],
        "input_fields": [
            {
                "name": "message",
                "label": "Message",
                "type": "text",
                "required": True,
                "placeholder": "Ask something",
            },
            {
                "name": "attachment",
                "label": "Attachment",
                "type": "file",
                "required": False,
            },
            {
                "name": "tone",
                "label": "Tone",
                "type": "select",
                "required": False,
                "options": ["Formal", "Friendly"],
                "default_value": "Formal",
            },
            {
                "name": "short_code",
                "label": "Short code",
                "type": "text",
                "required": False,
                "max_length": 5,
            },
        ],
        "schedule": {
            "cron": "0 9 * * *",
            "timezone": "Asia/Singapore",
            "enabled": False,
            "inputs_json": '{"message":"Scheduled"}',
        },
    }
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": graph, "expected_version": workflow["draft_version"]},
    )
    assert saved.status_code == 200, saved.text
    published = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/publish",
        headers=headers,
        json={"change_note": "Enable API trigger"},
    )
    assert published.status_code == 200, published.text

    description = client.get(f"/v1/apps/{workflow['slug']}")
    assert description.status_code == 200
    assert description.json()["triggers"] == ["api"]
    assert description.json()["input_fields"][0]["name"] == "message"
    assert client.post(f"/v1/apps/{workflow['slug']}/run", json={"inputs": {}}).status_code == 422
    api_run = client.post(
        f"/v1/apps/{workflow['slug']}/run", json={"inputs": {"message": "From API"}}
    )
    assert api_run.status_code == 200, api_run.text
    select_run = client.post(
        f"/v1/apps/{workflow['slug']}/run",
        json={"inputs": {"message": "From API", "tone": "Friendly"}},
    )
    assert select_run.status_code == 200, select_run.text
    invalid_select = client.post(
        f"/v1/apps/{workflow['slug']}/run",
        json={"inputs": {"message": "From API", "tone": "Unsupported"}},
    )
    assert invalid_select.status_code == 422
    too_long = client.post(
        f"/v1/apps/{workflow['slug']}/run",
        json={"inputs": {"message": "From API", "short_code": "TOO-LONG"}},
    )
    assert too_long.status_code == 422
    webhook_run = client.post(
        f"/v1/apps/{workflow['slug']}/webhook",
        json={"inputs": {"message": "From webhook"}},
    )
    assert webhook_run.status_code == 404, webhook_run.text
    runs = client.get(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/runs",
        headers=headers,
    ).json()
    assert {run["triggered_by"] for run in runs} >= {"api"}

    multiple_triggers = deepcopy(graph)
    multiple_start = next(node for node in multiple_triggers["nodes"] if node["type"] == "start")
    multiple_start["data"]["config"]["triggers"] = ["api", "webhook"]
    rejected = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": multiple_triggers, "expected_version": saved.json()["draft_version"]},
    )
    assert rejected.status_code == 422

    invalid_graph = deepcopy(graph)
    invalid_start = next(node for node in invalid_graph["nodes"] if node["type"] == "start")
    invalid_start["data"]["config"]["triggers"] = ["schedule"]
    invalid_start["data"]["config"]["schedule"]["cron"] = "not a cron"
    invalid = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": invalid_graph, "expected_version": saved.json()["draft_version"]},
    )
    assert invalid.status_code == 422

    invalid_options_graph = deepcopy(graph)
    invalid_options_start = next(
        node for node in invalid_options_graph["nodes"] if node["type"] == "start"
    )
    tone_field = next(
        field
        for field in invalid_options_start["data"]["config"]["input_fields"]
        if field["name"] == "tone"
    )
    tone_field["options"] = ["Formal", "Formal"]
    invalid_options = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": invalid_options_graph, "expected_version": saved.json()["draft_version"]},
    )
    assert invalid_options.status_code == 422


def test_draft_node_preview_records_single_node_trace(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Node preview workflow"},
    ).json()

    preview = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/nodes/end/run",
        headers=headers,
        json={"inputs": {"message": "Preview value"}},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["triggered_by"] == "node"
    assert preview.json()["outputs"] == {"message": "Preview value"}
    assert len(preview.json()["trace"]) == 1
    assert preview.json()["trace"][0]["node_id"] == "end"

    missing = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/nodes/missing/run",
        headers=headers,
        json={"inputs": {}},
    )
    assert missing.status_code == 404


def test_trace_input_is_resolved_and_environment_values_are_redacted():
    from app.services.workflow_engine import build_node_trace_input, build_node_trace_metadata

    node = {
        "id": "template",
        "type": "template",
        "data": {"config": {"inputs": [{"name": "name", "value": "{{inputs.name}}"}, {"name": "token", "value": "Bearer {{env.API_TOKEN}}"}], "template": "Hello {{ name }}"}},
    }
    trace_input = build_node_trace_input(node, {"inputs": {"name": "Codex"}, "env": {"API_TOKEN": "top-secret"}, "sys": {}})
    assert trace_input["inputs"][0]["value"] == "Codex"
    assert trace_input["inputs"][1]["value"] == "Bearer ••••••••"
    metadata = build_node_trace_metadata(node, trace_input, {"text": "ok", "_logs": ["token=top-secret"], "_usage": {"prompt_tokens": 4, "completion_tokens": 2}}, 12.5, 2, {"env": {"API_TOKEN": "top-secret"}})
    assert metadata["executor"] == "built-in"
    assert metadata["retry_count"] == 1
    assert metadata["usage"] == {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6}
    assert metadata["logs"] == ["token=••••••••"]


def test_node_names_are_unique_and_resolve_chinese_variable_references():
    graph = {
        "nodes": [
            {"id": "start", "type": "start", "data": {"label": "开始", "config": {"triggers": ["api"], "input_fields": [{"name": "message", "type": "text"}]}}},
            {"id": "assign", "type": "variable", "data": {"label": "变量赋值", "config": {"assignments": [{"name": "answer", "type": "String", "operation": "overwrite", "value": "{{开始.message}}"}]}}},
            {"id": "end", "type": "end", "data": {"label": "结束", "config": {"outputs": [{"name": "message", "type": "String", "value": "{{变量赋值.answer}}"}]}}},
        ],
        "edges": [
            {"id": "a", "source": "start", "target": "assign"},
            {"id": "b", "source": "assign", "target": "end"},
        ],
    }
    result, _ = execute_graph(graph, {"message": "按名称引用成功"})
    assert result == {"message": "按名称引用成功"}

    duplicate = deepcopy(graph)
    duplicate["nodes"][1]["data"]["label"] = "开始"
    with pytest.raises(HTTPException, match="unique node names"):
        workflow_engine.validate_draft_graph(duplicate)

def test_structured_end_outputs_are_resolved_and_validated(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Structured output workflow"},
    ).json()
    graph = deepcopy(workflow["draft_graph"])
    end = next(node for node in graph["nodes"] if node["type"] == "end")
    end["data"]["config"]["outputs"] = [
        {"name": "answer", "type": "String", "value": "{{inputs.message}}"},
        {"name": "summary", "type": "String", "value": "Received: {{inputs.message}}"},
        {"name": "count", "type": "Number", "value": 1},
    ]
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": graph, "expected_version": workflow["draft_version"]},
    )
    assert saved.status_code == 200, saved.text
    run = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/run",
        headers=headers,
        json={"inputs": {"message": "Hello"}},
    )
    assert run.status_code == 200, run.text
    assert run.json()["outputs"] == {
        "answer": "Hello",
        "summary": "Received: Hello",
        "count": 1,
    }

    invalid_graph = deepcopy(graph)
    invalid_end = next(node for node in invalid_graph["nodes"] if node["type"] == "end")
    invalid_end["data"]["config"]["outputs"][1]["name"] = "answer"
    invalid = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": invalid_graph, "expected_version": saved.json()["draft_version"]},
    )
    assert invalid.status_code == 422


def test_condition_node_executes_only_the_selected_branch():
    graph = {
        "schema_version": 1,
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "data": {"config": {"triggers": ["api"], "input_fields": [{"name": "score", "type": "number"}]}},
            },
            {
                "id": "condition",
                "type": "condition",
                "data": {"config": {"logical_operator": "and", "conditions": [
                    {"variable": "{{inputs.score}}", "operator": "greater_or_equal", "value": 60}
                ]}},
            },
            {"id": "passed", "type": "template", "data": {"config": {"template": "passed"}}},
            {"id": "failed", "type": "template", "data": {"config": {"template": "failed"}}},
            {"id": "pass_end", "type": "end", "data": {"config": {"outputs": [
                {"name": "result", "type": "String", "value": "{{passed.text}}"}
            ]}}},
            {"id": "fail_end", "type": "end", "data": {"config": {"outputs": [
                {"name": "result", "type": "String", "value": "{{failed.text}}"}
            ]}}},
        ],
        "edges": [
            {"source": "start", "target": "condition"},
            {"source": "condition", "sourceHandle": "true", "target": "passed"},
            {"source": "condition", "sourceHandle": "false", "target": "failed"},
            {"source": "passed", "target": "pass_end"},
            {"source": "failed", "target": "fail_end"},
        ],
    }

    passed_output, passed_trace = execute_graph(graph, {"score": 85})
    assert passed_output == {"result": "passed"}
    assert [item["node_id"] for item in passed_trace] == ["start", "condition", "passed", "pass_end"]
    assert passed_trace[1]["output"]["branch"] == "true"

    failed_output, failed_trace = execute_graph(graph, {"score": 40})
    assert failed_output == {"result": "failed"}
    assert [item["node_id"] for item in failed_trace] == ["start", "condition", "failed", "fail_end"]
    assert failed_trace[1]["output"]["branch"] == "false"


def test_classifier_routes_to_stable_category_handles():
    graph = {
        "schema_version": 1,
        "nodes": [
            {"id": "start", "type": "start", "data": {"config": {"triggers": ["api"], "input_fields": [{"name": "message", "type": "text"}]}}},
            {"id": "classifier", "type": "classifier", "data": {"config": {
                "input": "{{inputs.message}}",
                "categories": [
                    {"id": "sales", "name": "Sales", "description": "Pricing and purchases", "keywords": ["buy", "price"]},
                    {"id": "support", "name": "Support", "description": "Fallback support request", "keywords": ["broken", "error"]},
                ],
            }}},
            {"id": "sales_text", "type": "template", "data": {"config": {"template": "sales"}}},
            {"id": "support_text", "type": "template", "data": {"config": {"template": "support"}}},
            {"id": "sales_end", "type": "end", "data": {"config": {"outputs": [{"name": "result", "type": "String", "value": "{{sales_text.text}}"}]}}},
            {"id": "support_end", "type": "end", "data": {"config": {"outputs": [{"name": "result", "type": "String", "value": "{{support_text.text}}"}]}}},
        ],
        "edges": [
            {"source": "start", "target": "classifier"},
            {"source": "classifier", "sourceHandle": "category:sales", "target": "sales_text"},
            {"source": "classifier", "sourceHandle": "category:support", "target": "support_text"},
            {"source": "sales_text", "target": "sales_end"},
            {"source": "support_text", "target": "support_end"},
        ],
    }

    sales_output, sales_trace = execute_graph(graph, {"message": "I want to buy this"})
    assert sales_output == {"result": "sales"}
    assert sales_trace[1]["output"]["branch"] == "category:sales"
    assert sales_trace[1]["output"]["fallback"] is False
    assert [item["node_id"] for item in sales_trace] == ["start", "classifier", "sales_text", "sales_end"]

    fallback_output, fallback_trace = execute_graph(graph, {"message": "Something else"})
    assert fallback_output == {"result": "support"}
    assert fallback_trace[1]["output"]["branch"] == "category:support"
    assert fallback_trace[1]["output"]["fallback"] is True


def test_llm_config_supports_messages_and_structured_output():
    validate_llm_config(
        {
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": "Return JSON."},
                {"role": "user", "content": "{{inputs.message}}"},
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 2048,
            "response_format": "json_schema",
            "response_schema": {"type": "object", "properties": {"answer": {"type": "string"}}},
            "context": "{{knowledge.documents}}",
            "vision": {"enabled": True, "variable": "{{inputs.images}}", "detail": "high"},
            "reasoning": {"separate": True},
        }
    )
    validate_llm_config({"model": "legacy-model", "prompt": "Legacy prompt"})
    with pytest.raises(HTTPException):
        validate_llm_config({"model": "gpt-4.1-mini", "messages": [{"role": "user", "content": ""}]})
    with pytest.raises(HTTPException):
        validate_llm_config({"model": "gpt-4.1-mini", "prompt": "Hello", "temperature": 3})
    with pytest.raises(HTTPException):
        validate_llm_config({"model": "gpt-4.1-mini", "prompt": "Hello", "vision": {"enabled": True, "variable": "", "detail": "high"}})
    with pytest.raises(HTTPException):
        validate_llm_config({"model": "gpt-4.1-mini", "prompt": "Hello", "reasoning": {"separate": "yes"}})


def test_knowledge_config_supports_fused_retrieval_and_metadata_filters():
    validate_knowledge_config(
        {
            "dataset_ids": ["dataset-a", "dataset-b"],
            "query": "{{inputs.message}}",
            "retrieval_mode": "hybrid",
            "rerank": {"mode": "weighted", "semantic_weight": 0.8, "model_name": ""},
            "top_k": 8,
            "score_threshold": {"enabled": True, "value": 0.35},
            "metadata_filter": {
                "enabled": True,
                "logical_operator": "and",
                "conditions": [{"key": "department", "operator": "equals", "value": "sales"}],
            },
        }
    )
    validate_knowledge_config({"dataset_id": "legacy-dataset", "query": "hello", "top_k": 5})
    with pytest.raises(HTTPException):
        validate_knowledge_config({"dataset_ids": [], "query": "hello"})
    with pytest.raises(HTTPException):
        validate_knowledge_config({"dataset_ids": ["dataset-a"], "query": "hello", "rerank": {"mode": "model", "model_name": ""}})
    with pytest.raises(HTTPException):
        validate_knowledge_config({"dataset_ids": ["dataset-a"], "query": "hello", "metadata_filter": {"enabled": True, "conditions": [{"key": "", "operator": "equals", "value": "x"}]}})


def test_document_config_supports_office_pdf_operations():
    validate_document_config({"operation": "extract", "source": "{{inputs.file}}", "extract_mode": "text_tables", "ocr_fallback": True})
    validate_document_config({"operation": "create", "content": "{{llm.text}}", "format": "docx"})
    validate_document_config({"operation": "convert", "source": "{{inputs.file}}", "target_format": "pdf", "preserve_layout": True})
    validate_document_config({"operation": "merge", "sources": "{{inputs.files}}", "output_format": "pdf"})
    validate_document_config({"operation": "split", "source": "{{inputs.file}}", "split_mode": "ranges", "ranges": "1-3,4-6"})
    validate_document_config({"operation": "ocr", "source": "{{inputs.file}}", "languages": "chi_sim+eng", "ocr_output_format": "searchable_pdf", "deskew": True})
    with pytest.raises(HTTPException):
        validate_document_config({"operation": "merge", "sources": "", "output_format": "zip"})
    with pytest.raises(HTTPException):
        validate_document_config({"operation": "split", "source": "{{inputs.file}}", "split_mode": "ranges", "ranges": ""})
    with pytest.raises(HTTPException):
        validate_document_config({"operation": "ocr", "source": "{{inputs.file}}", "languages": "", "ocr_output_format": "text"})


def test_http_node_validates_and_executes_a_structured_request():
    validate_http_config({"url": "{{inputs.url}}"})

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == "https://example.test/items?page=2"
        assert request.headers["authorization"] == "Bearer secret-token"
        assert request.headers["x-workflow"] == "test"
        assert request.read() == b'{"name":"Open Workflow"}'
        return httpx.Response(201, json={"id": 42}, headers={"X-Result": "created"})

    output = execute_http_request(
        {
            "method": "POST",
            "url": "https://example.test/items",
            "query": {"page": 2},
            "headers": {"X-Workflow": "test"},
            "auth": {"type": "bearer", "token": "secret-token"},
            "body_type": "json",
            "body": {"name": "Open Workflow"},
            "timeout_seconds": 10,
            "max_response_bytes": 4096,
        },
        transport=httpx.MockTransport(handler),
    )

    assert output["status_code"] == 201
    assert output["body"] == {"id": 42}
    assert output["headers"]["x-result"] == "created"
    assert output["url"] == "https://example.test/items?page=2"
    assert output["ok"] is True
    assert output["elapsed_ms"] >= 0

    with pytest.raises(HTTPException):
        validate_http_config({"url": "file:///etc/passwd"})
    with pytest.raises(HTTPException):
        validate_http_config({"url": "https://example.test", "auth": {"type": "bearer", "token": ""}})


def test_http_node_redacts_query_credentials_and_sensitive_response_headers():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["access_token"] == "private-value"
        return httpx.Response(200, text="ok", headers={"Set-Cookie": "session=secret", "X-Result": "ok"})

    output = execute_http_request(
        {
            "url": "https://example.test/protected",
            "auth": {"type": "api_key", "key": "access_token", "value": "private-value", "location": "query"},
        },
        transport=httpx.MockTransport(handler),
    )
    assert "private-value" not in output["url"]
    assert "%5BREDACTED%5D" in output["url"]
    assert output["headers"]["set-cookie"] == "[REDACTED]"
    assert output["headers"]["x-result"] == "ok"


def test_node_retry_and_error_branch_continue_the_workflow():
    graph = {
        "schema_version": 1,
        "nodes": [
            {"id": "start", "type": "start", "data": {"config": {"triggers": ["api"], "input_fields": [{"name": "value", "type": "text"}]}}},
            {"id": "list", "type": "list", "data": {"config": {
                "source": "{{inputs.value}}",
                "operation": "sort",
                "retry": {"enabled": True, "max_retries": 2, "interval_seconds": 0},
                "error_strategy": "error_branch",
            }}},
            {"id": "success", "type": "template", "data": {"config": {"template": "success"}}},
            {"id": "recovery", "type": "template", "data": {"config": {"template": "recovered"}}},
            {"id": "success_end", "type": "end", "data": {"config": {"outputs": [{"name": "result", "value": "{{success.text}}"}]}}},
            {"id": "recovery_end", "type": "end", "data": {"config": {"outputs": [{"name": "result", "value": "{{recovery.text}}"}]}}},
        ],
        "edges": [
            {"source": "start", "target": "list"},
            {"source": "list", "target": "success"},
            {"source": "list", "sourceHandle": "error", "target": "recovery"},
            {"source": "success", "target": "success_end"},
            {"source": "recovery", "target": "recovery_end"},
        ],
    }

    output, trace = execute_graph(graph, {"value": "not-an-array"})
    assert output == {"result": "recovered"}
    assert [item["node_id"] for item in trace] == ["start", "list", "recovery", "recovery_end"]
    list_trace = trace[1]
    assert list_trace["status"] == "recovered"
    assert list_trace["attempts"] == 3
    assert list_trace["error_handled"] is True
    assert list_trace["output"]["branch"] == "error"
    assert list_trace["output"]["error_type"] == "HTTPException"


def test_template_jinja_bindings_and_variable_aggregation():
    graph = {
        "schema_version": 1,
        "nodes": [
            {"id": "start", "type": "start", "data": {"config": {"triggers": ["api"], "input_fields": [{"name": "name", "type": "text"}]}}},
            {"id": "empty", "type": "variable", "data": {"config": {"values": {"value": None}}}},
            {"id": "template", "type": "template", "data": {"config": {"inputs": [{"name": "name", "value": "{{inputs.name}}"}], "template": "Hello {{ name | upper }}!"}}},
            {"id": "aggregate", "type": "aggregate", "data": {"config": {"variables": ["{{empty.value}}", "{{template.text}}"]}}},
            {"id": "end", "type": "end", "data": {"config": {"outputs": [{"name": "result", "value": "{{aggregate.output}}"}]}}},
        ],
        "edges": [
            {"source": "start", "target": "empty"},
            {"source": "start", "target": "template"},
            {"source": "empty", "target": "aggregate"},
            {"source": "template", "target": "aggregate"},
            {"source": "aggregate", "target": "end"},
        ],
    }
    output, trace = execute_graph(graph, {"name": "Codex"})
    assert output == {"result": "Hello CODEX!"}
    aggregate_trace = next(item for item in trace if item["node_id"] == "aggregate")
    assert aggregate_trace["output"] == {"output": "Hello CODEX!", "values": [None, "Hello CODEX!"]}


def test_grouped_variable_aggregation_outputs_named_values():
    graph = {
        "schema_version": 1,
        "nodes": [
            {"id": "start", "type": "start", "data": {"config": {"triggers": ["api"], "input_fields": [{"name": "answer", "type": "text"}]}}},
            {"id": "aggregate", "type": "aggregate", "data": {"config": {"group_enabled": True, "groups": [{"name": "answer", "variables": ["{{inputs.missing}}", "{{inputs.answer}}"]}, {"name": "fallback", "variables": ["{{inputs.missing}}"]}]}}},
            {"id": "end", "type": "end", "data": {"config": {"outputs": [{"name": "answer", "value": "{{aggregate.answer}}"}]}}},
        ],
        "edges": [{"source": "start", "target": "aggregate"}, {"source": "aggregate", "target": "end"}],
    }
    output, trace = execute_graph(graph, {"answer": "done"})
    assert output == {"answer": "done"}
    assert trace[1]["output"] == {"answer": "done", "fallback": None, "output": {"answer": "done", "fallback": None}}


def test_variable_assignment_parameter_extraction_and_list_pipeline():
    variable = execute_node({
        "type": "variable",
        "data": {"config": {"assignments": [
            {"name": "items", "type": "Array", "operation": "overwrite", "value": '[{"score": 7}, {"score": 3}, {"score": 9}, {"score": 7}]'},
            {"name": "active", "type": "Boolean", "operation": "overwrite", "value": "yes"},
        ]}},
    }, {})
    assert variable["active"] is True
    assert len(variable["items"]) == 4

    listed = execute_node({
        "type": "list",
        "data": {"config": {
            "source": variable["items"],
            "filter": {"enabled": True, "field": "score", "operator": "greater_than", "value": 5},
            "sort": {"enabled": True, "key": "score", "order": "desc"},
            "unique": True,
            "limit": {"enabled": True, "count": 2},
            "nth": {"enabled": True, "index": 2},
        }},
    }, {})
    assert listed == {"items": [{"score": 9}, {"score": 7}], "item": {"score": 7}}

    extracted = execute_node({
        "type": "extract",
        "data": {"config": {
            "source": '{"customer": "Ada", "count": "3"}',
            "fields": [{"name": "customer", "type": "String"}, {"name": "count", "type": "Number"}],
        }},
    }, {})
    assert extracted == {"customer": "Ada", "count": 3}


def test_inline_code_validation_and_sandbox_execution(monkeypatch: pytest.MonkeyPatch):
    config = {
        "inputs": [{"name": "message", "type": "String", "value": "{{inputs.message}}"}],
        "source": 'def main(inputs, context):\n    print("running")\n    return {"answer": inputs["message"], "score": "7"}',
        "entrypoint": "main",
        "outputs": [{"name": "answer", "type": "String"}, {"name": "score", "type": "Number"}],
        "timeout_seconds": 30,
        "memory_mb": 256,
        "network_enabled": False,
    }
    validate_code_config(config)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "succeeded", "outputs": {"answer": "hello", "score": "7"}, "logs": ["running"], "elapsed_ms": 12}

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            assert kwargs["json"]["inputs"] == {"message": "hello"}
            assert kwargs["json"]["network_enabled"] is False
            return FakeResponse()

    monkeypatch.setattr(workflow_engine.httpx, "Client", FakeClient)
    output = execute_node({"type": "code", "data": {"config": config}}, {"inputs": {"message": "hello"}})
    assert output == {"answer": "hello", "score": 7, "_logs": ["running"], "_elapsed_ms": 12}


def test_iteration_container_executes_child_graph_for_each_item():
    graph = {
        "nodes": [
            {"id": "start", "type": "start", "data": {"config": {"triggers": ["form"], "input_fields": []}}},
            {"id": "iterate", "type": "iteration", "data": {"config": {
                "source": [1, 2, 3], "item_variable": "item", "mode": "parallel", "concurrency": 2,
                "output": "{{render.text}}",
            }}},
            {"id": "render", "type": "template", "parentNode": "iterate", "data": {"config": {
                "inputs": [{"name": "value", "value": "{{item}}"}], "template": "{{ value }}!",
            }}},
            {"id": "end", "type": "end", "data": {"config": {"outputs": [
                {"name": "result", "type": "Any", "value": "{{iterate.results}}"},
            ]}}},
        ],
        "edges": [
            {"id": "a", "source": "start", "target": "iterate"},
            {"id": "b", "source": "iterate", "target": "end"},
        ],
    }
    result, trace = execute_graph(graph, {})
    assert result == {"result": ["1!", "2!", "3!"]}
    assert [item["node_id"] for item in trace] == ["start", "iterate", "end"]


def test_loop_container_stops_when_child_condition_becomes_true():
    graph = {
        "nodes": [
            {"id": "start", "type": "start", "data": {"config": {"triggers": ["form"], "input_fields": []}}},
            {"id": "repeat", "type": "loop", "data": {"config": {
                "condition": "{{check.done}}", "max_iterations": 5, "output": "{{check.done}}",
            }}},
            {"id": "check", "type": "variable", "parentNode": "repeat", "data": {"config": {
                "assignments": [{"name": "done", "type": "Boolean", "operation": "overwrite", "value": True}],
            }}},
            {"id": "end", "type": "end", "data": {"config": {"outputs": [
                {"name": "result", "type": "Any", "value": "{{repeat.result}}"},
                {"name": "iterations", "type": "Number", "value": "{{repeat.iterations}}"},
            ]}}},
        ],
        "edges": [
            {"id": "a", "source": "start", "target": "repeat"},
            {"id": "b", "source": "repeat", "target": "end"},
        ],
    }
    result, _ = execute_graph(graph, {})
    assert result == {"result": True, "iterations": 1}


def test_container_edges_cannot_cross_the_parent_boundary():
    graph = {
        "nodes": [
            {"id": "start", "type": "start", "data": {"config": {"triggers": ["form"], "input_fields": []}}},
            {"id": "iterate", "type": "iteration", "data": {"config": {"source": [1], "item_variable": "item", "mode": "sequential", "concurrency": 1}}},
            {"id": "render", "type": "template", "parentNode": "iterate", "data": {"config": {"inputs": [{"name": "value", "value": "{{item}}"}], "template": "{{ value }}"}}},
            {"id": "end", "type": "end", "data": {"config": {"outputs": [{"name": "result", "type": "Any", "value": "{{iterate.results}}"}]}}},
        ],
        "edges": [
            {"id": "invalid", "source": "start", "target": "render"},
            {"id": "valid", "source": "iterate", "target": "end"},
        ],
    }
    with pytest.raises(HTTPException, match="container boundary"):
        workflow_engine.validate_graph(graph)


def test_incomplete_nodes_can_autosave_but_cannot_publish(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Incomplete draft"},
    ).json()
    graph = deepcopy(workflow["draft_graph"])
    graph["nodes"].append({
        "id": "template-draft",
        "type": "template",
        "position": {"x": 240, "y": 180},
        "data": {"label": "Template", "config": {"inputs": [{"name": "arg1", "value": ""}], "template": ""}},
    })
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": graph, "expected_version": workflow["draft_version"]},
    )
    assert saved.status_code == 200, saved.text
    published = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/publish",
        headers=headers,
        json={"change_note": "Must remain invalid"},
    )
    assert published.status_code == 422


def test_published_version_can_be_restored_to_draft(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Restore workflow"},
    ).json()
    published = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/publish",
        headers=headers,
        json={"change_note": "Baseline"},
    )
    assert published.status_code == 200, published.text

    edited_graph = deepcopy(workflow["draft_graph"])
    edited_graph["nodes"][0]["data"]["label"] = "Changed start"
    edited = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": edited_graph, "expected_version": workflow["draft_version"]},
    )
    assert edited.status_code == 200, edited.text

    restored = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/versions/{published.json()['id']}/restore",
        headers=headers,
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["draft_graph"]["nodes"][0]["data"]["label"] == "Start"
    assert restored.json()["draft_version"] == edited.json()["draft_version"] + 1


def test_canvas_annotations_are_not_executed(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Annotated workflow"},
    ).json()
    graph = deepcopy(workflow["draft_graph"])
    graph["nodes"].append(
        {
            "id": "note-1",
            "type": "note",
            "position": {"x": 200, "y": 20},
            "data": {"label": "Remember", "description": "Review output", "color": "yellow"},
        }
    )
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": graph, "expected_version": workflow["draft_version"]},
    )
    assert saved.status_code == 200, saved.text
    run = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/run",
        headers=headers,
        json={"inputs": {"message": "Hello"}},
    )
    assert run.status_code == 200, run.text
    assert [item["node_id"] for item in run.json()["trace"]] == ["start", "end"]


def test_management_resource_lifecycle_and_run_logs(client: TestClient):
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]

    dataset = client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge",
        headers=headers,
        json={"name": "QA knowledge", "description": "Lifecycle test"},
    )
    assert dataset.status_code == 201, dataset.text
    dataset_id = dataset.json()["id"]
    documents = client.get(
        f"/api/v1/workspaces/{workspace_id}/knowledge/{dataset_id}/documents",
        headers=headers,
    )
    assert documents.status_code == 200
    assert documents.json() == []
    assert client.delete(
        f"/api/v1/workspaces/{workspace_id}/knowledge/{dataset_id}", headers=headers
    ).status_code == 200

    model = client.post(
        f"/api/v1/workspaces/{workspace_id}/models",
        headers=headers,
        json={
            "name": "Local compatible",
            "base_url": "http://localhost:9999/v1",
            "api_key": "test-secret",
            "default_model": "test-model",
        },
    )
    assert model.status_code == 201, model.text
    assert client.delete(
        f"/api/v1/workspaces/{workspace_id}/models/{model.json()['id']}", headers=headers
    ).status_code == 200

    workflow = client.get(
        f"/api/v1/workspaces/{workspace_id}/workflows", headers=headers
    ).json()[0]
    logs = client.get(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/runs",
        headers=headers,
    )
    assert logs.status_code == 200
    assert isinstance(logs.json(), list)


def test_human_approval_pauses_and_resumes_the_selected_branch(client: TestClient):
    session = register(client, "approval-owner@example.com", "Approval Owner")
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    workflow = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Approval resume workflow"},
    ).json()
    graph = {
        "schema_version": 1,
        "nodes": [
            {
                "id": "start",
                "type": "start",
                "position": {"x": 0, "y": 0},
                "data": {"label": "Start", "config": {"triggers": ["api"], "input_fields": []}},
            },
            {
                "id": "review",
                "type": "human",
                "position": {"x": 260, "y": 0},
                "data": {
                    "label": "Review",
                    "config": {
                        "submission_methods": ["studio"],
                        "form_content": "Please review {{inputs.message}}",
                        "actions": [
                            {"id": "approve", "label": "Approve", "value": "approved", "style": "primary"},
                            {"id": "reject", "label": "Reject", "value": "rejected", "style": "danger"},
                        ],
                        "timeout_minutes": 60,
                    },
                },
            },
            {
                "id": "approved",
                "type": "end",
                "position": {"x": 520, "y": -80},
                "data": {"label": "Approved", "config": {"outputs": [{"name": "decision", "type": "String", "value": "approved"}]}},
            },
            {
                "id": "rejected",
                "type": "end",
                "position": {"x": 520, "y": 80},
                "data": {"label": "Rejected", "config": {"outputs": [{"name": "decision", "type": "String", "value": "rejected"}]}},
            },
        ],
        "edges": [
            {"source": "start", "target": "review"},
            {"source": "review", "sourceHandle": "action:approve", "target": "approved"},
            {"source": "review", "sourceHandle": "action:reject", "target": "rejected"},
        ],
    }
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}",
        headers=headers,
        json={"graph": graph, "expected_version": workflow["draft_version"]},
    )
    assert saved.status_code == 200, saved.text

    waiting = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/run",
        headers=headers,
        json={"inputs": {"message": "invoice 42"}},
    )
    assert waiting.status_code == 200, waiting.text
    assert waiting.json()["status"] == "waiting"
    assert waiting.json()["finished_at"] is None
    approvals = client.get(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/approvals",
        headers=headers,
    )
    assert approvals.status_code == 200, approvals.text
    approval = approvals.json()[0]
    assert approval["status"] == "pending"
    assert approval["request"]["form_content"] == "Please review invoice 42"

    resumed = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/runs/{waiting.json()['id']}/approvals/{approval['id']}/respond",
        headers=headers,
        json={"action_id": "approve", "data": {"reviewed": True}, "comment": "Looks good"},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "succeeded"
    assert resumed.json()["outputs"] == {"decision": "approved"}
    assert [item["node_id"] for item in resumed.json()["trace"]] == ["start", "review", "approved"]
    assert client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{workflow['id']}/runs/{waiting.json()['id']}/approvals/{approval['id']}/respond",
        headers=headers,
        json={"action_id": "reject"},
    ).status_code == 409


def test_subworkflow_maps_inputs_and_pins_the_published_version(client: TestClient):
    session = register(client, "subworkflow-owner@example.com", "Subworkflow Owner")
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]

    child = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Reusable child"},
    ).json()
    child_graph = deepcopy(child["draft_graph"])
    child_start = next(node for node in child_graph["nodes"] if node["type"] == "start")
    child_start["data"]["config"] = {
        "triggers": ["api"],
        "input_fields": [{"name": "message", "label": "Message", "type": "text", "required": True}],
    }
    child_end = next(node for node in child_graph["nodes"] if node["type"] == "end")
    child_end["data"]["config"]["outputs"] = [
        {"name": "child_value", "type": "String", "value": "v1 {{inputs.message}}"}
    ]
    child_saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{child['id']}",
        headers=headers,
        json={"graph": child_graph, "expected_version": child["draft_version"]},
    )
    assert child_saved.status_code == 200, child_saved.text
    child_v1 = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{child['id']}/publish",
        headers=headers,
        json={"access": "public", "change_note": "Child v1"},
    )
    assert child_v1.status_code == 200, child_v1.text

    parent = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Parent caller"},
    ).json()
    parent_graph = deepcopy(parent["draft_graph"])
    parent_start = next(node for node in parent_graph["nodes"] if node["type"] == "start")
    parent_start["data"]["config"] = {
        "triggers": ["api"],
        "input_fields": [{"name": "message", "label": "Message", "type": "text", "required": True}],
    }
    parent_end = next(node for node in parent_graph["nodes"] if node["type"] == "end")
    parent_end["data"]["config"]["outputs"] = [
        {"name": "result", "type": "String", "value": "{{call.child_value}}"}
    ]
    parent_graph["nodes"].append(
        {
            "id": "call",
            "type": "subworkflow",
            "position": {"x": 250, "y": 160},
            "data": {
                "label": "Call child",
                "config": {"workflow_id": child["id"], "inputs": {"message": "{{inputs.message}}"}},
            },
        }
    )
    parent_graph["edges"] = [
        {"source": "start", "target": "call"},
        {"source": "call", "target": "end"},
    ]
    parent_saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{parent['id']}",
        headers=headers,
        json={"graph": parent_graph, "expected_version": parent["draft_version"]},
    )
    assert parent_saved.status_code == 200, parent_saved.text
    draft_run = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{parent['id']}/run",
        headers=headers,
        json={"inputs": {"message": "hello"}},
    )
    assert draft_run.status_code == 200, draft_run.text
    assert draft_run.json()["outputs"] == {"result": "v1 hello"}
    parent_v1 = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{parent['id']}/publish",
        headers=headers,
        json={"access": "public", "change_note": "Pin child v1"},
    )
    assert parent_v1.status_code == 200, parent_v1.text
    pinned = parent_v1.json()["resolved_references"]["_subworkflows"]["call"]
    assert pinned["workflow_version_id"] == child_v1.json()["id"]

    child_graph_v2 = deepcopy(child_saved.json()["draft_graph"])
    child_end_v2 = next(node for node in child_graph_v2["nodes"] if node["type"] == "end")
    child_end_v2["data"]["config"]["outputs"][0]["value"] = "v2 {{inputs.message}}"
    child_v2_saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{child['id']}",
        headers=headers,
        json={"graph": child_graph_v2, "expected_version": child_saved.json()["draft_version"]},
    )
    assert child_v2_saved.status_code == 200, child_v2_saved.text
    assert client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{child['id']}/publish",
        headers=headers,
        json={"access": "public", "change_note": "Child v2"},
    ).status_code == 200

    published_run = client.post(
        f"/v1/apps/{parent['slug']}/run",
        json={"inputs": {"message": "world"}},
    )
    assert published_run.status_code == 200, published_run.text
    assert published_run.json()["outputs"] == {"result": "v1 world"}


def test_subworkflow_human_approval_resumes_across_the_nested_call(client: TestClient):
    session = register(client, "nested-approval@example.com", "Nested Approval")
    headers = auth(session)
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    child = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Approval child"},
    ).json()
    child_graph = {
        "schema_version": 1,
        "nodes": [
            {"id": "child-start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Child start", "config": {"triggers": ["api"], "input_fields": []}}},
            {
                "id": "child-review",
                "type": "human",
                "position": {"x": 220, "y": 0},
                "data": {"label": "Nested review", "config": {"submission_methods": ["studio"], "form_content": "Review nested call", "actions": [{"id": "approve", "label": "Approve", "value": "approved"}, {"id": "reject", "label": "Reject", "value": "rejected"}], "timeout_minutes": 60}},
            },
            {"id": "child-ok", "type": "end", "position": {"x": 460, "y": -60}, "data": {"label": "Approved end", "config": {"outputs": [{"name": "decision", "type": "String", "value": "approved"}]}}},
            {"id": "child-no", "type": "end", "position": {"x": 460, "y": 60}, "data": {"label": "Rejected end", "config": {"outputs": [{"name": "decision", "type": "String", "value": "rejected"}]}}},
        ],
        "edges": [
            {"source": "child-start", "target": "child-review"},
            {"source": "child-review", "sourceHandle": "action:approve", "target": "child-ok"},
            {"source": "child-review", "sourceHandle": "action:reject", "target": "child-no"},
        ],
    }
    child_saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{child['id']}",
        headers=headers,
        json={"graph": child_graph, "expected_version": child["draft_version"]},
    )
    assert child_saved.status_code == 200, child_saved.text

    parent = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows",
        headers=headers,
        json={"name": "Nested approval parent"},
    ).json()
    graph = deepcopy(parent["draft_graph"])
    end = next(node for node in graph["nodes"] if node["type"] == "end")
    end["data"]["config"]["outputs"] = [{"name": "decision", "type": "String", "value": "{{call.decision}}"}]
    graph["nodes"].append({"id": "call", "type": "subworkflow", "position": {"x": 250, "y": 160}, "data": {"label": "Call approval child", "config": {"workflow_id": child["id"], "inputs": {}}}})
    graph["edges"] = [{"source": "start", "target": "call"}, {"source": "call", "target": "end"}]
    saved = client.put(
        f"/api/v1/workspaces/{workspace_id}/workflows/{parent['id']}",
        headers=headers,
        json={"graph": graph, "expected_version": parent["draft_version"]},
    )
    assert saved.status_code == 200, saved.text
    waiting = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{parent['id']}/run",
        headers=headers,
        json={"inputs": {"message": "hello"}},
    )
    assert waiting.status_code == 200, waiting.text
    assert waiting.json()["status"] == "waiting"
    approval = client.get(
        f"/api/v1/workspaces/{workspace_id}/workflows/{parent['id']}/approvals",
        headers=headers,
    ).json()[0]
    assert approval["node_id"] == "call/child-review"
    resumed = client.post(
        f"/api/v1/workspaces/{workspace_id}/workflows/{parent['id']}/runs/{waiting.json()['id']}/approvals/{approval['id']}/respond",
        headers=headers,
        json={"action_id": "approve"},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "succeeded"
    assert resumed.json()["outputs"] == {"decision": "approved"}
    call_trace = next(item for item in resumed.json()["trace"] if item["node_id"] == "call")
    assert [item["node_id"] for item in call_trace["output"]["_trace"]] == [
        "child-start",
        "child-review",
        "child-ok",
    ]
