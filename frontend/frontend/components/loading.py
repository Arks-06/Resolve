import reflex as rx

def agent_thinking_indicator() -> rx.Component:
    """A stylish loading indicator for the chat interface."""
    return rx.box(
        rx.hstack(
            rx.spinner(size="2", color=rx.color("blue", 9)),
            rx.text(
                "Agent is orchestrating workflow...", 
                size="2", 
                color="gray",
                style={"animation": "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite"}
            ),
            align_items="center",
            gap="3",
        ),
        padding="1em",
        border_radius="md",
        bg=rx.color("blue", 2),
        margin_y="1em",
        width="fit-content",
    )