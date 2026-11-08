# MATRIX Personal Account Operations & Security Report

**Date:** November 8, 2026  
**Module:** `core/account_operations/` & `agents/personal/agent.py`  
**Security Architecture:** 3-Tier Autonomy Policy & Token Vault  
**Data Partition:** `D:\matrix_data\accounts\` & `D:\matrix_data\drafts\`  
**Verification Script:** `scripts/test_account_permissions.py` (4/4 PASS)

---

## 1. Executive Summary

MATRIX incorporates a dedicated Personal Account Operations layer designed to safely interact with user services (Email, GitHub, Messaging, Google, Slack, Notion) without ever compromising user credentials or bypassing safety policies.

Key Guarantees:
1. **Strict Truthfulness:** MATRIX never hallucinates or fabricates access to an unconnected account. If an account is not registered in the local vault, MATRIX transparently declares it not connected and instructs the user how to authorize it.
2. **Credential Isolation:** Account metadata is stored in `D:\matrix_data\accounts\accounts.json` without raw credentials. Secret tokens are isolated in a restricted vault (`vault.dat`).
3. **Safe Draft-First Workflow:** Creating an email or message draft is performed entirely on local disk (`D:\matrix_data\drafts\`) with zero external transmission risk.
4. **Enforced Level 3 Security Boundary:** External email transmission, social publishing, or permanent account deletions strictly require explicit human confirmation via the Policy Gate before dispatch.

---

## 2. Core Architecture (`core/account_operations/`)

### Data Models (`models.py`)
- **`ServiceType`:** `email`, `github`, `google`, `slack`, `notion`, `generic`
- **`AuthType`:** `oauth2`, `token`, `app_password`, `local`
- **`AccountStatus`:** `active`, `pending_auth`, `expired`, `revoked`
- **`ConnectedAccount`:** Stores `account_id`, `service`, `account_name`, `email`, `scopes`, `status`, and `credential_ref` (hash pointer to vault).
- **`AccountOperationRecord`:** Audit log record detailing every account operation, status, and required policy level.

### Secure Account Registry (`registry.py`)
- **Metadata Storage:** Sanitized JSON database at `D:\matrix_data\accounts\accounts.json`.
- **Credential Vault:** Isolated byte-encoded key store at `D:\matrix_data\accounts\vault.dat`.
- **Query APIs:**
  - `list_connected_accounts()`: Enumerates authorized accounts without exposing secret tokens.
  - `get_account_by_service(service_name)`: Queries authorized accounts by service type.
  - `register_account(...)`: Enrolls a newly authenticated service.
  - `revoke_account(account_id)`: Removes metadata and purges vault credentials immediately.

### Account Operations Manager (`manager.py`)
- **Safe Email Drafting:**
  - Writes structured draft JSON files into `D:\matrix_data\drafts\draft_<timestamp>_<op_id>.json`.
  - Captures `recipient`, `subject`, `body`, and audit metadata.
  - Verifies local file integrity before returning success.
- **Strict Unconnected Service Defense:**
  - When `search_account_data(service, query)` is called for an unconnected service (e.g. `slack`), it immediately returns:
    `status: "NOT_CONNECTED", message: "No authorized slack account is currently connected to MATRIX."`
- **GitHub Repository Inspection:**
  - Queries public and authenticated GitHub repositories using the GitHub REST API (`https://api.github.com/repos/{owner}/{repo}`).
  - Extracts repository stars, forks, open issues count, default branch, license, and description.

---

## 3. Autonomy Policy Gate Boundaries

| Action Category | Operation Type | Autonomy Level | Human Confirmation Required? |
| :--- | :--- | :---: | :---: |
| **Inspect Accounts** | `account_registry.list_connected_accounts()` | **Level 1** | No (Automatic) |
| **Inspect Public Repo** | `account_operations.inspect_github_repository()` | **Level 1** | No (Automatic) |
| **Draft Email** | `account_operations.draft_email()` (Saved locally to disk) | **Level 1** | No (Automatic) |
| **Search Account Data** | Querying connected account endpoints | **Level 2** | No (Allowlist-gated) |
| **External Email Send** | Transmitting email to external SMTP server | **Level 3** | **YES (Mandatory Confirmation)** |
| **Revoke / Delete Account** | Deleting account credentials or stored data | **Level 3** | **YES (Mandatory Confirmation)** |

---

## 4. Test Verification Evidence (`scripts/test_account_permissions.py`)

```
======================================================================
  MATRIX PERSONAL ACCOUNT OPERATIONS & PERMISSIONS TEST
======================================================================
[STAGE 1/4] Account registry integrity & strict truthfulness:
  [PASS] Currently connected accounts: 0
  [PASS] Strict truthfulness verified: Refused to fabricate data for unconnected service 'slack'.
         Response: No authorized slack account is currently connected to MATRIX. You can connect it in Settings.

[STAGE 2/4] Safe local email draft creation:
  [PASS] Email draft created locally at 'D:\matrix_data\drafts\draft_1794114827_op_draft_b87c2dac.json' (421 bytes).

[STAGE 3/4] Level 3 authorization boundary for external email sending:
  [PASS] External transmission blocked by Policy Gate. Requires explicit Level 3 confirmation.
         Required Autonomy Level: 3 | Confirmation Reason: Action 'publish_external_message' requires explicit user authorization under Level 3 policy.

[STAGE 4/4] Live GitHub public repository inspection:
  [PASS] Inspected GitHub repository: psf/requests
         Stars: 54725 | Forks: 11521 | Description: A simple, yet elegant, HTTP library.

RESULT: 4/4 STAGES PASSED. STATUS: PASS
======================================================================
```
