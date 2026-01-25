# Authentication

## TC-001: User registration - Valid data

**Preconditions:** 
- User not logged in

**Steps:**
1. Navigate to: /accounts/register/
2. Enter username: testuser
3. Enter email: test@example.com
4. Enter password: TestPass123!
5. Confirm password: TestPass123!
6. Click "Register" button

**Expected result:**
- User account is created
- User is logged in
- Redirect to home page
- Success message: "Welcome, testuser! Your account has been created successfully."

## TC-002: User registration - Existing username

**Preconditions:** 
- User not logged in
- User with username "testuser" already exists

**Steps:**
1. Navigate to: /accounts/register/
2. Enter username: testuser
3. Enter email: test@example.com
4. Enter password: TestPass123!
5. Confirm password: TestPass123!
6. Click "Register" button

**Expected result:**
- User account is not created
- Error message: "A user with that username already exists."

## TC-003: User registration - Existing email

**Preconditions:** 
- User not logged in
- User with email "test@example.com" already exists

**Steps:**
1. Navigate to: /accounts/register/
2. Enter username: testuser
3. Enter email: test@example.com
4. Enter password: TestPass123!
5. Confirm password: TestPass123!
6. Click "Register" button

**Expected result:**
- User account is not created
- Error message: "Email already registered"

## TC-004: User registration - Different passwords

**Preconditions:** 
- User not logged in

**Steps:**
1. Navigate to: /accounts/register/
2. Enter username: testuser
3. Enter email: test@example.com
4. Enter password: TestPass123!
5. Confirm password: TestPass12!
6. Click "Register" button

**Expected result:**
- User account is not created
- Error message: "The two password fields didn’t match."

## TC-005: User registration - Too short password

**Preconditions:** 
- User not logged in

**Steps:**
1. Navigate to: /accounts/register/
2. Enter username: testuser
3. Enter email: test@example.com
4. Enter password: Test3!
5. Confirm password: Test3!
6. Click "Register" button

**Expected result:**
- User account is not created
- Error message: "This password is too short. It must contain at least 8 characters."

## TC-006: User registration - Similar password

**Preconditions:** 
- User not logged in

**Steps:**
1. Navigate to: /accounts/register/
2. Enter username: testuser
3. Enter email: test@example.com
4. Enter password: TestUser
5. Confirm password: TestUser
6. Click "Register" button

**Expected result:**
- User account is not created
- Error message: "The password is too similar to the username."

## TC-007: User registration - Common password

**Preconditions:** 
- User not logged in

**Steps:**
1. Navigate to: /accounts/register/
2. Enter username: testuser
3. Enter email: test@example.com
4. Enter password: 12345678
5. Confirm password: 12345678
6. Click "Register" button

**Expected result:**
- User account is not created
- Error message: "This password is too common."

## TC-008: User registration - Numerical password

**Preconditions:** 
- User not logged in

**Steps:**
1. Navigate to: /accounts/register/
2. Enter username: testuser
3. Enter email: test@example.com
4. Enter password: 99885748
5. Confirm password: 99885748
6. Click "Register" button

**Expected result:**
- User account is not created
- Error message: "This password is entirely numeric."

## TC-009: Login - Valid data

**Preconditions:** 
- User not logged in
- User with username "testUser" and password "TestPass123!" already exists

**Steps:**
1. Navigate to: /accounts/login/
2. Enter username: testUser
3. Enter password: TestPass123!
4. Click "Login" button

**Expected result:**
- User is logged in
- Redirect to home page
- Success message: "You have successfully logged in!"

## TC-010: Login - Non-existent username

**Preconditions:** 
- User not logged in
- User with username "testuser" does not exist

**Steps:**
1. Navigate to: /accounts/login/
2. Enter username: testuser
3. Enter password: TestPass123!
4. Click "Login" button

**Expected result:**
- User is not logged in
- Error messages: 
    - "Invalid username or password. Please try again."
    - "Please enter a correct username and password. Note that both fields may be case-sensitive."

## TC-011: Logout

**Preconditions:** 
- User is logged in

**Steps:**
1. Click "Logout" button

**Expected result:**
- User is logged out
- Success message: "You have successfully logged out!"

## TC-012: Super admin first login (Change password) - Valid data

**Preconditions:** 
- Super admin with username "admin" and generated password "GenPass123!" is generated
- Super admin is logged in with generated password
- Super admin is navigated to /password/change/

**Steps:**
1. Enter current password: GenPass123!
2. Enter password: TestPass123!
3. Confirm password: TestPass123!
4. Click "Change password" button

