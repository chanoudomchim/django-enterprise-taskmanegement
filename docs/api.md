# REST API & Webhooks Documentation — WorkFlow Enterprise

WorkFlow Enterprise provides a versioned REST API under `/api/v1/` for programmatic integration, alongside an outbound HMAC-SHA256 signed webhook dispatch system.

---

## 1. Authentication

The API supports two authentication mechanisms:
1. **Session Authentication** (for browser and HTMX requests).
2. **API Key & Secret Authentication** (for automated agents, external CLI tools, and microservices).

### Headers for API Key Authentication:
```http
X-API-Key: <client_public_key>
X-API-Secret: <client_secret_token>
Content-Type: application/json
```

---

## 2. Multi-Tenant Scoping

Every API request is filtered through `TenantFilterBackend`. An API key is bound to a single `Organization`; attempting to query or mutate records belonging to other tenants results in HTTP 404 or HTTP 403.

---

## 3. Endpoints

### Projects API
- `GET /api/v1/projects/`: List all projects in the authenticated organization.
  - Query parameters: `?status=active`, `?priority=high`, `?search=platform`
- `POST /api/v1/projects/`: Create a new project.
  ```json
  {
    "name": "Data Migration v2",
    "key": "MIG2",
    "description": "Enterprise cloud database cutover",
    "status": "planning",
    "priority": "high",
    "budget": "50000.00"
  }
  ```
- `GET /api/v1/projects/{key}/`: Retrieve project details and summary metrics.
- `PATCH /api/v1/projects/{key}/`: Update project status or budget.

### Tasks API
- `GET /api/v1/tasks/`: List tasks with tenant filtering.
  - Query parameters: `?status=in_progress`, `?priority=urgent`, `?project__key=API`
- `POST /api/v1/tasks/`: Create a task.
  ```json
  {
    "project": "6f7c6e08-25e2-45e0-9ef2-817c7689de73",
    "title": "Provision primary database cluster",
    "status": "todo",
    "priority": "high",
    "estimated_hours": "12.00"
  }
  ```
- `GET /api/v1/tasks/{id}/`: Retrieve task by UUID.
- `PATCH /api/v1/tasks/{id}/`: Update task status, priority, or progress.

---

## 4. Webhooks & HMAC Signatures

Outgoing events (e.g., `task.created`, `task.status_changed`, `project.completed`) are dispatched to registered `WebhookEndpoint` destinations.

### Security Payload Verification:
Every payload includes the header:
```http
X-WorkFlow-Signature: sha256=<hex_digest>
```
The signature is computed as:
$$\text{HMAC-SHA256}(\text{payload\_bytes}, \text{webhook\_secret})$$

Deliveries are processed asynchronously and retried up to 3 times via:
```bash
python manage.py process_webhooks
```

