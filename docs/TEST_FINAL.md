# End-to-end test results

**Date:** 03-05.02.2026.

**Version:** v0.3.0

**Tester:** Milica Đumić

## 1. Authentication flow
| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Register new user |✅ PASS |  |
| Login with valid credentials | ✅ PASS |  |
| Login with invalid credentials | ✅ PASS |  |
| Logout | ✅ PASS |  |
| Super admin first login → forced password change | ✅ PASS |  |
| Profile view and edit | ✅ PASS |  |
| Change password | ✅ PASS |  |
| Change email | ✅ PASS |  |

## 2. Repository flow
| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Create public repository| ✅ PASS |  |
| Create private repository | ✅ PASS |  |
| Edit repository | ✅ PASS |  |
| Delete repository | ✅ PASS |  |
| View own repositories | ✅ PASS |  |
| View repository detail | ✅ PASS |  |

## 3. Tag flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| View tags on repository | ✅ PASS |  |
| Create tag | ✅ PASS |  |
| Delete tag | ✅ PASS |  |
| Sort tags | ✅ PASS |  |
| Filter tags | ✅ PASS |  |

## 4. Explore flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Search repositories | ✅ PASS |  |
| Filter by Official | ✅ PASS |  |
| Filter by Verified Publisher | ✅ PASS |  |
| Filter by Sponsored OSS | ✅ PASS |  |
| Sort repositories | ✅ PASS |  |
| View repository from search results | ✅ PASS |  |

## 5. Admin flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Super admin creates admin | ✅ PASS |  |
| Admin searches users | ✅ PASS |  |
| Admin assigns badges | ✅ PASS |  |
| Admin creates official repository | ✅ PASS |  |

## 6. Registry flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Push image to registry | ✅ PASS |  |
| Pull image from registry | ✅ PASS |  |
| Tags synced to Django | ✅ PASS |  |

## 7. Analytics flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| View logs | ✅ PASS |  |
| Search logs by text | ✅ PASS |  |
| Filter by date range | ✅ PASS |  |
| Filter by level | ✅ PASS |  |
| Complex query (AND/OR/NOT) | ✅ PASS |  |
| Synchronization logs | ✅ PASS |  |

## 8. Star flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Star a repository | ✅ PASS |  |
| Unstar a repository | ✅ PASS |  |
| View starred repositories | ✅ PASS |  |

## Bug reports

- No critical bugs found in this test circle.