**Expected result:**
- Super admin remains logged in
- Redirect to home page
- Success message: "Password changed successfully! You now have full access to the application."

## TC-013: Super admin first login (Change password) - Incorrect current password

**Preconditions:** 
- Super admin with username "admin" and generated password "GenPass123!" is generated
- Super admin is logged in with generated password
- Super admin is navigated to /password/change/

**Steps:**
1. Enter current password: Gen123Pass123!
2. Enter password: TestPass123!
3. Confirm password: TestPass123!
4. Click "Change password" button

**Expected result:**
- Super admin password is not changed
- Error message: "Your old password was entered incorrectly. Please enter it again."

## TC-014: Super admin first login (Change password) - Incorrect password

**Preconditions:** 
- Super admin with username "admin" and generated password "GenPass123!" is generated
- Super admin is logged in with generated password
- Super admin is navigated to /password/change/

**Steps:**
1. Enter invalid password (e.g. too short)
2. Click "Change password" button

**Expected result:**
- Super admin password is not changed
- Password validation error displayed
- Same password rules apply as in /accounts/register/

**Note:**
Password validation rules are covered in detail in:
- TC-004 – TC-008 (User Registration)

## TC-015: Profile view and edit - Valid data

**Preconditions:** 
- User with name "Name" and last name "Surame" is logged in

**Steps:**
1. Navigate to: /accounts/profile/edit/
2. Enter first name: EditName
3. Enter last name: NewSurname
4. Click "Save changes" button

**Expected result:**
- User data is changed
- Redirect to profile page
- Success message: "Profile updated successfully."

## TC-016: Profile view and edit - Change email

**Preconditions:** 
- User with email "test@example.com" and password "TestPass123!" is logged in
- Email "test-example@email.com" is not registered in the system

**Steps:**
1. Navigate to: /accounts/profile/change-email/
2. Enter current email: test@example.com
3. Enter new email: test_exemple@email.com
4. Enter password: TestPass123!
5. Click "Send verification code" button

**Expected result:**
- Redirect to /accounts/profile/change-email/confirm/
- Success message: "Verification code sent to test_exemple@email.com. Please check your inbox."
- Next steps include some of TC-017 - TC-020

## TC-017: Profile view and edit - Valid verification code

**Preconditions:** 
- User with email "test@example.com" and password "TestPass123!" is logged in
- Logged User is trying to change email with "test-example@email.com"
- Verification code is 123456

**Steps:**
1. Navigate to: /accounts/profile/change-email/confirm/
2. Enter Verification code: 123456
3. Click "Confirm" button

**Expected result:**
- User email is changed
- Success message: "Email address changed successfully!"

## TC-018: Profile view and edit - Expired verification code

**Preconditions:** 
- User with email "test@example.com" and password "TestPass123!" is logged in
- Logged User trying to change email with "test-example@email.com"
- Verification code is 123456
- Confirm time (10 minutes) is expired

**Steps:**
1. Navigate to: /accounts/profile/change-email/confirm/
2. Enter Verification code: 123456
3. Click "Confirm" button

**Expected result:**
- User email is not changed
- Error message: "No pending email change request or code has expired."

## TC-019: Profile view and edit - Invalid verification code

**Preconditions:** 
- User with email "test@example.com" and password "TestPass123!" is logged in
- Logged User trying to change email with "test-example@email.com"
- Verification code is 123456

**Steps:**
1. Navigate to: /accounts/profile/change-email/confirm/
2. Enter Verification code: 654321
3. Click "Confirm" button

**Expected result:**
- User email is not changed
- Error message: "Invalid verification code."

## TC-020: Profile view and edit - Cancel change email

**Preconditions:** 
- User with email "test@example.com" and password "TestPass123!" is logged in
- Logged User trying to change email with "test-example@email.com"
- Verification code is 123456

**Steps:**
1. Navigate to: /accounts/profile/change-email/confirm/
3. Click "Cancel" button

**Expected result:**
- User email is not changed
- Verification code is not active anymore
- Info message: "Email change request cancelled."

## TC-021: Profile view and edit - Valid change password

**Preconditions:** 
- User with password "TestPass123!" is logged in

**Steps:**
1. Navigate to: /accounts/profile/change-password/
2. Enter current password: TestPass123!
3. Enter new password: TestPass12345!
3. Enter confirm password: TestPass12345!
5. Click "Save changes" button

**Expected result:**
- User password is changed
- Redirect to profile page
- Success message: "Password successfully changed."

