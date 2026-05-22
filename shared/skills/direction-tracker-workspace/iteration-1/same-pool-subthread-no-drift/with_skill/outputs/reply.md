Yep, that slots into Pool 1 cleanly — added it under the auth refactor as `LEADING`. No drift flag; same module, same surface.

On the mid-request rotation: the failure mode is usually that request A reads token T1, the refresher rotates to T2 before A's downstream call lands, and A gets a 401 even though the session is still valid. A few shapes for the fix, depending on where you want the seam:

1. **Single-flight refresh with request-scoped token snapshot.** Capture the token at the start of the request (snapshot semantics), and if the downstream 401s, retry once with a fresh read from the token store. The refresher uses single-flight (sync.Once / mutex) so concurrent requests don't trigger N rotations. Cheap to implement, but you eat one retry per rotation collision.

2. **Generation counter on the token.** Each rotation bumps a counter. The request carries the generation it started with; on 401, the auth middleware compares generations and only retries if the live generation is ahead. Avoids retrying on actual auth failures (wrong creds), only retries on rotation races.

3. **Refresh-ahead with overlap window.** The refresher rotates T1 → T2 but keeps T1 valid for a short grace window (e.g., 30s). In-flight requests using T1 still succeed. This is the cleanest semantically but requires the token issuer to support overlap, which not every backend does.

For a CLI specifically, I'd lean toward (1) + (2) combined: single-flight refresh, request-scoped snapshot, and a generation check so you only retry on actual rotation collisions and not on real auth errors. (3) is overkill unless you're seeing it under load.

Which auth backend are you against — your own issuer, or something like Cognito / Auth0 / Supabase? That changes whether (3) is even available, and it'll determine where the retry boundary sits (HTTP client interceptor vs the kt command wrapper).
