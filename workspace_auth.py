"""Compatibility imports. The application uses boe_accounts.auth directly."""
from boe_accounts.auth import (
    initialize, sign_out, login_page, require_admin, require_permission,
    format_time, user_page, password_page, require_workspace,
    can, can_export, admin_download, APP_TITLE, PERMISSION_LABELS,
)
