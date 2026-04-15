"""Minimal client for Anthropic Managed Agent agent_011Ca6AntxEpH92rCjmM2S1L."""

import sys
import anthropic

AGENT_ID = "agent_011Ca6AntxEpH92rCjmM2S1L"
ENVIRONMENT_ID = "env_019wrcRqHaSHeegSGTHuRLZ3"


def main():
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Prompt: ")
    if not prompt.strip():
        print("No prompt provided.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()

    # 1. Create a session pointing at the pre-existing agent + environment
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": AGENT_ID},
        environment_id=ENVIRONMENT_ID,
    )
    print(f"Session created: {session.id}")

    # 2. Stream-first: open the SSE stream before sending the message
    #    so we don't miss early events.
    try:
        with client.beta.sessions.stream(session_id=session.id) as stream:
            # 3. Send the user message while the stream is already open
            client.beta.sessions.events.send(
                session_id=session.id,
                events=[
                    {
                        "type": "user.message",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            )

            # 4. Consume events until the agent finishes
            for event in stream:
                if event.type == "agent.message":
                    for block in event.content:
                        if block.type == "text":
                            print(block.text, end="", flush=True)

                elif event.type == "session.status_idle":
                    # Only break on terminal stop reasons; requires_action
                    # means the agent is waiting on us (custom tool, etc.)
                    if getattr(event, "stop_reason", None) and event.stop_reason.type != "requires_action":
                        break

                elif event.type == "session.status_terminated":
                    break

                elif event.type == "session.error":
                    print(f"\nSession error: {event}", file=sys.stderr)
                    sys.exit(1)

        print()  # newline after streamed output

    except anthropic.APIError as e:
        print(f"\nAPI error ({e.status_code}): {e.message}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