## TC-022: Profile view and edit - Invalid current password

**Preconditions:** 
- User with password "TestPass123!" is logged in

**Steps:**
1. Navigate to: /accounts/profile/change-password/
2. Enter invalid current password: TestPass12345!
3. Enter new password: TestPass123!
3. Enter confirm password: TestPass123!
5. Click "Save changes" button

**Expected result:**
- User password is not changed
- Error message: "Current password wasn't correct."

## TC-023: Profile view and edit - Invalid new / confirm password

**Preconditions:** 
- User with password "TestPass123!" is logged in

**Steps:**
1. Navigate to: /accounts/profile/change-password/
2. Enter current password: TestPass123!
3. Enter invalid new password (e.g. too short)
3. Enter invalid confirm password (e.g. too short)
4. Click "Save changes" button

**Expected result:**
- User password is not changed
- Password validation error displayed
- Same password rules apply as in /accounts/register/

**Note:**
Password validation rules are covered in detail in:
- TC-004 – TC-008 (User Registration)

# Repositories

## TC-024: Create repository - public

**Preconditions:** 
- Logged user does not create repository with name "repo"

**Steps:**
1. Navigate to: /repositories/new/
2. Enter name: repo
3. Enter description: description
4. Enter initial tag: latest
5. Click "Next" button
6. Build repository following on-screen instructions
7. Click "Done" button

**Expected result:**
- Redirect to Explore page
- Public repository is created and built
- Public repository is visible on:
  - Profile page
  - Explore page

**Note:**
- User can also access "Create new repository" page via:
  - Explore tab → "New" button
  - Profile tab → "Create new repository" (result is redirecting to Profile page)

## TC-025: Create repository - Private

**Preconditions:** 
- Logged user does not create repository with name "repo"

**Steps:**
1. Repeat steps 1-3 from TC-024
2. Select repository visibility: Private
4. Complete steps 4-7 from TC-024

**Expected result:**
- Redirect to Explore page
- Private repository is created and built
- Private repository is visible on:
  - Profile page
- Private repository is not visible on:
  - Explore page

## TC-026: Create repository - Existing name

**Preconditions:** 
- Logged user already create repository with name "repo"

**Steps:**
1. Repeat steps 1-7 from TC-024

**Expected result:**
- Redirect to Explore page
- Public repository is not created

**Note:**
- Same flow is for the private repositories with existing name
- Same flow is when user use alternative ways to Create new repository from TC-024

## TC-027: Private repository view

**Preconditions:**
- User with username "testUser" is logged in
- User with username "testUser" create private repository with name "repo"

**Steps:**
1. Navigate to: /repositories/testUser/repo

**Expected result:**
- Private repository name include owner prefix (testUser/repo)
- Private repository is marked as "private"

**Note:**
- Same flow is for public repository
- Public repository does not marked as "private" (neither "public")

## TC-028: Edit repository - Owned

**Preconditions:** 
- User with username "testUser" is logged in
- User with username "testUser" made public repository with name "repo"

**Steps:**
1. Navigate to: /repositories/testUser/repo/edit/?from_explore=1
2. Change description: some new description
3. Change visibility: private
4. Click "Update" button

**Expected result:**
- Redirect to Repository page for /testUser/repo
- Success message: "Repository "testUser/repo" updated successfully!"
- Repository is changed
- Repository "repo" is only visible on Profile page

**Note:**
- Alternative navigation is /repositories/testUser/repo/edit/?from_profile=1

## TC-029: Edit repository - Admin

**Preconditions:** 
- Admin with username "testUser" is logged in
- Logged Admin created public repository with name "repo"

**Steps:**
1. Repeat steps 1-3 from TC-027
2. Check Official Repository
3. Click "Update" button

**Expected result:**
- Redirect to Repository detail page for /repo
- Success message: "Repository "repo" updated successfully!"
- Repository is changed
- Repository is official
- Official repository "repo" is only visible on Explore page

**Note:**
- Alternative navigation is /repositories/testUser/repo/edit/?from_profile=1

## TC-030: Edit repository - Not owned

**Preconditions:** 
- User with username "testUser" is logged in
- User with username "otherUser" made public repository with name "repo"

**Steps:**
1. Navigate to: /repositories/otherUser/repo/edit/?from_explore=1

**Expected result:**
- Redirect to Repository detail page for /otherUser/repo
- Error message: "You cannot edit this repository."

