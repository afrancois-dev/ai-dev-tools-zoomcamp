## 1. Set up an empty Django project with a passing test
Goal: Establish the smallest runnable Django project and prove the test runner works.
Description: Create the Django project and initial application structure without implementing product behavior. Add one basic test that passes and document the command used to run the test suite.

## 2. Configure environment-based settings and local containers
Goal: Run Django and PostgreSQL locally with configuration supplied through environment variables.
Description: Add development-safe settings for the secret key, debug mode, allowed hosts, and database connection values, then create the Dockerfile and Docker Compose services. Configure persistence, service startup, and a database health check, and include an example environment file without secrets.

## 3. Configure the template and HTMX frontend foundation
Goal: Provide a shared responsive page structure that supports full-page and partial responses.
Description: Configure Django template and static-file discovery, add a minimal base layout, and include HTMX through a pinned local or CDN reference. Establish the template convention for HTMX fragments and add a smoke test for the base page.

## 4. Create the household and member data models
Goal: Persist households, their creators, and nickname-based members.
Description: Add models for a household and its members, including creation timestamps, active membership state, and the creator relationship. Add database constraints and migrations that prevent invalid household membership records.

## 5. Implement household creation with an invite code
Goal: Let a person create a household and receive a shareable invite code.
Description: Add the form, view, and template needed to create a household with the creator's nickname. Generate a unique invite code, create the initial member, and show the code after successful creation.

## 6. Implement joining a household by invite code
Goal: Let a roommate join an existing household using its invite code.
Description: Add a join form and flow that validates the code and creates an active member with a nickname. Handle invalid codes and duplicate nicknames with clear user-facing errors.

## 7. Add nickname-based member sessions
Goal: Associate each request with a selected household member without account authentication.
Description: Store the selected member in the session after household creation or joining and provide a shared request helper for retrieving the active member. Reject protected household actions when no valid active member is present.

## 8. Add creator-only member removal
Goal: Allow the household creator to remove an active member safely.
Description: Add a member-management view that is accessible only to the household creator. Deactivate the selected member, prevent removing the creator, and invalidate the removed member's future household actions.

## 9. Centralize household membership and creator authorization
Goal: Apply consistent access checks to all household actions.
Description: Create reusable authorization helpers or decorators for active membership and creator-only actions. Add focused tests proving inactive members and non-creators cannot access protected operations.

## 10. Create the chore model and migrations
Goal: Persist chores with names, point values, and recurrence configuration.
Description: Add the chore model and database migration scoped to a household. Define validation for required names, positive bounded points, and a recurrence configuration without implementing occurrence generation yet.

## 11. Implement chore CRUD and point editing
Goal: Let any active household member manage the chore catalog.
Description: Add forms, views, and templates for listing, creating, editing, and deleting chores. Allow every active member to adjust point values while applying the model validation and household authorization rules.

## 12. Implement fixed recurring schedule rules
Goal: Represent and validate fixed recurrence schedules such as daily or weekly.
Description: Define the supported fixed schedule options and validate their configuration independently of database occurrence generation. Add unit tests for valid schedules, invalid schedules, and date-boundary calculations.

## 13. Implement flexible deadline-window rules
Goal: Represent chores that can be completed within a flexible time window.
Description: Define recurrence configuration for a start date or period with a deadline window rather than one fixed due moment. Validate the window and add tests showing when an occurrence becomes overdue.

## 14. Create and maintain chore occurrences
Goal: Give each recurring chore a visible outstanding occurrence.
Description: Add occurrence storage and generation logic for both fixed schedules and flexible deadline windows. Prevent duplicate occurrences, preserve existing work, and generate the next occurrence after a completed recurring occurrence.

## 15. Track overdue occurrence state
Goal: Keep unfinished work visible after its deadline.
Description: Add status handling that identifies available, assigned, claimed, completed, and overdue occurrences. Ensure overdue occurrences remain actionable until completion and add tests for status transitions around deadlines.

## 16. Implement claiming and releasing chore occurrences
Goal: Let members claim available chores for themselves.
Description: Add actions for claiming an unassigned occurrence and releasing a claim before completion. Enforce that only active household members can claim work and that an occurrence cannot be claimed by two members at once.

