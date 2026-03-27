
from strands import Agent, tool
from strands.hooks import (
    HookProvider, HookRegistry, 
    BeforeInvocationEvent, AfterInvocationEvent,
    BeforeToolCallEvent, AfterToolCallEvent,
    MessageAddedEvent
)
import json

class DebugHook(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_before_invocation)
        registry.add_callback(AfterInvocationEvent, self.on_after_invocation)
        registry.add_callback(BeforeToolCallEvent, self.on_before_tool_call)
        registry.add_callback(AfterToolCallEvent, self.on_after_tool_call)
        registry.add_callback(MessageAddedEvent, self.on_message_added)

    def on_before_invocation(self, event: BeforeInvocationEvent):
        print(f"\n--- BeforeInvocationEvent ---")
        print(f"Attrs: {[a for a in dir(event) if not a.startswith('_')]}")

    def on_after_invocation(self, event: AfterInvocationEvent):
        print(f"\n--- AfterInvocationEvent ---")
        print(f"Attrs: {[a for a in dir(event) if not a.startswith('_')]}")

    def on_before_tool_call(self, event: BeforeToolCallEvent):
        print(f"\n--- BeforeToolCallEvent ---")
        print(f"Attrs: {[a for a in dir(event) if not a.startswith('_')]}")
        # Let's try to access 'tool_name' or 'arguments' if they exist (based on typical patterns)
        try:
            print(f"Tool: {event.tool_name}")
            print(f"Args: {event.arguments}")
        except Exception as e:
            print(f"Error accessing tool/args: {e}")

    def on_after_tool_call(self, event: AfterToolCallEvent):
        print(f"\n--- AfterToolCallEvent ---")
        print(f"Attrs: {[a for a in dir(event) if not a.startswith('_')]}")
        try:
            print(f"Result: {event.result}")
        except Exception as e:
            print(f"Error accessing result: {e}")

    def on_message_added(self, event: MessageAddedEvent):
        print(f"\n--- MessageAddedEvent ---")
        print(f"Attrs: {[a for a in dir(event) if not a.startswith('_')]}")
        try:
            print(f"Message: {event.message}")
        except Exception as e:
            print(f"Error accessing message: {e}")

@tool
def dummy_tool(arg1: str):
    return f"Processed {arg1}"

# We need a model to run the agent, but we can just use the events if we trigger them manually or mock it.
# For now, let's just see if we can instantiate these events and check their docs if possible.
# Actually, I'll just look at the source code of strands if I can find it in the venv.

if __name__ == "__main__":
    # Just print the dir of the event classes
    for cls in [BeforeInvocationEvent, AfterInvocationEvent, BeforeToolCallEvent, AfterToolCallEvent, MessageAddedEvent]:
        print(f"\n--- {cls.__name__} ---")
        print([a for a in dir(cls) if not a.startswith('_')])