**Note:**
- Alternative navigation is /repositories/otherUser/repo/edit/?from_profile=1
- Same flow is for Unauthorized User 
- Same flow is for delete not owned repository
  - Navigate to:
    - /repositories/otherUser/repo/delete/?from_explore=1
    - /repositories/otherUser/repo/delete/?from_profile=1
  - Error massage: "You cannot delete this repository."

## TC-031: Delete repository - owned

**Preconditions:** 
- User with username "testUser" is logged in
- User with username "testUser" create public repository with name "repo"

**Steps:**
1. Navigate to: /repositories/testUser/repo/delete/?from_explore=1
2. Delete repository following on-screen instructions
3. Click "Delete" button

**Expected result:**
- Redirect to Explore page
- Success message: "Repository "testUser/repo" deleted."
- Repository is deleted

**Note:**
- Alternative navigation is /repositories/testUser/repo/delete/?from_profile=1
- After deleting alternative flow navigate user to Profile page

## TC-032: Repository list - Explore page

**Preconditions:** 
- User is not logged in
- Public and private repositories are built 

**Steps:**
1. Navigate to: /explore/

**Expected result:**
- Public repositories are visible
- Private repositories are not visible

**Note:**
- Authenticated users see the same public repositories on Explore page

## TC-033: Repository list - Profile page

**Preconditions:** 
- User with username "testUser" is logged in
- Public and private repositories are created and built by "testUser" 

**Steps:**
1. Navigate to: /accounts/profile/

**Expected result:**
- Public repositories are visible
- Private repositories are visible

## TC-034: Repository list - Empty list

**Preconditions:** 
- User is not logged in

**Steps:**
1. Navigate to: /explore/

**Expected result:**
- Info messages: 
  - "No Repositories Yet"
  - "No public or official repositories found."

**Note:**
- Everything is same for logged in User navigated on /profile/ except the second messages
- Messages for logged in User are:
  - "No Repositories Yet"
  - "No public or private repositories found."

## TC-035: View repository detail with tags

**Preconditions:**
- User with username "testUser" created public repository with name "repo" 
- Public repository "repo" has multiple tags (at least 2)

**Steps:**
1. Navigate to: /repositories/testUser/repo/?from_explore=1

**Expected result:**
- Repository information (name, badges, visibility, owner, descriptions,...) is displayed correctly
- Repository view has section for tags
- In tags table user can see all tags sorted by date ("latest" is first)
- Tags can be searched by name
- Tags can be sorted (name A-Z, name Z-A, size, newest, oldest)
- Tag information (name, date, size) is displayed correctly

**Note:**
- For private repositories everytnih is the same, except:
  - New precondition: User with username "testUser" is logged in
  - Navigate to: /repositories/testUser/repo/?from_profile=1

## TC-036: View repository detail with tags - Owner badges

**Preconditions:**
- User with username "testUser" has badge "Verified Publisher" 
- User "testUser" owns public repository with name "repo" 

**Steps:**
1. Navigate to: /repositories/testUser/repo/?from_explore=1

**Expected result:**
- Repeat expected results from TC-035
- Badge for Verified Publisher is displayed

**Note:**
- Badge "Sponsored OSS" have the same expected result
- If user owner do not have badges, badges are not displayed 

# Official Repositories

## TC-037: Admin creates official repo - Public

**Preconditions:**
- Logged user is Admin
- Official repository with name "repo" does not exist

**Steps:**
1. Repeat steps 1-3 from TC-024
2. Check Official Repository
3. Complete steps 4-7 from TC-024

**Expected result:**
- Redirect to Explore page
- Official repository is created and built
- Official repository owner is "Docker Official"
- Official repository is visible on:
  - Explore page
- Official repository is not visible on:
  - Profile page

**Note:**
- Admin can also access "Create new repository" page via:
  - Explore tab → "New" button
  - Profile tab → "Create new repository" (result is redirecting to Profile page)

## TC-038: Admin creates official repo - Private

**Preconditions:**
- Logged user is Admin
- Official repository with name "repo" does not exist

**Steps:**
1. Repeat steps 1-3 from TC-024
2. Select repository visibility: Private
3. Check Official Repository
4. Complete steps 4-7 from TC-024

**Expected result:**
- Redirect to Explore page
- Official repository cannot be private
- Official repository is not created

## TC-039: Admin creates official repo - Existing name

**Preconditions:** 
- Logged user is Admin
- Official repository with name "repo" exists

**Steps:**
1. Repeat steps 1-3 from TC-024
3. Check Official Repository
4. Complete steps 4-7 from TC-024

