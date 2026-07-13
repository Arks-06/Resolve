import reflex as rx
from .pages.index import index
from .pages.chat import chat_page
from .pages.admin import admin_page

app = rx.App()

# the pages
app.add_page(index, route="/")
app.add_page(chat_page, route="/chat")
app.add_page(admin_page, route="/admin")