# WorkFlow Enterprise — Complete Entity-Relationship (ER) Model

This document outlines the entity relationships across all 15 modular applications.

## High-Level Domain Model Diagram

```mermaid
erDiagram
    ORGANIZATION ||--o{ USER_MEMBERSHIP : has
    ORGANIZATION ||--o{ DEPARTMENT : contains
    ORGANIZATION ||--o{ PROJECT : owns
    ORGANIZATION ||--o{ TASK : scopes
    ORGANIZATION ||--o{ APPROVAL_WORKFLOW : defines
    ORGANIZATION ||--o{ AUDIT_LOG : tracks

    USER ||--o{ USER_MEMBERSHIP : joins
    USER ||--o{ PROJECT_MEMBERSHIP : assigned
    USER ||--o{ TASK_ASSIGNMENT : works_on
    USER ||--o{ TIME_ENTRY : logs
    USER ||--o{ NOTIFICATION : receives

    DEPARTMENT ||--o{ TEAM : contains
    DEPARTMENT ||--o{ DEPARTMENT_MEMBERSHIP : has
    TEAM ||--o{ TEAM_MEMBERSHIP : has

    PROJECT ||--o{ PROJECT_MEMBERSHIP : has
    PROJECT ||--o{ PROJECT_MILESTONE : tracks
    PROJECT ||--o{ TASK : contains

    TASK ||--o{ TASK_ASSIGNMENT : has
    TASK ||--o{ TASK_CHECKLIST : contains
    TASK ||--o{ TASK_DEPENDENCY : depends_on
    TASK ||--o{ COMMENT : has
    TASK ||--o{ ATTACHMENT : stores
    TASK ||--o{ TIME_ENTRY : records

    APPROVAL_WORKFLOW ||--o{ APPROVAL_STAGE : includes
    APPROVAL_REQUEST }|--|| APPROVAL_WORKFLOW : uses
    APPROVAL_REQUEST ||--o{ APPROVAL_DECISION : records
```

---

## Detailed Data Model Specifications by Module

### 1. Accounts & Multi-Tenancy (`apps/accounts`, `apps/organizations`)
```mermaid
erDiagram
    USER {
        uuid id PK
        string email UK
        string first_name
        string last_name
        boolean is_active
        boolean is_staff
        boolean is_superuser
        datetime date_joined
        datetime last_login
    }

    USER_PROFILE {
        uuid id PK
        uuid user_id FK
        string avatar
        string phone_number
        string title
        string bio
        string timezone
        string theme_preference
    }

    ORGANIZATION {
        uuid id PK
        string name
        string slug UK
        string logo
        string primary_color
        boolean is_active
        datetime created_at
    }

    ORGANIZATION_MEMBERSHIP {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string role
        boolean is_default
        boolean is_active
        datetime joined_at
    }

    ORGANIZATION_INVITATION {
        uuid id PK
        uuid organization_id FK
        string email
        string role
        string token UK
        string status
        datetime expires_at
    }

    USER ||--|| USER_PROFILE : has
    USER ||--o{ ORGANIZATION_MEMBERSHIP : holds
    ORGANIZATION ||--o{ ORGANIZATION_MEMBERSHIP : contains
    ORGANIZATION ||--o{ ORGANIZATION_INVITATION : issues
```

### 2. RBAC & Organization Structure (`apps/rbac`, `apps/departments`)
```mermaid
erDiagram
    ORGANIZATION_ROLE {
        uuid id PK
        uuid organization_id FK
        string name
        string slug
        string description
        boolean is_system_role
    }

    ROLE_PERMISSION {
        uuid id PK
        uuid role_id FK
        string permission_code
    }

    DEPARTMENT {
        uuid id PK
        uuid organization_id FK
        uuid manager_id FK
        string name
        string code
        text description
    }

    TEAM {
        uuid id PK
        uuid organization_id FK
        uuid department_id FK
        uuid lead_id FK
        string name
        text description
    }

    TEAM_MEMBERSHIP {
        uuid id PK
        uuid team_id FK
        uuid user_id FK
        string role_in_team
    }

    ORGANIZATION ||--o{ ORGANIZATION_ROLE : defines
    ORGANIZATION_ROLE ||--o{ ROLE_PERMISSION : includes
    ORGANIZATION ||--o{ DEPARTMENT : maintains
    DEPARTMENT ||--o{ TEAM : houses
    TEAM ||--o{ TEAM_MEMBERSHIP : assigns
```