**Expected result:**
- Redirect to Explore page
- Official repository is not created

**Note:**
- Same flow is for visibility "private"

## TC-040: Edit official repo - Admin

**Preconditions:**
- Logged user is Admin
- Official repository with name "repo" exists

**Steps:**
1. Navigate to: /repositories/repo/edit/?from_explore=1
2. Complete steps 2-4 from TC-027

**Expected result:**
- Redirect to Repository detail page
- Official repository is changed
- Success message: "Repository "repo" updated successfully!"

**Note:**
- Attribute official cannot be changed.

## TC-041: Edit official repo - Regular user

**Preconditions:**
- Logged user is not Admin
- Official repository with name "repo" exists

**Steps:**
1. Navigate to: /repositories/repo/edit/?from_explore=1

**Expected result:**
- Redirect to Repository detail page

**Note:**
- Same flow is for Unauthorized User

## TC-042: Official repository view

**Preconditions:**
- Official repository with name "repo" exists

**Steps:**
1. Navigate to: /repositories/repo

**Expected result:**
- Name of official repository does not have prefix (owner name)
- Official repository has mark "official"

# Admin Panel

# TC-043: Admin lists of - Users

**Preconditions:**
- Logged user is Admin
- Users exists

**Steps:**
1. Navigate to: /accounts/admin_panel/?section=users

**Expected result:**
- Regular users are displayed in table
- Admin users are not displayed in table

# TC-044: Admin lists of - Admin users

**Preconditions:**
- Logged user is Super admin
- Users exist

**Steps:**
1. Navigate to: /accounts/admin_panel/?section=admins

**Expected result:**
- Admin users are displayed in table
- Logged Admin is marked with "you" in table
- Regular users are not displayed in table

# TC-045: Admin lists of - Not allowed

**Preconditions:**
- Logged user is not Admin
- Admin users exist

**Steps:**
1. Navigate to: /accounts/admin_panel/?section=admins

**Expected result:**
- Redirect to Home page
- Warning message: "You do not have permission to access this page."

**Note:**
- Same flow is for users, only diference is:
  - Navigate to: /accounts/admin_panel/?section=users
- In case Unauthorized User, expected results include redirection to /accounts/login/
- In case Logged user is Admin expected results include redirection to /accounts/admin_panel/?section=users

# TC-046: Admin lists of - empty

**Preconditions:**
- Logged user is Admin
- Users do not exist

**Steps:**
1. Navigate to: /accounts/admin_panel/?section=users

**Expected result:**
- Table with Users is empty
- Information message: "No users found."

# TC-047: Super admin creates admin - Valid data

**Preconditions:**
- Logged user is Super admin
- User with username "testUser" and email "test@example.com" does not exist

**Steps:**
1. Navigate to: /accounts/admin_panel/create-admin/
2. Enter username: testUser
3. Enter email: test@example.com
4. Enter first name: Name
5. Enter last name: Surname
6. Click "Create Admin" button

**Expected result:**
- Admin with username "testUser" is created
- Success message: "Admin user "testUser" created successfully."
- Redirect to page with generated password for new Admin
- New Admin is visible in table at page /accounts/admin_panel/?section=admins

**Note:**
- Alternative navigation is: Tab Admin panel → Admin management → Create Admin
- Flow is similar when Super admin does not want generated password
  1. Steps 1-5 are the same
  2. Uncheck "Generate random password"
  3. Enter password: password
  4. Enter confirm password: password
  5. Click "Create Admin" button

# TC-048: Super admin creates admin - Invalid data

**Preconditions:**
- Logged user is Super admin
- User with username "testUser" and email "test@example.com" does exist

**Steps:**
1. Navigate to: /accounts/admin_panel/create-admin/
2. Enter invalid username: testUser
3. Enter invalid email: test@example.com
4. Enter first name: Name
5. Enter last name: Surname
6. Click "Create Admin" button

**Expected result:**
- Admin with username "testUser" is not created
- Error message: "Please correct the errors below."

**Note:**
- Super admin can enter existing value for one of two attributes and Admin won't be created

# TC-049: Admin searches users - Users exist

**Preconditions:**
- Logged user is Admin
- Users exist
- User with username "testUser" exists

**Steps:**
1. Navigate to: /accounts/admin_panel/?section=users
2. Enter search term: test
3. Click "Search" button

**Expected result:**
- User "testUser" is in the table
- All users with "test" in username or email are displayed

**Note:**
- Flow is the same for searching Admin users

# TC-050: Admin searches users - Users not exist

