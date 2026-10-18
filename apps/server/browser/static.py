from fastapi import HTTPException
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles


def mount_dashboard(app, config):
    if not config.enabled or config.static_root is None:
        return
    root = config.static_root.resolve()
    if not (root / "index.html").is_file() or not (root / "assets").is_dir():
        raise ValueError("Browser static_root must be a complete reviewed dashboard build")
    app.mount(
        "/assets",
        StaticFiles(directory=root / "assets", follow_symlink=False),
        name="dashboard-assets",
    )

    async def index():
        if not (root / "index.html").is_file():
            raise HTTPException(503, "dashboard_build_unavailable")
        return FileResponse(
            root / "index.html",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": (
                    "default-src 'none'; script-src 'self'; "
                    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                    "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                    "base-uri 'none'; form-action 'self'"
                ),
                "Permissions-Policy": "microphone=(), camera=(), geolocation=()",
            },
        )

    app.add_api_route("/", index, methods=["GET"], include_in_schema=False)
    app.add_api_route("/settings", index, methods=["GET"], include_in_schema=False)