### 3. Projects & Advanced Tasks (`apps/projects`, `apps/tasks`)
```mermaid
erDiagram
    PROJECT {
        uuid id PK
        uuid organization_id FK
        uuid owner_id FK
        uuid manager_id FK
        string name
        string key UK
        text description
        string status
        date start_date
        date target_end_date
        decimal budget
        integer progress_percentage
    }

    PROJECT_MILESTONE {
        uuid id PK
        uuid project_id FK
        string title
        date due_date
        string status
    }

    TASK {
        uuid id PK
        uuid organization_id FK
        uuid project_id FK
        uuid parent_task_id FK
        uuid created_by_id FK
        string task_key UK
        string title
        text description
        string status
        string priority
        uuid category_id FK
        date start_date
        date due_date
        decimal estimated_hours
        decimal actual_hours
        integer progress
        integer position
    }

    TASK_ASSIGNMENT {
        uuid id PK
        uuid task_id FK
        uuid user_id FK
        datetime assigned_at
    }

    TASK_CHECKLIST {
        uuid id PK
        uuid task_id FK
        string title
    }

    TASK_CHECKLIST_ITEM {
        uuid id PK
        uuid checklist_id FK
        string content
        boolean is_completed
        uuid completed_by_id FK
    }

    TASK_DEPENDENCY {
        uuid id PK
        uuid blocking_task_id FK
        uuid dependent_task_id FK
        string dependency_type
    }

    PROJECT ||--o{ PROJECT_MILESTONE : tracks
    PROJECT ||--o{ TASK : contains
    TASK ||--o{ TASK_ASSIGNMENT : assigned_to
    TASK ||--o{ TASK_CHECKLIST : has
    TASK_CHECKLIST ||--o{ TASK_CHECKLIST_ITEM : items
    TASK ||--o{ TASK_DEPENDENCY : blockers
```

### 4. Collaboration, Approvals & Time Tracking (`apps/collaboration`, `apps/approvals`, `apps/time_tracking`)
```mermaid
erDiagram
    COMMENT {
        uuid id PK
        uuid task_id FK
        uuid author_id FK
        text content
        datetime created_at
        datetime updated_at
    }

    ATTACHMENT {
        uuid id PK
        uuid organization_id FK
        uuid task_id FK
        uuid uploaded_by_id FK
        string file
        string original_filename
        integer file_size
        string mime_type
    }

    APPROVAL_WORKFLOW {
        uuid id PK
        uuid organization_id FK
        string name
        text description
        boolean is_active
    }

    APPROVAL_REQUEST {
        uuid id PK
        uuid organization_id FK
        uuid workflow_id FK
        uuid task_id FK
        uuid requester_id FK
        string status
        text notes
    }

    APPROVAL_DECISION {
        uuid id PK
        uuid request_id FK
        uuid approver_id FK
        string decision
        text comments
        datetime decided_at
    }

    TIME_ENTRY {
        uuid id PK
        uuid organization_id FK
        uuid task_id FK
        uuid user_id FK
        date work_date
        decimal hours
        text description
        boolean is_billable
    }

    ACTIVE_TIMER {
        uuid id PK
        uuid user_id UK
        uuid task_id FK
        datetime started_at
        text description
    }

    TASK ||--o{ COMMENT : receives
    TASK ||--o{ ATTACHMENT : stores
    TASK ||--o{ APPROVAL_REQUEST : triggers
    APPROVAL_WORKFLOW ||--o{ APPROVAL_REQUEST : guides
    APPROVAL_REQUEST ||--o{ APPROVAL_DECISION : resolves
    TASK ||--o{ TIME_ENTRY : logs
    USER ||--o| ACTIVE_TIMER : runs
```

---

## 5. Security & Isolation Invariants

1. **Organization Scoping:** Every business entity contains `organization_id` as non-nullable foreign key with index, except for global accounts and platform superusers.
2. **Compound Unique Constraints:** Keys such as `(organization_id, task_key)` and `(organization_id, project_key)` ensure uniqueness within an enterprise boundary without cross-tenant collisions.
3. **Cascading Strategies:** Deleting an organization cascades deletions across its sub-entities; soft-deactivation flags (`is_active = False`) are used for business operations to preserve audit trails.