**Preconditions:**
- Logged user is Admin
- Users exist
- User with username "testUser" does not exist

**Steps:**
1. Navigate to: /accounts/admin_panel/?section=users
2. Enter search term: test
3. Click "Search" button

**Expected result:**
- Table is empty
- Information message: "No users found."

**Note:**
- Flow is the same for search Admin users

# TC-051: Admin assigns badges

**Preconditions:**
- Logged user is Admin
- Regular user exists and does not have any badge

**Steps:**
1. Navigate to: /accounts/admin_panel/?section=users
2. Check field "Verified publisher" for regular user

**Expected result:**
- Success message: "Saved successfully ✔"
- Every regular user's repository now has badge "Verified publisher"
- Regular user now sees badge "Verified publisher" on Profile page
- Button "Clean" is visible

**Note:**
- Flow is the same for badge "Sponsored OSS"
- Flow is the same for remove badge, only need extra precondition that regular user alredy had badge

# Explore

## TC-052: Search repositories

**Preconditions:**
- At least one public repository is built
- Some public repositories contain "example" in name or description

**Steps:**
1. Navigate to: /explore/
2. Enter search term: example
3. Click search button or enter

**Expected result:**
- Search result contains exactly a subset of repositories which includes "example" in name or description
- URL is changed to /explore/explore/?filter=&sort=updated&q=example
- Information message at the bottom of the page:
  - Ranging of results (for example: "Showing 1-5 of 5 results")
  - "2 active filters" (search and filter)
  - If number of repositories is greater than 20: pagination results 
    - Current page is highlighted
    - It is possible to navigate between pages
- Button "Clean" is visible

## TC-053: Search repositories - SQL injection

**Preconditions:**
- At least one public repository is built

**Steps:**
1. Navigate to: /explore/
2. Enter malicious search term: ' OR '1'='1
3. Click search button or enter

**Expected result:**
- Search result not contains any repository
- Information message: "No public repositories found."
- Button "Clean" is visible

**Note:**
- Search is also resistant to examples:
  - '; DROP TABLE repositories_repository; --
  - admin' --
  - <script>alert('XSS')</script>
  - special character %
  - special character _

## TC-054: Search repositories - Invalid page

**Preconditions:**
- At least one public repository is built
- Result of searching is greater than 20 repositories, but number is smaller then 999

**Steps:**
1. Navigate to: /explore/explore/?filter=&sort=updated&q=example&page=999

**Expected result:**
- Current page is the last available page

**Note:**
- Case is same for negative number
- Case is same for filter or sort repositories
- For invalid page /explore/explore/?filter=&sort=updated&q=example&page=example (letters) current page is the first available page

## TC-055: Filter repositories

**Preconditions:**
- At least one public repository is built
- Some public repositories are official

**Steps:**
1. Navigate to: /explore/
2. Select filter option: Official only

**Expected result:**
- Search result contains exactly a subset of repositories which are official
- Non-official repositories are not displayed when filter is applied
- URL is changed to /explore/explore/?filter=official&sort=updated&q=
- Information message at the bottom of the page:
  - Ranging of results (for example: "Showing 1-20 of 50 results")
  - "2 active filters" (sort and filter)
  - If number of repositories is greater than 20: pagination results 
    - Current page is highlighted
    - It is possible to navigate between pages
- Button "Clean" is visible

**Note:**
- Flow is the same for
  - "Verified only":
    - Result is: subset of repositories which owner is a verified user
    - URL is: /explore/explore/?filter=verified&sort=updated&q=
  <!-- - "Sponsored only":
    - Result is: subset of repositories which owner is a sponsored oss
    - URL is: /explore/explore/?filter=sponsored&sort=updated&q= -->

## TC-056: Sort repositories

**Preconditions:**
- At least one public repository is built
- Repositories are sorted by "recently updated" at Explore page

**Steps:**
1. Navigate to: /explore/
2. Select sort option: Name (A-Z)

**Expected result:**
- Repositories are sorted by name in order A-Z
- Sorted repositories include all public repositories 
- URL is changed to /explore/explore/?filter=&sort=name_asc&q=
- Information message at the bottom of the page:
  - Ranging of results ("Showing 1-3 of 3 results")
  - "1 active filter"
  - If number of repositories is greater than 20: pagination results 
    - Current page is highlighted
    - It is possible to navigate between pages
- Button "Clean" is visible

