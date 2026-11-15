# StratosCAD engineering knowledge

[Approved library and review dashboard](https://stratoscad-knowledge.vercel.app) · [Adoption requests](https://github.com/bhupendrafire-ai/stratoscad-knowledge/issues) · [Released feed](https://stratoscad-knowledge.vercel.app/library.json)

Use the StratosCAD chat to search the collection or propose a sourced public finding. Each request includes a claim, its applicability, a source URL and a short exact excerpt. Keep customer names, drawings, screenshots and job information in the job. Requests are proposals until an administrator verifies the original source and adopts them.

## Administrator review

Start at **Adoption requests** on the dashboard. Enter the request number. Inspect the cited publisher, revision, units and scope and check for superseded or conflicting releases. Compare candidate tooling rules with governing customer specifications before using them on a job. Copy the approval or rejection and post it in the request while signed into the administrator account. The action checks current repository administrator permission and the digest of the exact request you reviewed. A change to its text needs a fresh review.

The admin can also run the agent locally with Python and their existing GitHub CLI login:

    python review.py inbox
    python review.py inspect 1
    python review.py inspect 1 --brain "PATH/TO/brain.py"
    python review.py approve 1 DIGEST
    python review.py reject 1 DIGEST

Run one decision for the reviewed request. A rejected request closes without entering the feed. Approved requests carry the reviewer and link to the request. The app caches them for offline lookup. If GitHub reports a write conflict, inspect the open request and rerun the decision. The change history is available in the Git history of library.json.

An admin running a local AI agent can ask it to read the pending requests and search only the StratosCAD project's Second Brain for supporting and conflicting evidence. Keep private notes local. Return the public source, its applicability and the digest to the administrator; run the decision only under the administrator's instruction.

The website is static. GitHub stores requests, decisions and the published feed. There is no database server or background AI worker. The search provider and chat model keep their own usage limits.
