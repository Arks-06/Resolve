import httpx
import reflex as rx
from .base_state import AppState

class AdminState(AppState):
    """Manages system prompts and RAG knowledge ingestion for the current tenant."""
    
    prompt_key: str = ""
    prompt_text: str = ""
    prompt_status: str = ""
    is_submitting_prompt: bool = False
    
    lookup_task_id: str = ""
    selected_task_id: str = ""
    selected_task_memory: str = "Enter a Task ID above to view the agent's pending action."
    is_resuming: bool = False
    is_loading_state: bool = False

    def set_prompt_key(self, text: str):
        self.prompt_key = text

    def set_selected_task_id(self, task_id: str):
        self.selected_task_id = task_id
        
    def set_prompt_text(self, text: str):
        self.prompt_text = text
        
    def set_doc_title(self, text: str):
        self.doc_title = text
        
    def set_raw_content(self, text: str):
        self.raw_content = text

    def set_lookup_task_id(self, text: str):
        self.lookup_task_id = text

    async def view_task_state(self):
        """Hits your existing /state endpoint to read LangGraph's memory."""
        if not self.lookup_task_id:
            self.selected_task_memory = "Please enter a Task ID."
            return

        self.is_loading_state = True
        self.selected_task_id = self.lookup_task_id
        self.selected_task_memory = "Loading agent memory..."
        yield
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.api_url}/api/v1/chat/state/{self.selected_task_id}")
                if response.status_code == 200:
                    data = response.json()
                    self.selected_task_memory = str(data.get("state", "No state found."))
                else:
                    self.selected_task_memory = f"Error: Task not found or not paused ({response.status_code})."
            except Exception as e:
                self.selected_task_memory = f"Connection Error: {e}"
                
        self.is_loading_state = False
        yield

    async def approve_and_resume(self):
        """The actual Admin Approval button logic."""
        if not self.selected_task_id:
            return
            
        self.is_resuming = True
        yield
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/api/v1/chat/resume/{self.selected_task_id}?tenant_id={self.current_tenant}"
                )
                if response.status_code == 200:
                    self.selected_task_memory = "✅ Task approved and resumed. The customer will now receive the response."
                    self.selected_task_id = ""
                    self.lookup_task_id = ""
                else:
                    self.selected_task_memory = f"Failed to resume: {response.text}"
            except Exception as e:
                self.selected_task_memory = f"Error: {e}"
                
        self.is_resuming = False
        yield

    async def register_prompt(self):
        if not self.prompt_key or not self.prompt_text:
            self.prompt_status = "Please fill out both fields."
            return
            
        self.is_submitting_prompt = True
        self.prompt_status = "Registering..."
        yield
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/api/v1/prompts/{self.current_tenant}",
                    json={"prompt_key": self.prompt_key, "prompt_text": self.prompt_text}
                )
                if response.status_code == 201:
                    self.prompt_status = "Prompt registered successfully!"
                    self.prompt_key = ""
                    self.prompt_text = ""
                else:
                    self.prompt_status = f"Failed: {response.status_code}"
            except Exception as e:
                self.prompt_status = f"Error: {str(e)}"
        
        self.is_submitting_prompt = False
        yield

    # Knowledge Base Management
    doc_title: str = ""
    raw_content: str = ""
    knowledge_status: str = ""
    is_ingesting: bool = False

    async def ingest_knowledge(self):
        if not self.doc_title or not self.raw_content:
            self.knowledge_status = "Please fill out both fields."
            return
            
        self.is_ingesting = True
        self.knowledge_status = "Vectorizing and ingesting..."
        yield
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/api/v1/tenants/{self.current_tenant}/knowledge",
                    json={"document_title": self.doc_title, "raw_content": self.raw_content}
                )
                if response.status_code == 201:
                    self.knowledge_status = "Knowledge ingested successfully!"
                    self.doc_title = ""
                    self.raw_content = ""
                else:
                    self.knowledge_status = f"Failed: {response.status_code}"
            except Exception as e:
                self.knowledge_status = f"Error: {str(e)}"
                
        self.is_ingesting = False
        yield