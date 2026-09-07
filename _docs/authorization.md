# Household Authorization

Protected views use the decorators in `core.authorization` as the single
authorization boundary. `@active_member_required` resolves the member ID from
the server-side session, verifies that the persisted member is active, and
passes the persisted `member` and `household` objects to the view. It rejects
missing, malformed, deleted, and inactive sessions with a 403 response.

Use `@creator_required` for creator-only actions. It applies the same active
session check and then compares the persisted member to the household's
persisted `creator` relationship. Views must scope any target lookup through
the injected household; request member or household IDs are never proof of
authorization.

Both decorators render the shared access-denied response, so protected views
have the same status and visible failure behavior without revealing whether an
object in another household exists.
