import os
import gradio as gr
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

LANGGRAPH_DEPLOYMENT = "https://chambre-agricole-chatbot-686407044d7f59d29a1e494685864177.us.langgraph.app/"

client = get_client(url=LANGGRAPH_DEPLOYMENT)

async def respond(
    message: str,
    *,
    history: list[tuple[str, str]] = None,
    system_message: str = "You are a friendly Chatbot.",
):
    thread = await client.threads.create()
    
    await client.messages.create(
        thread_id=thread.id,
        content=message,
        role="user"
    )
    
    assistants = await client.assistants.search(
        graph_id="retrieval_graph", metadata={"created_by": "system"}
    )
    
    response = ""
    
    async for chunk in client.runs.stream(
        thread_id=thread.id,
        assistant_id=assistants[0]["assistant_id"],
        input={},
        stream_mode="events",
    ):
        if chunk.event == "events":
            if chunk.data["event"] == "on_chat_model_stream":
                token = chunk.data["data"]["chunk"]["content"]
                response += token
                yield response

demo = gr.ChatInterface(
    respond,
    additional_inputs=[
        gr.Textbox(value="You are a friendly Chatbot.", label="System message"),
    ],
)

if __name__ == "__main__":
    demo.launch()
