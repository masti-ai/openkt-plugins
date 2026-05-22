Good call — that fits naturally in the current auth refactor. Mid-request token rotation is a classic source of intermittent 401s, and the cleanest place to handle it is wherever we're already touching the auth middleware/client.

Before I dive in, let me make sure I understand the scenario you want to handle:

1. **Request starts** with token A (still valid at request start).
2. **Token A is rotated** to token B by some other path (background refresh, parallel request, server-initiated rotation) while the request is in flight.
3. **Request completes** and either:
   - (a) the response comes back fine but the next request now has a stale cached token A, OR
   - (b) the in-flight request itself gets a 401 because the server already invalidated A.

A few questions so I implement the right thing:

- **Is this for the CLI client, the MCP server, or both?** The refactor in PR #30 looks CLI-focused, so I want to confirm scope.
- **How is rotation triggered today?** Is there a background refresher, a refresh-on-401 retry, or both? That changes whether we need locking around the token store or just a retry-once-on-401 wrapper.
- **What's the token store?** In-memory only, or is it persisted (keyring, file)? If it's persisted, concurrent processes complicate things and we may need a file lock or a "read-after-write" check.

My default plan, if you want me to just go:

1. Add a single-flight refresh lock so concurrent requests don't trigger N refreshes (one refresh, others await the result).
2. On 401, re-read the token from the store before retrying — if it changed since the request started, retry with the new one; otherwise trigger a refresh.
3. Cap retries at 1 to avoid loops.
4. Add a test that simulates rotation between `getToken()` and the actual HTTP call.

Want me to proceed with that, or do you want to constrain it differently? Also — should I file this as a follow-up bead under the auth refactor epic, or fold it into the existing PR #30?
