import reflex as rx

def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Welcome to Resolve AI", size="8"),
            rx.text("Multi-Tenant Agentic Orchestration Layer.", size="4"),
            rx.link(
                rx.button("Enter Workspace", size="3", margin_top="2em"),
                href="/chat",
                is_external=False,
            ),
            align_items="center",
            justify_content="center",
            height="100vh",
        )
    )