from backend.fastapi.app import app


def test_router_groups_registered():
    tags = {str(route.tags[0]) for route in app.routes if getattr(route, "tags", None)}
    assert "runtime" in tags
    assert "trades" in tags
    assert "ml" in tags
    assert "ops" in tags


def test_core_paths_still_exposed():
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/runtime/status" in paths
    assert "/trades/analytics" in paths
    assert "/ml/learning-overview" in paths
    assert "/ops/readiness" in paths
