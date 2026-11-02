# Application Security Architecture — WorkFlow Enterprise

WorkFlow Enterprise implements defense-in-depth security across every application layer, enforcing strict multi-tenancy, granular role-based access control, file upload isolation, and immutable audit logging.

---

## 1. Multi-Tenant Data Isolation

### Shared-Database, Shared-Schema Architecture
- **TenantModel Abstract Base**: Every tenant-scoped entity (`Project`, `Task`, `Comment`, `Attachment`, `TimeEntry`, `AuditLog`) inherits from `TenantModel`, which enforces a required foreign key to `Organization`.
- **TenantQuerySet & TenantManager**: Custom managers prevent cross-tenant queries.
- **TenantMiddleware**: Resolves active tenant from authenticated user session and injects `request.tenant`.
- **Foreign Key Cross-Check**: Model validation prevents cross-tenant relations (e.g. assigning a task to a project belonging to a different organization).

---

## 2. Role-Based Access Control (RBAC)

- Organization-scoped roles (`OrganizationRole`) and permissions (`RolePermission`).
- Decorators and mixins:
  - `@require_org_permission(code)`
  - `PermissionRequiredMixin`
- Default system roles: `org-admin`, `dept-manager`, `project-manager`, `standard-member`, `viewer`.
- Owners and superusers have administrative bypass within their tenant boundaries.

---

## 3. Attachment & Media Security

- **Dangerous File Extension Blocking**: Rejects extensions matching `.exe`, `.bat`, `.cmd`, `.sh`, `.bin`, `.msi`, `.dll`, `.scr`, `.php`, `.py`, `.cgi`, `.asp`, `.jsp`.
- **Maximum File Size**: Enforces a strict 25 MB file limit.
- **Authenticated Endpoint**: Attachments are served via `/media/secure/<uuid>/`, ensuring private files cannot be accessed anonymously or across tenant boundaries.

---

## 4. Immutable Audit Trail

- `apps.audit.models.AuditLog` records state mutations (CRUD operations, CSV exports, logins) with:
  - Actor User ID & Email
  - Action name (`task.create`, `report.export_csv`)
  - Target model and object representation
  - Field-level JSON change deltas
  - Client IP address and User-Agent
- Audit records are append-only.

---

## 5. Web Security Headers & Defenses

- **CSRF Protection**: Enabled on all POST/PUT/DELETE forms and HTMX ajax requests (`X-CSRFToken`).
- **XSS & Content Type Sniffing**: `SECURE_CONTENT_TYPE_NOSNIFF = True` and auto-escaped Django templates.
- **Clickjacking Protection**: `X_FRAME_OPTIONS = "DENY"`.
- **HSTS & HTTPS**: `SECURE_HSTS_SECONDS = 31536000` with subdomains and preload enabled in production.