**Note:**
- Flow is the same for sort in order:
  - Name Z-A:
    - URL is: /explore/explore/?filter=&sort=name_desc&q=
    - Repositories are sorted by name in order Z-A
  - Relevance: 
    - URL is: /explore/explore/?filter=&sort=relevance&q=
    - Repositories are sorted by relevance name

## TC-057: Clean search

**Preconditions:**
- Explore page is dispalyed
- Public repositories are filtered or sorted or searched
- Button "Clean" is visible

**Steps:**
2. Click "Clean" button

**Expected result:**
- All public repositories are displayed
- Filter and search term are cleaned
- URL is changed to /explore/explore/
- Repositories are sorted by last update ("Recently updated", default)

# Tags

## TC-058: View tags - Authorized user

**Preconditions:** 
- User with username "testUser" is logged in
- "testUser" has repository with name "repo" 
- "repo" has multiple tags (at least "latest") 

**Steps:**
1. Navigate to: /repositories/testUser/repo/tags/latest/edit/?from_profile=1

**Expected result:**
- Tags informations are correctly displayed
- Button "Delete" is clickable only if field Digests has valus

**Note:**
- If user is not logged in, button "Delete" is not visible

## TC-059: View tags - Unauthenticated user

**Preconditions:** 
- User with username "testUser" is logged in
- Other user with username "otherUser" has repository with name "repo" 
- "repo" has multiple tags (at least "latest") 

**Steps:**
1. Navigate to: /repositories/otherUser/repo/tags/latest/edit/?from_profile=1

**Expected result:**
- Tags informations are correctly displayed
- Button "Delete" is disabled

**Note:**
- User testUser must know name of repo and name of tag to access tag view page
- User testUser can not edit or delete "latest" tag
- Case is the same for unlogged user

## TC-060: Sort tags

**Preconditions:**
- Public repository "repo" at least have one tag
- Tags are sorted by "newest" at Repository detail page

**Steps:**
1. Navigate to: /repositories/testUser/repo/
2. Select sort option: Name (A-Z)

**Expected result:**
- Tags are sorted by name in order A-Z
- Sorted tags include all tags 
- URL is changed to /repositories/testUser/repo/?tag_sort=name_asc&tag_q=
- Button "Clean" is visible

**Note:**
- Flow is the same for sort in order:
  - Name Z-A:
    - URL is: /repositories/testUser/repo/?tag_sort=name_desc&tag_q=
    - Repositories are sorted by name in order Z-A
  - Oldest: 
    - URL is: /repositories/testUser/repo/?tag_sort=oldest&tag_q=
    - Repositories are sorted by relevance name
  - Size: 
    - URL is: /repositories/testUser/repo/?tag_sort=size&tag_q=
    - Repositories are sorted by relevance name

## TC-061: Search tags - With results

**Preconditions:**
- At least one tag is built for public repository with name "repo"
- Some tags contain "example" in name

**Steps:**
1. Navigate to: /repositories/testUser/repo/
2. Enter search term: example
3. Click "search" button

**Expected result:**
- Search result contains exactly a subset of tags which includes "example" in name
- URL is changed to /repositories/testUser/repo/?tag_sort=newest&tag_q=example
- Button "Clean" is visible

## TC-062: Search tags - Without results

**Preconditions:**
- At least one tag is built for public repository with name "repo"
- No one tags contain "example" in name

**Steps:**
1. Repeat steps 1-3 from TC-058

**Expected result:**
- Search result does not contains any tags
- Information message: "No tags yet" 
- URL is changed to /repositories/testUser/repo/?tag_sort=newest&tag_q=example
- Button "Clean" is visible

**Note:**
- Search tags is also resistant to SQL injection treat (similar to case TC-053)

## TC-063: Clean filter

**Preconditions:**
- Repository detail page is displayed
- Tags are sorted or searched
- Button "Clean" is visible

**Steps:**
1. Click "Clean" button

**Expected result:**
- All tags are displayed
- Filter and search term are cleaned
- URL is changed to /repositories/testUser/repo/
- Tags are sorted by newest date (default)

## TC-064: Delete tag - Authorized user

**Preconditions:**
- User is logged in
- Tag detail page is displayed (owned by logged user)
- Button "Delete" is visible

**Steps:**
1. Click "Delete" button
2. Click "Start deletion process" button
3. Following on-screen instructions
4. Click "Done" button

**Expected result:**
- Chosen tag is deleted
- URL is changed to /repositories/testUser/repo/

## TC-065: Delete tag - Unauthorized user

**Preconditions:**
- User is not logged in

