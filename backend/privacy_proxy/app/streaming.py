"""Preserve Chat Completions protocol fields while restoring output text."""
import json


async def json_events(source):
    pending = b''
    data = []
    async for chunk in source:
        pending += chunk
        while b'\n' in pending:
            line, pending = pending.split(b'\n', 1)
            line = line.rstrip(b'\r')
            if line.startswith(b'data:'):
                data.append(line[5:].lstrip(b' '))
            elif not line and data:
                raw = b'\n'.join(data)
                data = []
                if raw.strip() == b'[DONE]':
                    return
                yield json.loads(raw)
    if pending.startswith(b'data:'):
        data.append(pending[5:].lstrip(b' '))
    if data:
        raw = b'\n'.join(data)
        if raw.strip() != b'[DONE]':
            yield json.loads(raw)


def restore(text, mapping):
    for token in sorted(mapping, key=len, reverse=True):
        text = text.replace(token, mapping[token])
    return text


async def transform_stream(source, mapping, split_boundary):
    buffers, envelopes = {}, {}
    async for event in json_events(source):
        if not event.get('choices'):
            # Usage-only and error events must also reach the client.
            yield event
            continue
        for position, choice in enumerate(event['choices']):
            index = choice.get('index', position)
            envelope = {k: v for k, v in event.items() if k not in ('choices', 'usage')}
            envelopes[index] = envelope
            delta = dict(choice.get('delta') or {})
            text = delta.pop('content', None)
            if delta:
                # Forward reasoning_content, role and fragmented tool_calls verbatim.
                yield {**envelope, 'choices': [{**choice, 'index': index, 'delta': delta, 'finish_reason': None}]}
            if text:
                safe, remainder = split_boundary(buffers.get(index, '') + text)
                buffers[index] = remainder
                if safe:
                    yield {**envelope, 'choices': [{'index': index, 'delta': {'content': restore(safe, mapping)}, 'finish_reason': None}]}
            if choice.get('finish_reason') is not None:
                if buffers.get(index):
                    yield {**envelope, 'choices': [{'index': index, 'delta': {'content': restore(buffers.pop(index), mapping)}, 'finish_reason': None}]}
                yield {**envelope, 'choices': [{**choice, 'index': index, 'delta': {}}]}
        if event.get('usage') is not None:
            yield {**event, 'choices': []}
    for index, text in buffers.items():
        if text:
            yield {**envelopes[index], 'choices': [{'index': index, 'delta': {'content': restore(text, mapping)}, 'finish_reason': None}]}