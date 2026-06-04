import os
import urllib3
from dotenv import find_dotenv, load_dotenv
from jira import JIRA

# Disabling SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv(find_dotenv())

JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
JQL_QUERY = os.getenv("JQL_QUERY")

# Static review comment added on release
# Update the link below to point to your public or generic review documentation
REVIEW_STAMP = """
*Review Results:*
Readiness - OK
Synchronization - OK
Review time spent:  5 min
[Review Criteria|https://your-documentation.com]
"""

# Workflow steps to execute in order
WORKFLOW_PATH = ["assign", "finish design", "release"]

# The custom fields below are optional and commented out.
# Enable and configure them only if your specific Jira workflow requires
# filling custom fields during transitions.
#
# REFERENCE_BEHAVIOR_FIELD_ID = "customfield_000"
# REFERENCE_BEHAVIOR_TEXT = "Automated transition to 'Ready for Review' state"
# PRECONDITIONS_FIELD_ID = "customfield_000"
# PRECONDITIONS_TEXT = "see description"


def is_field_empty(issue, field_id):
    """
    Check if a Jira field is empty or not set.
    """
    value = getattr(issue.fields, field_id, None)
    return not (value and str(value).strip())


def build_fields(issue, step, assignee):
    """
    Build the field payload for a transition.

    - Always keeps the original assignee to prevent Jira conflicts.
    - Custom fields can be added here if needed for specific workflows.
    """
    fields = {}

    # Example of how to use custom fields if they are required:
    # if is_field_empty(issue, PRECONDITIONS_FIELD_ID):
    #     fields[PRECONDITIONS_FIELD_ID] = PRECONDITIONS_TEXT
    #
    # if is_field_empty(issue, REFERENCE_BEHAVIOR_FIELD_ID):
    #     fields[REFERENCE_BEHAVIOR_FIELD_ID] = REFERENCE_BEHAVIOR_TEXT

    # Always enforce original assignee (because it uses the one with the token)
    if assignee:
        fields["assignee"] = {"name": assignee}

    return fields


def safe_transition(jira, issue, t_id, fields=None, comment=None):
    """
    Execute a Jira transition with basic error handling.

    Handles:
    - Reviewer conflict (assignee must differ from reviewer)
    - Optional: Fields rejected by transition screen (fallback to direct update)
    """
    try:
        jira.transition_issue(issue, t_id, fields=fields or {}, comment=comment)
        return True

    except Exception as e:
        msg = str(e).lower()

        # Handle reviewer conflict by unassigning and retrying
        if "must not be the reviewer" in msg:
            print(" \tUnassigning due to reviewer conflict...")
            jira.assign_issue(issue, None)

            # Remove assignee from payload to avoid re-conflict
            if fields:
                fields.pop("assignee", None)

            jira.transition_issue(issue, t_id, fields=fields or {}, comment=comment)
            return True

        # Handle fields not present on transition screen (Fallback mechanism)
        if hasattr(e, "response"):
            try:
                errors = e.response.json().get("errors", {})
                if errors and fields:
                    for field_key in list(errors.keys()):
                        if field_key in fields:
                            print(f" \tFallback update for {field_key}")
                            issue.update(fields={field_key: fields[field_key]})
                            del fields[field_key]

                    jira.transition_issue(
                        issue, t_id, fields=fields or {}, comment=comment
                    )
                    return True
            except Exception:
                pass

        # Re-raise if not handled
        raise e


def automated_jira_review():
    """
    Main process:
    - Connect to Jira
    - Fetch issues via JQL
    - Execute workflow transitions sequentially
    - Preserve original assignee across transitions
    """
    print(f"\nConnecting to {JIRA_SERVER} ...")

    jira = JIRA(server=JIRA_SERVER, token_auth=JIRA_TOKEN, options={"verify": False})
    token_user = jira.myself()["name"]

    issues = jira.search_issues(JQL_QUERY, maxResults=False)
    print(f"Found {len(issues)} issues\n")

    for issue in issues:
        print(f"==>\t{issue.key} ({issue.fields.status.name})")

        # Capture original assignee once (do not rely on mutated Jira state)
        original_assignee = (
            issue.fields.assignee.name if issue.fields.assignee else token_user
        )

        try:
            for step in WORKFLOW_PATH:
                transition = next(
                    (t for t in jira.transitions(issue) if t["name"].lower() == step),
                    None,
                )

                if not transition:
                    continue

                print(f"*\tStep: {step}")

                fields = build_fields(issue, step, original_assignee)

                if step == "release":
                    # Ensure assignee is still enforced on final step
                    fields = build_fields(issue, step, None)
                    safe_transition(
                        jira,
                        issue,
                        transition["id"],
                        fields=fields,
                        comment=REVIEW_STAMP,
                    )
                    print("->\tReleased with review stamp")
                else:
                    safe_transition(jira, issue, transition["id"], fields=fields)
                    print("->\tTransition OK")

                # Refresh issue after transition
                issue = jira.issue(issue.key)
                current = issue.fields.assignee.name if issue.fields.assignee else None
                if current != original_assignee:
                    print(f"\tRestoring assignee → {original_assignee}")
                    jira.assign_issue(issue, original_assignee)

            print(f"SUCCESS:\t{issue.key} → {issue.fields.status.name}\n")

        except Exception as e:
            print(f"ERROR:\t{issue.key}: {e}\n")

    print("End of process")


if __name__ == "__main__":
    automated_jira_review()
