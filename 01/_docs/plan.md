# Shared Household Chores

## 1. Homework Goal

Build a deployable web application for roommates in one household to manage shared chores fairly. The application should track recurring chores, effort points, claims, completions, and household history while remaining simple enough to use from a desktop or mobile browser.

## 2. Locked Scope

### Users and households

- A household is created by one person.
- The creator shares an invite code for others to join.
- Members use names or nicknames; there are no email/password accounts in this version.
- The creator can manage household membership and remove members.
- All members have equal permissions for creating and editing chores.
- All members can adjust chore point values.

### Chores

Each chore has only the fields needed for the core workflow:

- Name
- Effort point value
- Recurrence configuration

Recurrence must support both fixed schedules and flexible deadline windows. A chore remains overdue until it is completed; it is not silently deleted or reset.

### Assignment and fairness

- Members can claim unassigned chores.
- Members can also be assigned chores.
- A claim is not automatically overridden by a suggestion.
- The system provides assignment suggestions but never assigns automatically.
- Suggestions consider effort points and each member's past assignments.
- Availability is out of scope for the MVP.
- Fairness is measured from the date the household was created.
- Balance is based on total effort points, not the number of chores.

### Completion and history

- A member can mark a chore complete.
- Completion records the member and timestamp.
- Members can undo or edit a completion.
- The application keeps completion history for fairness calculations and auditing.

### Reminders

- Provide in-app reminders for upcoming or overdue chores.
- Email and push notifications are out of scope.

## 3. Technical Scope

- Backend: Django
- Frontend: Django templates with HTMX and light CSS/JavaScript
- Database: PostgreSQL
- Local and deployment packaging: Docker and Docker Compose
- Testing: Django unit and integration tests for models, business rules, and important views
- Deployment documentation: include instructions for running the containerized application with a managed PostgreSQL database

The README is intentionally empty for this homework setup. Project usage and deployment documentation will be added later if required by the course.

## 4. Core User Flows

### Create or join a household

1. A user creates a household and enters a nickname.
2. The application shows an invite code.
3. Another user enters the code and chooses a nickname.
4. The new member appears in the household member list.

### Manage chores

1. A member creates a chore with a name, point value, and recurrence.
2. Any member can edit the chore or adjust its point value.
3. The recurring chore generates the next outstanding occurrence after completion.
4. Overdue occurrences remain visible until completed.

### Claim, assign, and complete

1. A member claims an available chore, or a member records an assignment.
2. The main screen shows each member's outstanding chores and total effort points.
3. The system displays suggestions for balancing effort based on historical totals.
4. A member completes a chore.
5. The application records who completed it and when, updates fairness totals, and allows the completion to be undone or edited.

### Review the household

1. Members see today's chores first.
2. The same screen shows a compact fairness summary.
3. Members can open history to review completions, assignments, and changes.
4. In-app reminders identify upcoming and overdue chores.

## 5. Proposed Domain Model

Use Django models similar to the following. Names may change during implementation, but the relationships and stored information should remain equivalent.

- `Household`: name, invite code, creator, created timestamp
- `Member`: household, nickname, joined timestamp, active status
- `Chore`: household, name, point value, recurrence type/configuration, created/updated timestamps
- `ChoreOccurrence`: chore, due/deadline data, status, claimed member, assigned member
- `Completion`: occurrence, completing member, completed timestamp, edited/undone state
- `AssignmentHistory`: occurrence, member, action, actor, timestamp
- `Reminder`: household member, occurrence, reminder type, read state, timestamps

Do not add authentication models unless the implementation requires them. A nickname-based session is sufficient for this scope, but the session must be tied to a household member rather than trusting an arbitrary nickname in each request.

## 6. Implementation Plan

### Phase 1: Project foundation

- Create the Django project and application structure.
- Add PostgreSQL configuration through environment variables.
- Add Dockerfile and Docker Compose services for the web app and database.
- Add environment templates and development commands.
- Configure static files, templates, and HTMX.

### Phase 2: Household membership

- Implement household creation and invite-code generation.
- Implement joining by invite code.
- Create nickname-based member sessions.
- Add creator-only member removal.
- Add validation for duplicate or invalid nicknames within a household.

### Phase 3: Chores and recurrence

- Implement chore CRUD available to every household member.
- Implement point-value validation and edits.
- Implement fixed recurrence schedules.
- Implement flexible deadline windows.
- Generate and maintain outstanding chore occurrences.
- Keep overdue occurrences visible.

### Phase 4: Claims, assignments, and fairness

- Implement claiming and release of unassigned occurrences.
- Implement explicit assignment.
- Record assignment changes.
- Calculate each member's total completed effort points since household creation.
- Implement suggestion logic using current totals and past assignment/completion history.
- Present suggestions without applying them automatically.

### Phase 5: Completion, history, and reminders

- Implement completion, undo, and edit flows.
- Preserve completion history and timestamps.
- Build upcoming and overdue in-app reminders.
- Add the main dashboard with today's chores and a compact fairness summary.
- Add history views for household activity.

### Phase 6: UI, reliability, and delivery

- Add responsive layouts for mobile and desktop browsers.
- Use HTMX for inline updates such as claiming, completing, and dismissing reminders.
- Add permission and validation error states.
- Add Django unit and integration tests.
- Verify the Docker Compose setup from a clean checkout.
- Document deployment to a Docker-compatible platform with managed PostgreSQL.

## 7. Acceptance Criteria

- A user can create a household and share an invite code.
- A second user can join with the invite code and a nickname.
- Any member can create, edit, and assign recurring chores.
- Chores support fixed schedules and flexible deadline windows.
- Members can claim available chores.
- The system records assignments, completions, undo/edit actions, and timestamps.
- Overdue chores remain visible until completed.
- Fairness totals use effort points and cover the full household lifetime.
- Suggestions account for effort points and past assignments but never assign automatically.
- The dashboard prioritizes today's chores and includes a fairness summary.
- In-app reminders identify upcoming and overdue chores.
- The creator can remove a member; ordinary members cannot.
- The application runs against PostgreSQL through Docker Compose.
- Automated backend tests cover the main domain rules and critical request flows.
- Deployment instructions are sufficient to run the application with a managed PostgreSQL database.

## 8. Explicit Non-Goals

- Email/password or third-party authentication
- Multiple households in one user account
- Email, SMS, or push notifications
- Availability calendars
- Categories, tags, or extra chore metadata
- Automatic assignment without member confirmation
- Advanced analytics or charts
- Native mobile applications
