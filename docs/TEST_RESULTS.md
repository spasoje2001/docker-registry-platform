# End-to-end test results

**Date:** 03-05.02.2026.

**Version:** v0.3.0

**Tester:** Milica Đumić

## 1. Authentication flow
| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Register new user | ✅ PASS |  |
| Login with valid credentials | ✅ PASS |  |
| Login with invalid credentials | ✅ PASS | Error messages are displayed. |
| Logout | ✅ PASS |  |
| Super admin first login → forced password change | ✅ PASS | After successful first login admin must change password. |
| Profile view and edit | ✅ PASS | Registered user can change first and last name. |
| Change password | ✅ PASS |  |
| Change email | ✅ PASS | Mailhog is for verification. |

## 2. Repository flow
| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Create public repository| ✅ PASS |  |
| Create private repository | ✅ PASS |  |
| Edit repository | ✅ PASS | Edit visibility and description is possible. |
| Delete repository | ✅ PASS |  |
| View own repositories | ✅ PASS | User sees public and private repositories (Admin does not see official repositories) in profile page. |
| View repository detail | ✅ PASS |  |

## 3. Tag flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| View tags on repository | ✅ PASS |  |
| Create tag | ✅ PASS | User can create tag in owned repository. |
| Delete tag | ✅ PASS | User can delete tag in owned repository. |
| Sort tags | ✅ PASS | Sort tags by first and last adding, name A-Z and Z-A, size. |
| Filter tags | ✅ PASS |  |

## 4. Explore flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Search repositories | ✅ PASS |  |
| Filter by Official | ✅ PASS |  |
| Filter by Verified Publisher | ✅ PASS |  |
| Filter by Sponsored OSS | ✅ PASS |  |
| Sort repositories | ✅ PASS | Sort by last update, relevance, name A-Z and Z-A. |
| View repository from search results | ✅ PASS | Combined filter, search and sort queries successfully display results. |

## 5. Admin flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Super admin creates admin | ✅ PASS |  |
| Admin searches users | ✅ PASS | Super admin also can search admins. |
| Admin assigns badges | ✅ PASS  | Available badges are Verified Publisher and Sponsored OSS. |
| Admin creates official repository | ✅ PASS | Admin also can edit/delete every official repository and add/delete tags for them. |

## 6. Registry flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Push image to registry | ✅ PASS | Verified with *docker push* to localhost:5000. |
| Pull image from registry | ✅ PASS | Verified with *docker pull* |
| Tags synced to Django | ✅ PASS | *sync_tags* successfully detects registry changes and updates metadata. |

## 7. Analytics flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| View logs | ✅ PASS |  |
| Search logs by text | ✅ PASS |  |
| Filter by date range | ✅ PASS |  |
| Filter by level | ✅ PASS | Available levels are info, error and warning. |
| Complex query (AND/OR/NOT) | ✅ PASS |  |

## 8. Star flow

| Scenario | Status | Notes |
| :--- | :--- | :--- |
| Star a repository | ✅ PASS | User can star official and non-owned repository (Admin cannot star official repository). |
| Unstar a repository | ✅ PASS |  |
| View starred repositories | ✅ PASS |  |

## Bug reports

- No critical bugs found in this test circle.