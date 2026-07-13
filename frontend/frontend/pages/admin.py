import reflex as rx
from frontend.state.admin_state import AdminState
from frontend.components.navbar import navbar

def admin_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            navbar(),
            rx.heading("Tenant Control Center", size="7", margin_y="1em"),
            rx.text("Manage your agent's behavior and knowledge context.", color="gray", margin_bottom="2em"),
            
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("System Prompts", value="prompts"),
                    rx.tabs.trigger("Knowledge Base (RAG)", value="knowledge"),
                    rx.tabs.trigger("Audit Queue", value="queue"), # New Queue Tab
                ),
                
                # PROMPT MANAGEMENT TAB
                rx.tabs.content(
                    rx.card(
                        rx.vstack(
                            rx.heading("Register New Prompt", size="4"),
                            rx.text("Define the system framework instructions for this tenant.", size="2", color="gray"),
                            
                            rx.input(
                                placeholder="Prompt Key (e.g., 'default_customer_service')",
                                value=AdminState.prompt_key,
                                on_change=AdminState.set_prompt_key,
                                width="100%"
                            ),
                            rx.text_area(
                                placeholder="You are a helpful AI assistant...",
                                value=AdminState.prompt_text,
                                on_change=AdminState.set_prompt_text,
                                height="200px",
                                width="100%"
                            ),
                            rx.button(
                                "Register Prompt Version",
                                on_click=AdminState.register_prompt,
                                loading=AdminState.is_submitting_prompt,
                                width="100%"
                            ),
                            rx.text(AdminState.prompt_status, color="blue", size="2"),
                            gap="3",
                        ),
                        width="100%",
                        margin_top="1em"
                    ),
                    value="prompts",
                ),
                
                # KNOWLEDGE INGESTION TAB
                rx.tabs.content(
                    rx.card(
                        rx.vstack(
                            rx.heading("Ingest Knowledge Document", size="4"),
                            rx.text("Upload raw text to be converted into 1536-dimensional vectors.", size="2", color="gray"),
                            
                            rx.input(
                                placeholder="Document Title (e.g., 'Return Policy 2026')",
                                value=AdminState.doc_title,
                                on_change=AdminState.set_doc_title,
                                width="100%"
                            ),
                            rx.text_area(
                                placeholder="Paste raw unstructured documentation here...",
                                value=AdminState.raw_content,
                                on_change=AdminState.set_raw_content,
                                height="200px",
                                width="100%"
                            ),
                            rx.button(
                                "Vectorize & Ingest",
                                on_click=AdminState.ingest_knowledge,
                                loading=AdminState.is_ingesting,
                                width="100%",
                                color_scheme="green"
                            ),
                            rx.text(AdminState.knowledge_status, color="green", size="2"),
                            gap="3",
                        ),
                        width="100%",
                        margin_top="1em"
                    ),
                    value="knowledge",
                ),

                # AUDIT QUEUE TAB
                rx.tabs.content(
                    rx.card(
                        rx.vstack(
                            rx.heading("Manual Task Audit", size="4"),
                            rx.text("Paste a paused Task ID to review its LangGraph state and approve execution.", size="2", color="gray"),
                            
                            # Search Bar
                            rx.hstack(
                                rx.input(
                                    placeholder="Enter Task ID (e.g., 8fdcd132...)",
                                    value=AdminState.lookup_task_id,
                                    on_change=AdminState.set_lookup_task_id,
                                    width="100%"
                                ),
                                rx.button(
                                    "Fetch State",
                                    on_click=AdminState.view_task_state,
                                    loading=AdminState.is_loading_state,
                                ),
                                width="100%"
                            ),
                            
                            # State Display
                            rx.box(
                                rx.code_block(AdminState.selected_task_memory, language="json", width="100%"),
                                height="250px",
                                width="100%",
                                overflow_y="auto",
                                border="1px solid #333",
                                border_radius="md",
                                padding="1em",
                                margin_y="1em"
                            ),
                            
                            # Approval Button
                            rx.cond(
                                AdminState.selected_task_id != "",
                                rx.button(
                                    "Approve & Resume Workflow",
                                    color_scheme="green",
                                    width="100%",
                                    size="3",
                                    loading=AdminState.is_resuming,
                                    on_click=AdminState.approve_and_resume
                                )
                            ),
                            width="100%",
                            align_items="flex-start"
                        ),
                        width="100%",
                        margin_top="1em"
                    ),
                    value="queue",
                ),

                default_value="prompts",
                width="100%",
            ),
            width="100%",
            max_width="900px", # Wide, slightly to accommodate the split screen
            margin="auto",
        )
    )