import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from rich.console import RenderableType
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, Static


SubmitResult: TypeAlias = Awaitable[None] | None
SubmitHandler: TypeAlias = Callable[[str], SubmitResult]
ReadyHandler: TypeAlias = Callable[[], SubmitResult]


class ShellApp(App[None]):
    CSS = """
    Screen {
        background: #0b0d12;
        color: #e5e7eb;
    }

    #shell {
        width: 100%;
        height: 100%;
        padding: 0 1 0 2;
        background: #0b0d12;
    }

    #transcript_scroll {
        height: 1fr;
        padding: 1 0 1 1;
        background: #0b0d12;
        overflow-x: hidden;
        overflow-y: auto;
        scrollbar-background: #0f1117;
        scrollbar-color: #3b4457;
    }

    #transcript_flow {
        height: auto;
    }

    .transcript-entry {
        height: auto;
        margin-bottom: 1;
    }

    #composer_wrap {
        height: auto;
        margin: 0 0 1 0;
        border-top: solid #202633;
        padding: 1 0 0 1;
    }

    #input_prompt {
        height: auto;
        margin-bottom: 1;
        color: #f8fafc;
    }

    #composer_row {
        height: auto;
        layout: horizontal;
    }

    #composer_prompt {
        width: 1;
        color: #60a5fa;
        content-align: left middle;
    }

    #composer {
        height: 1;
        width: 1fr;
        min-height: 1;
        border: none;
        background: #0b0d12;
        color: #f3f4f6;
        padding: 0;
    }

    #composer_spinner {
        width: 1;
        color: #94a3b8;
        content-align: center middle;
    }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self.on_submit: SubmitHandler | None = None
        self.on_ready: ReadyHandler | None = None
        self.submit_task: asyncio.Task[None] | None = None
        self.loading_task: asyncio.Task[None] | None = None
        self.allow_submit_while_busy = False
        self.transcript_scroll = VerticalScroll(id="transcript_scroll")
        self.transcript_flow = Vertical(id="transcript_flow")
        self.input_prompt = Static("", id="input_prompt")
        self.composer_prompt = Static(">", id="composer_prompt")
        self.composer = Input(
            placeholder="Send a message. Enter submits.",
            id="composer",
        )
        self.composer_spinner = Static("", id="composer_spinner")

    def compose(self) -> ComposeResult:
        with Container(id="shell"):
            with Vertical():
                with self.transcript_scroll:
                    yield self.transcript_flow
                with Container(id="composer_wrap"):
                    yield self.input_prompt
                    with Horizontal(id="composer_row"):
                        yield self.composer_prompt
                        yield self.composer
                        yield self.composer_spinner

    async def on_mount(self) -> None:
        self.composer.focus()
        if self.on_ready is not None:
            result = self.on_ready()
            if result is not None:
                await result

    async def _run_loading_dots(self) -> None:
        frames = ["|", "/", "-", "\\"]
        index = 0
        try:
            while True:
                self.composer_spinner.update(frames[index % len(frames)])
                index += 1
                await asyncio.sleep(0.12)
        except asyncio.CancelledError:
            self.composer_spinner.update("")
            raise

    async def _append_item(self, content: RenderableType | object) -> None:
        widget = Static(content, classes="transcript-entry")
        await self.transcript_flow.mount(widget)
        self.transcript_scroll.scroll_end(animate=False)

    def write(self, content: RenderableType | object) -> None:
        self.run_worker(self._append_item(content), exclusive=False)

    def set_loading(self, is_loading: bool) -> None:
        self.composer.placeholder = (
            "Thinking..." if is_loading else "Send a message. Enter submits."
        )
        if is_loading:
            if self.loading_task is None or self.loading_task.done():
                self.loading_task = asyncio.create_task(self._run_loading_dots())
            return

        if self.loading_task is not None and not self.loading_task.done():
            self.loading_task.cancel()
        self.loading_task = None
        self.composer_spinner.update("")

    def update_input_prompt(self, content: RenderableType | object) -> None:
        self.input_prompt.update(content)

    def clear_input_prompt(self) -> None:
        self.input_prompt.update(Text(""))

    def set_allow_submit_while_busy(self, allow: bool) -> None:
        self.allow_submit_while_busy = allow
        if allow:
            self.composer.focus()

    def set_submit_handler(self, handler: SubmitHandler) -> None:
        self.on_submit = handler

    def set_ready_handler(self, handler: ReadyHandler) -> None:
        self.on_ready = handler

    async def _run_submit_handler(self, text: str) -> None:
        current_task = asyncio.current_task()
        try:
            if self.on_submit is None:
                return
            result = self.on_submit(text)
            if result is not None:
                await result
        except Exception as exc:
            self.write(f"[bold red]Error[/bold red]\n{exc}")
        finally:
            if current_task is self.submit_task:
                self.submit_task = None

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        if text in {"/exit", "exit", "quit"}:
            self.exit()
            return
        if (
            self.submit_task is not None
            and not self.submit_task.done()
            and not self.allow_submit_while_busy
        ):
            self.bell()
            return

        self.composer.value = ""
        next_task = asyncio.create_task(self._run_submit_handler(text))
        if self.submit_task is None or self.submit_task.done():
            self.submit_task = next_task


class Shell:
    def __init__(self) -> None:
        self.app = ShellApp()
        self._pending_prints: list[RenderableType | object] = []
        self._pending_input_prompt: RenderableType | object | None = None
        self._pending_loading = False
        self._initialized = False
        self._submit_handler: SubmitHandler | None = None
        self._pending_input: asyncio.Future[str] | None = None

    def initialize(
        self,
        *,
        on_submit: SubmitHandler | None = None,
        on_ready: ReadyHandler | None = None,
    ) -> None:
        self._submit_handler = on_submit
        self.app.set_submit_handler(self._handle_submit)
        if on_ready is not None:
            self.app.set_ready_handler(on_ready)
        self._initialized = True

    async def _handle_submit(self, text: str) -> None:
        future = self._pending_input
        if future is not None and not future.done():
            future.set_result(text)
            return

        if self._submit_handler is None:
            return

        result = self._submit_handler(text)
        if result is not None:
            await result

    def _call_in_app(self, callback: Callable[[], None]) -> None:
        app_thread_id = getattr(self.app, "_thread_id", None)
        if (
            self.app.is_running
            and app_thread_id is not None
            and app_thread_id != threading.get_ident()
        ):
            self.app.call_from_thread(callback)
        else:
            callback()

    def print(self, content: RenderableType | object) -> None:
        if not self.app.is_running:
            self._pending_prints.append(content)
            return
        self._call_in_app(lambda: self.app.write(content))

    def set_loading(self, is_loading: bool) -> None:
        if not self.app.is_running:
            self._pending_loading = is_loading
            return
        self._call_in_app(lambda: self.app.set_loading(is_loading))

    def print_to_input(self, content: RenderableType | object) -> None:
        if not self.app.is_running:
            self._pending_input_prompt = content
            return
        self._call_in_app(lambda: self.app.update_input_prompt(content))

    def set_awaiting_input(self, is_awaiting: bool) -> None:
        self._call_in_app(lambda: self.app.set_allow_submit_while_busy(is_awaiting))

    def clear_input(self) -> None:
        self._pending_input_prompt = None
        self._call_in_app(self.app.clear_input_prompt)

    async def input(self) -> str:
        existing = self._pending_input
        if existing is not None and not existing.done():
            raise RuntimeError("Already waiting for input")

        if not self.app.is_running:
            raise RuntimeError("Shell input requested before app started")

        loop = asyncio.get_running_loop()
        self._pending_input = loop.create_future()
        self.set_loading(False)
        self.set_awaiting_input(True)
        try:
            return await self._pending_input
        finally:
            self._pending_input = None
            self.clear_input()
            self.set_awaiting_input(False)

    def update_region(self, name: str, content: RenderableType | object) -> None:
        return None

    def clear_region(self, name: str) -> None:
        return None

    def update_entry(self, _name: str, content: RenderableType | object) -> None:
        self.print(content)

    def clear_entry(self, _name: str) -> None:
        return None

    async def _flush_pending(self) -> None:
        self.app.set_loading(self._pending_loading)
        for content in self._pending_prints:
            self.app.write(content)
        self._pending_prints.clear()
        if self._pending_input_prompt is not None:
            self.app.update_input_prompt(self._pending_input_prompt)

    def run(self) -> None:
        if not self._initialized:
            self.initialize()

        original_ready = self.app.on_ready

        async def ready_wrapper() -> None:
            await self._flush_pending()
            if original_ready is not None:
                result = original_ready()
                if result is not None:
                    await result

        self.app.set_ready_handler(ready_wrapper)
        self.app.run()


class Agent:
    def __init__(self, shell: Shell) -> None:
        self.shell = shell

    async def run(self, text: str) -> None:
        self.shell.print_to_input("What is one detail I should include?")
        detail = await self.shell.input()
        self.shell.print(
            f"[bold magenta]Agent[/bold magenta]\nYou said: {text}\nDetail: {detail}"
        )


class Demo:
    def __init__(self) -> None:
        self.shell = Shell()
        self.agent = Agent(self.shell)

    async def on_ready(self) -> None:
        self.shell.print("Type a message and the agent will respond.")

    async def on_submit(self, text: str) -> None:
        self.shell.print(f"[bold cyan]User[/bold cyan]\n{text}")
        await self.agent.run(text)

    def run(self) -> None:
        self.shell.initialize(on_submit=self.on_submit, on_ready=self.on_ready)
        self.shell.run()


if __name__ == "__main__":
    Demo().run()
