from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse


def custom_swagger_ui_html(app: FastAPI) -> HTMLResponse:
    openapi_url = app.openapi_url or "/openapi.json"
    default_docs = get_swagger_ui_html(
        openapi_url=openapi_url,
        title=f"{app.title} - Swagger UI",
    )
    html = bytes(default_docs.body).decode("utf-8")
    script = """
<script>
(() => {
    const hideWrapperFor = (selector) => {
        document.querySelectorAll(selector).forEach((element) => {
            const container = element.closest('.wrapper') || element.closest('div');
            if (container) {
                container.style.display = 'none';
            }
        });
    };

    const showWrapperFor = (selector) => {
        document.querySelectorAll(selector).forEach((element) => {
            const container = element.closest('.wrapper') || element.closest('div');
            if (container) {
                container.style.display = '';
            }
        });
    };

    const hideOauthExtras = () => {
        hideWrapperFor('input[name="client_id"], input[name="client_secret"]');
        hideWrapperFor('input[data-name="clientId"], input[data-name="clientSecret"]');
        hideWrapperFor('#client_id_password, #client_secret_password');
        hideWrapperFor('select[data-name="passwordType"], #password_type');

        document.querySelectorAll('.auth-container .scopes, .auth-container .scope-def').forEach((element) => {
            element.style.display = 'none';
        });

        document.querySelectorAll('.auth-container .scopes ~ p, .auth-container .scopes ~ h2').forEach((element) => {
            element.style.display = 'none';
        });

        showWrapperFor('input[name="username"], input[name="password"]');
        showWrapperFor('input[data-name="username"], input[data-name="password"]');
        showWrapperFor('#oauth_username, #oauth_password');
    };

    const observer = new MutationObserver(() => hideOauthExtras());
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener('load', hideOauthExtras);
})();
</script>
"""
    html = html.replace("</body>", f"{script}</body>")
    return HTMLResponse(content=html)
