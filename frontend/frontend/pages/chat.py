import reflex as rx
from frontend.state.chat_state import ChatState
from frontend.components.navbar import navbar
from frontend.components.loading import agent_thinking_indicator

def message_bubble(message: dict) -> rx.Component:
    """Renders a single message bubble."""
    is_user = message["role"] == "user"
    
    return rx.box(
        rx.text(message["content"], padding="1em", color="white"),
        bg=rx.cond(is_user, rx.color("blue", 9), rx.color("gray", 9)),
        border_radius="lg",
        margin_y="0.5em",
        align_self=rx.cond(is_user, "flex-end", "flex-start"),
        max_width="80%",
    )

def chat_page() -> rx.Component:
    """The main chat interface."""
    return rx.container(
        rx.vstack(
            navbar(),
            rx.heading("Resolve Agentic Workspace", size="7", margin_bottom="2em"),
            
            # The Chat Display Area
            rx.box(
                rx.vstack(
                    rx.foreach(ChatState.chat_history, message_bubble),
                    rx.cond(
                        ChatState.is_processing,
                        agent_thinking_indicator() 
                    ),
                    
                    # NEW CONDITIONAL BUTTON
                    # rx.cond(
                    #     ChatState.is_paused,
                    #     rx.button(
                    #         "Approve & Resume Workflow",
                    #         color_scheme="green",
                    #         size="3",
                    #         margin_top="1em",
                    #         on_click=ChatState.resume_workflow
                    #     )
                    # ),
                    
                    width="100%",
                ),
                height="60vh",
                overflow_y="auto",
                border="1px solid #333",
                border_radius="md",
                padding="1em",
                margin_bottom="1em",
                width="100%",
            ),
            
            # The Input Area
            rx.hstack(
                rx.input(
                    placeholder="Type your query here...",
                    value=ChatState.current_input,
                    on_change=ChatState.set_current_input,
                    on_key_down=ChatState.handle_key_down, 
                    width="100%",
                    disabled=ChatState.is_processing,
                ),
                rx.button(
                    "Send", 
                    id="send-btn",
                    on_click=ChatState.send_message,
                    disabled=ChatState.is_processing,
                ),
                width="100%",
            ),
            
            # Diagnostic Info (Optional, good for debugging)
            rx.text(
                f"Connected to: {ChatState.api_url} | Tenant: {ChatState.current_tenant}", 
                size="1", 
                color="gray", 
                margin_top="2em"
            ),
            
            align_items="center",
            width="100%",
            max_width="800px",
            margin="auto",
            padding_top="4em",
        )
    )