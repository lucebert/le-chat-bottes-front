import os
import gradio as gr
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

LANGGRAPH_DEPLOYMENT = "https://chambre-agricole-chatbot-686407044d7f59d29a1e494685864177.us.langgraph.app/"

client = get_client(url=LANGGRAPH_DEPLOYMENT)

async def respond(
    message,
    history,
    system_message,
    thread_state
):
    assistants = await client.assistants.search(
        graph_id="retrieval_graph", metadata={"created_by": "system"}
    )
    
    # Only create new thread if one doesn't exist
    if not thread_state:
        thread = await client.threads.create()
        thread_state = thread["thread_id"]
    
    response = ""
    
    async for chunk in client.runs.stream(
        thread_id=thread_state,
        assistant_id=assistants[0]["assistant_id"],
        input={
            "messages": message
        },
        stream_mode="events",
    ):
        if chunk.event == "events":
            if chunk.data["event"] == "on_chat_model_stream":
                token = chunk.data["data"]["chunk"]["content"]
                response += token
                yield history + [(message, response)], thread_state

demo = gr.Interface(
    fn=respond,
    inputs=[
        gr.Textbox(
            placeholder="Posez votre question ici concernant les données R&D agricoles...",
            label="Votre question",
            lines=2,
        ),
        gr.Chatbot(
            height=600,
            avatar_images=("👨‍🌾", "🤖")
        ),
        gr.State(value=None),
    ],
    outputs=[
        gr.Chatbot(),
        gr.State(),
    ],
    title="Assistant R&D Agricole",
    description="""
    Bienvenue sur l'assistant de recherche R&D Agricole. 
    Je peux vous aider à :
    - Rechercher des données techniques
    - Trouver des résultats d'expérimentations
    - Accéder aux synthèses des études
    - Consulter les références disponibles
    """,
    theme=gr.themes.Soft(),
    css="""
        .gradio-container {background-color: #f5f7f5}
        .title {color: #2e5d1d}
        .description {color: #4a4a4a}
    """
)

if __name__ == "__main__":
    demo.launch()
