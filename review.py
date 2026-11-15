"""StratosCAD admin agent. Uses the administrator's existing GitHub login."""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO = "bhupendrafire-ai/stratoscad-knowledge"
FIELDS = {"claim": 360, "scope": 220, "url": 600, "evidence": 400}


def api(path, method="GET", payload=None):
    args = ["gh", "api", "--method", method, f"repos/{REPO}/{path}"]
    if payload is not None:
        args.extend(["--input", "-"])
    result = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else None


def fingerprint(body):
    return hashlib.sha256(body.replace("\r\n", "\n").strip().encode()).hexdigest()[:20]


def parse(body):
    record = json.loads(body)
    if not isinstance(record, dict) or set(record) != set(FIELDS):
        raise ValueError("Expected claim, scope, url and evidence")
    for field, limit in FIELDS.items():
        s = record[field]
        if not isinstance(s, str) or not 0 < len(s.strip()) <= limit or not all(c.isprintable() for c in s):
            raise ValueError("Invalid field " + field)
    url = urlsplit(record["url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("A public HTTPS source is required")
    return record


def decide(number, decision, expected, actor):
    # The workflow supplies the identity of the authenticated comment author.
    if api(f"collaborators/{actor}/permission")["permission"] != "admin":
        raise ValueError("Only a repository administrator can decide")
    issue = api(f"issues/{number}")
    if "pull_request" in issue or issue["state"] != "open" or fingerprint(issue["body"]) != expected:
        raise ValueError("Request closed or changed. Review the current text again")
    if decision not in ("approve", "reject"):
        raise ValueError("Unknown decision")
    blob = api("contents/library.json")
    feed = json.loads(base64.b64decode(blob["content"]))
    if feed.get("schema") != 1:
        raise ValueError("Unknown feed")
    decisions = feed.setdefault("decisions", {})
    previous = decisions.get(str(number))
    decision_record = {"decision": decision, "digest": expected, "reviewer": actor}
    if previous and previous != decision_record:
        raise ValueError("Another decision already exists for this request")
    if not previous:
        if decision == "approve":
            record = parse(issue["body"])
            if not any(all(r[k] == record[k] for k in FIELDS) for r in feed["records"]):
                feed["records"].append(dict(record, request=number, reviewer=actor, review_digest=expected))
        decisions[str(number)] = decision_record
        content = (json.dumps(feed, ensure_ascii=False, indent=2) + "\n").encode()
        # The expected blob SHA serializes decisions. Retry on a concurrent change.
        api("contents/library.json", "PUT", {"message": f"{decision.title()} request #{number} reviewed by {actor}",
            "content": base64.b64encode(content).decode(), "sha": blob["sha"]})
    api(f"issues/{number}", "PATCH", {"state": "closed",
        "state_reason": "completed" if decision == "approve" else "not_planned"})
    print(f"Request {number}: {decision} by {actor}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["inbox", "inspect", "approve", "reject", "event"])
    parser.add_argument("number", type=int, nargs="?")
    parser.add_argument("digest", nargs="?")
    parser.add_argument("--brain", metavar="BRAIN_PY", type=Path,
                        help="Also search this admin PC's StratosCAD Second Brain during inspection")
    args = parser.parse_args()
    if args.mode == "inbox":
        result = subprocess.run(["gh", "issue", "list", "--repo", REPO, "--state", "open",
                                 "--limit", "100", "--json", "number,title,url"], timeout=30)
        result.check_returncode()
        return
    if args.mode == "event":
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        if event["repository"]["full_name"] != REPO or "pull_request" in event["issue"]:
            return
        m = re.fullmatch(r"/(approve|reject) ([0-9a-f]{20})", event["comment"]["body"].strip())
        if m:
            decide(event["issue"]["number"], m[1], m[2], event["comment"]["user"]["login"])
        return
    if not args.number:
        parser.error("A request number is required")
    issue = api(f"issues/{args.number}")
    digest = fingerprint(issue["body"])
    if args.mode == "inspect":
        print(json.dumps(issue["body"], ensure_ascii=True))
        if args.brain:
            record = parse(issue["body"])
            brain = args.brain.resolve(strict=True)
            # Never send a local search result back to the request or public feed.
            subprocess.run([sys.executable, str(brain), "search", "--project", "stratoscad-kernel",
                            "--limit", "3", "--", record["claim"]], timeout=30, check=True)
        print("Review the source, units and scope. Decision digest:", digest)
        return
    if args.digest != digest:
        parser.error("Review the current digest with inspect before deciding")
    # Local runs use the signed-in admin account and the same permission check as the dashboard.
    actor = subprocess.check_output(["gh", "api", "user", "--jq", ".login"], text=True, timeout=20).strip()
    decide(args.number, args.mode, digest, actor)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as e:
        sys.exit(str(e))

