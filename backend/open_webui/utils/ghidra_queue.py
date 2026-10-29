"""FIFO admission to the single Ghidra instance in one Garnet worker."""
import asyncio
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class _Job:
    operation: object
    future: asyncio.Future
    emitter: object
    waiting: bool
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    started: bool = False


class GhidraQueue:
    def __init__(self):
        self._jobs = asyncio.Queue()
        self._worker = None
        self._active = None
        self._failure = None

    async def _status(self, job, description, done):
        if job.emitter:
            try:
                await job.emitter({'type': 'status', 'data': {
                    'action': 'ghidra_queue', 'description': description, 'done': done,
                }})
            except Exception:
                log.warning('Could not deliver Ghidra queue status', exc_info=True)

    async def run(self, operation, event_emitter=None):
        if self._failure is not None:
            raise self._failure
        ahead = self._jobs.qsize() + int(self._active is not None)
        job = _Job(operation, asyncio.get_running_loop().create_future(), event_emitter, ahead > 0)
        self._jobs.put_nowait(job)
        if self._worker is None:
            self._worker = asyncio.create_task(self._drain())
        try:
            if job.waiting:
                await self._status(job, f'Ghidra: waiting in queue ({ahead} ahead)', False)
            job.ready.set()
            return await asyncio.shield(job.future)
        except asyncio.CancelledError:
            if job.started:
                # Keep the caller's MCP session alive until the in-flight request
                # has finished. Cancellation must never release the next project
                # while the previous Ghidra operation is still executing.
                while not job.future.done():
                    try:
                        await asyncio.shield(job.future)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if not job.future.cancelled():
                    job.future.exception()
            else:
                job.future.cancel()
            raise
        finally:
            job.ready.set()

    async def _drain(self):
        try:
            while not self._jobs.empty():
                job = self._jobs.get_nowait()
                self._active = job
                try:
                    await job.ready.wait()
                    if job.future.cancelled():
                        if job.waiting:
                            await self._status(job, 'Ghidra: queued request cancelled', True)
                        continue
                    if self._failure is not None:
                        await self._status(job, 'Ghidra: queue paused after connection failure', True)
                        job.future.set_exception(self._failure)
                        continue
                    job.started = True
                    if job.waiting:
                        await self._status(job, 'Ghidra: request started', True)
                    try:
                        result = await job.operation()
                    except Exception as exc:
                        if getattr(exc, 'ghidra_operation_uncertain', False):
                            # A transport timeout does not prove the remote
                            # analysis stopped. Fail closed instead of switching
                            # another chat into the still-running project.
                            self._failure = exc
                        job.future.set_exception(exc)
                    else:
                        job.future.set_result(result)
                finally:
                    self._active = None
                    self._jobs.task_done()
        finally:
            self._worker = None