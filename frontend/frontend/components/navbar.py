import reflex as rx
from frontend.state.base_state import AppState

def navbar() -> rx.Component:
    """The main application navigation bar."""
    return rx.hstack(
        # Left side: Brand/Logo
        rx.hstack(
            rx.icon("bot", size=24, color=rx.color("blue", 9)),
            rx.heading("Resolve", size="5"),
            align_items="center",
            gap="2",
        ),
        
        rx.spacer(), # Pushes the next elements to the right
        
        # Right side: Tenant Badge & Navigation
        rx.hstack(
            rx.badge(
                rx.text(f"Tenant: {AppState.current_tenant}"),
                color_scheme="blue",
                variant="surface",
                size="2",
            ),
            rx.link(
                rx.button("Workspace", variant="soft", size="2"),
                href="/chat",
            ),
            rx.link(
                rx.button("Home", variant="outline", size="2"),
                href="/",
            ),
            gap="3",
            align_items="center",
        ),
        
        # Navbar styling
        width="100%",
        padding="1em",
        border_bottom="1px solid",
        border_color=rx.color("gray", 3),
        bg=rx.color("gray", 1),
        align_items="center",
    )