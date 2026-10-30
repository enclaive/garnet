def ghidra_result_indices(messages, server_id="ghidra"):
    """Identify native Ghidra results by their preceding assistant tool call.

    Content, user messages and unpaired tool results cannot opt out of scanning.
    Recompute for every request so restored conversation history is covered too.
    """
    calls = {}
    results = set()
    prefix = f"{server_id}_"
    for index, message in enumerate(messages):
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                call_id = call.get("id")
                name = (call.get("function") or {}).get("name", "")
                if call_id:
                    calls[call_id] = isinstance(name, str) and name.startswith(prefix) and len(name) > len(prefix)
        elif message.get("role") == "tool" and calls.get(message.get("tool_call_id"), False):
            results.add(index)
    return results