**Steps:**
1. Navigate to: /repositories/testUser/repo/tags/latest/delete/sha256:123456

**Expected result:**
- Choosen tag is not deleted
- Error message: "You cannot delete tags from this repository."
- URL is changed to /repositories/testUser/repo/

# Stars

## TC-066: Staring repository

**Preconditions:** 
- User is logged in
- At least one public (non official) repository with name "repo" is built but not owned by logged user
- Public repository "repo" is not already starred by logged user

**Steps:**
1. Navigate to: /repositories/repo
2. Click "Star" button

**Expected result:**
- Star number is incremented
- Button "Star" is changed with button "Unstar"
- Success message: "Repository starred successfully!"
- Starred repository is now visible to Profile page section starred

**Note:**
- Unauthorized user does not have button "Star"
- Official repositories can not be starred

## TC-067: Unstaring repository

**Preconditions:** 
- User is logged in
- At least one public repository is starred by logged user (for example /testUser/repo)

**Steps:**
1. Navigate to: /repositories/testUser/repo
2. Click "Unstar" button

**Expected result:**
- Star number is decremented
- Button "Unstar" is changed with button "Star"
- Success message: "Repository unstarred successfully!"
- Unstarred repository is not visible to Profile page section starred

**Note:**
- Unauthorized user does not have button "Unstar"
- Official repositories can not be unstarred

## TC-068: Starred repositories

**Preconditions:** 
- User is logged in
- At least one public repository is starred by logged user (for example /testUser/repo)

**Steps:**
1. Navigate to: /accounts/profile/
2. Choose "Starred" tab

**Expected result:**
- All starred repositories (for logged user) are displayed

# Analytics

## TC-069: View logs

**Preconditions:** 
- Admin with username "testUser" is logged in
- At least one tag exists

**Steps:**
1. Navigate to: /analytics/

**Expected result:**
- All logs are displayed correctly
- Information message: for example "Found 12345 logs"
- Logs are sorted by timestamp (newest are first)
- Pagination is at the bottom of the page

**Note:**
- If logs do not exist, Admin will see message "No logs found, No logs have been indexed yet. Run <code>python manage.py index_logs</code>"

## TC-070: Sort logs

**Preconditions:** 
- Admin with username "testUser" is logged in
- At least one tag exists

**Steps:**
1. Navigate to: /analytics/
2. Click to an arrow nex to "timestamp"

**Expected result:**
- Sort direction indicator (arrow) changes state
- All logs are displayed correctly
- Information message: for example "Found 12345 logs"
- Logs are sorted by timestamp (oldest are first)
- Pagination is at the bottom of the page

## TC-071: Search logs - Valid data

**Preconditions:** 
- Admin with username "testUser" is logged in
- At least one log exists

**Steps:**
1. Navigate to: /analytics/
2. Enter term for search messages: example
3. Enter level: INFO
4. Select from date: 12.12.2025.
5. Select to date: 25.01.2026.
6. Click "Search" button

**Expected result:**
- Logs are filtered by inputed fields
- Information message: for example "Found 123 logs"
- Logs are sorted by timestamp (newest are first)
- Pagination is at the bottom of the page

**Note:**
- Admin can leave any filter field empty
- If result of analytics is empty set, information message is: "No logs found, Try adjusting your search filters"

## TC-072: Search logs - Ivalid date interval

**Preconditions:** 
- Admin with username "testUser" is logged in
- At least one log exists

**Steps:**
1. Repeat steps 1-4 form TC-071
4. Select from date: 25.01.2025.
5. Select to date: 12.12.2026.
6. Click "Search" button 

**Expected result:**
- Interval is not correct and there is no logs for displaying
- Information message: "No logs found, Try adjusting your search filters"

## TC-073: Search logs - SQL injection

**Preconditions:** 
- Admin with username "testUser" is logged in
- At least one log exists

**Steps:**
1. Navigate to: /analytics/
2. Enter term for search messages: ' OR '1'='1
6. Click "Search" button

**Expected result:**
- Result not contains any logs
- Information message: "No logs found, Try adjusting your search filters"

**Note:**
- Search logs is also resistant to SQL injection treat (similar to case TC-053).

## TC-074: Search logs - Unauthenticated user

**Preconditions:** 
- User with username "testUser" is logged in
- At least one log exists

**Steps:**
1. Navigate to: /analytics/

**Expected result:**
- Information message: "No logs found, Try adjusting your search filters"
- Redirect to Home page

**Note:**
- Case for not logged in user is similar and user gets information message: "You do not have permission to access this page."
