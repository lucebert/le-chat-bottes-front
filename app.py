import os
import gradio as gr
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

LANGGRAPH_DEPLOYMENT = "https://chambre-agricole-chatbot-686407044d7f59d29a1e494685864177.us.langgraph.app/"

client = get_client(url=LANGGRAPH_DEPLOYMENT)

async def respond(message, history, thread_state):
    assistants = await client.assistants.search(
        graph_id="retrieval_graph", metadata={"created_by": "system"}
    )
    
    if not thread_state:
        thread = await client.threads.create()
        thread_state = thread["thread_id"]
    
    response = ""
    
    async for chunk in client.runs.stream(
        thread_id=thread_state,
        assistant_id=assistants[0]["assistant_id"],
        input={"messages": message},
        stream_mode="events",
    ):
        if chunk.event == "events":
            if chunk.data["event"] == "on_chat_model_stream":
                token = chunk.data["data"]["chunk"]["content"]
                response += token
                yield history + [(message, response)], thread_state

def clear_conversation():
    return [], None

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    with gr.Column(scale=3):
        gr.Markdown("### Assistant R&D Agricole")
        chatbot = gr.Chatbot(
            height=600,
            avatar_images=(
                "https://em-content.zobj.net/source/microsoft-teams/337/farmer_1f9d1-200d-1f33e.png",
                "https://em-content.zobj.net/source/microsoft-teams/363/robot_1f916.png"
            ),
            container=True,
            show_label=False,
        )
        with gr.Row():
            txt = gr.Textbox(
                placeholder="Posez votre question ici concernant les données R&D agricoles...",
                show_label=False,
                container=False,
                scale=9,
            )
            submit_btn = gr.Button("Envoyer", scale=1)
        
        with gr.Row():
            clear_btn = gr.Button("Effacer la conversation")
        
        thread_state = gr.State() 

    txt.submit(
        respond,
        [txt, chatbot, thread_state],
        [chatbot, thread_state],
        api_name=False
    ).then(
        lambda: "",
        None,
        [txt]
    )
    
    submit_btn.click(
        respond,
        [txt, chatbot, thread_state],
        [chatbot, thread_state],
        api_name=False
    ).then(
        lambda: "",
        None,
        [txt]
    )

    clear_btn.click(
        clear_conversation,
        None,
        [chatbot, thread_state],
        api_name=False
    )

if __name__ == "__main__":
    demo.launch(share=True)