## 17. Implement explicit chore assignment
Goal: Let household members assign an occurrence to a specific roommate.
Description: Add assignment controls that target active members and record the assigned member on the occurrence. Define and test how an explicit assignment interacts with an existing claim.

## 18. Record assignment history
Goal: Preserve who assigned or claimed work and when.
Description: Add an append-only history record for claims, releases, assignments, and reassignments. Expose the history for an occurrence and prevent edits that would erase the audit trail.

## 19. Implement normal chore completion
Goal: Record a valid completion and advance recurring work.
Description: Add the flow for a member to complete an occurrence, storing the completing member and timestamp. Update the occurrence state and create the next recurring occurrence when appropriate, while preserving assignment history.

## 20. Implement completion correction flows
Goal: Allow members to undo or correct an inaccurate completion.
Description: Add undo and edit actions that preserve the original completion event and its audit information. Recalculate occurrence state and recurring generation consistently after each correction, with tests for both operations.

## 21. Calculate lifetime effort totals
Goal: Show each member's completed effort points since household creation.
Description: Implement a service or query that sums valid completion points from the household creation date onward. Exclude undone completions, handle edited completion records consistently, and add tests for multiple members and recurring occurrences.

## 22. Generate non-binding assignment suggestions
Goal: Recommend fair work distribution without making automatic assignments.
Description: Implement suggestion logic that considers members' completed effort totals, current outstanding work, and past assignment history. Return ranked suggestions for display only and ensure viewing suggestions never changes claims, assignments, or completion state.

## 23. Add in-app reminder generation
Goal: Identify upcoming and overdue chores inside the application.
Description: Create reminder records or query logic for each member's upcoming and overdue occurrences, scoped to the active household. Exclude email, SMS, and push delivery and add tests for reminder eligibility.

## 24. Add reminder display and read actions
Goal: Let members review and dismiss their in-app reminders.
Description: Add reminder UI components and views that show upcoming and overdue work and allow a member to mark a reminder as read. Use HTMX for the read action and ensure one member cannot modify another member's reminders.

## 25. Build the dashboard data and page shell
Goal: Give roommates one responsive screen focused on immediate household work.
Description: Build the dashboard view and templates that prioritize today's and overdue occurrences, showing status, points, claims, and assignments. Include a compact fairness summary and the data needed for later inline actions without implementing those actions in this task.

## 26. Add HTMX dashboard actions
Goal: Make common chore actions update the dashboard without a full page reload.
Description: Add HTMX endpoints and partial responses for claiming, releasing, assigning, completing, and dismissing reminders. Return clear success and error fragments while preserving the same authorization and validation rules as the full-page flows.

## 27. Add household activity history views
Goal: Let members review what happened in the household over time.
Description: Add a paginated history view covering completions and assignment changes with relevant timestamps. Scope the results to the household and present enough context to identify the chore and member involved.

## 28. Add cross-cutting validation and conflict errors
Goal: Make invalid, stale, and conflicting actions safe and understandable.
Description: Add consistent user-facing errors for invalid forms, stale claims, deleted members, and conflicting updates. Cover representative error responses in unit and request tests without duplicating authorization logic.

## 29. Add core domain test coverage
Goal: Protect recurrence, occurrence, fairness, assignment, and completion rules.
Description: Expand unit tests for schedule calculations, occurrence generation, overdue behavior, claims, assignments, completions, corrections, and effort totals. Keep the tests focused on business rules rather than template implementation details.

## 30. Add critical request-flow test coverage
Goal: Protect the main user journeys through Django views.
Description: Add integration tests for creating a household, joining it, establishing a member session, managing a chore, claiming or assigning work, completing it, and viewing the dashboard. Include authorization and invalid-input cases for the most important endpoints.

## 31. Verify the application through Docker Compose
Goal: Confirm a clean checkout can build, migrate, run, and test the application.
Description: Exercise the image build, database migration, development server, and test commands from a clean environment. Fix configuration or startup issues found during verification and record the reliable command sequence.

## 32. Prepare deployment instructions for managed PostgreSQL
Goal: Make the containerized application deployable outside local development.
Description: Document required environment variables, migration and static-file commands, database configuration, health checks, and persistent operational settings. Target a Docker-compatible hosting platform with managed PostgreSQL and explicitly exclude provider-specific secrets from the repository.
