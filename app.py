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

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Historique des conversations")
            chat_list = gr.Chatbot(height=700, show_label=False)
        
        with gr.Column(scale=3):
            gr.Markdown("### Assistant R&D Agricole")
            chatbot = gr.Chatbot(
                height=600,
                avatar_images=(
                    "https://em-content.zobj.net/source/microsoft-teams/363/person_1f9d1.png",  # Person emoji
                    "https://em-content.zobj.net/source/microsoft-teams/363/robot_1f916.png"  # Robot emoji
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
            
            thread_state = gr.State(value=None)

    def clear_conversation():
        return [], None

    txt.submit(
        respond,
        [txt, chatbot, thread_state],
        [chatbot, thread_state],
        api_name=False
    ).then(
        lambda: "",  # Clear the textbox after submission
        None,
        [txt]
    )
    
    submit_btn.click(
        respond,
        [txt, chatbot, thread_state],
        [chatbot, thread_state],
        api_name=False
    ).then(
        lambda: "",  # Clear the textbox after submission
        None,
        [txt]
    )

    clear_btn.click(
        clear_conversation,
        None,
        [chatbot, thread_state],
        api_name=False
    )

    gr.Markdown("""
    <style>
        .gradio-container {
            background-color: #f5f7f5;
        }
        .contain {
            max-width: 1200px !important;
            margin: auto;
        }
        .message {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        .user-message {
            background-color: #e6f3ff;
        }
        .bot-message {
            background-color: #f5f5f5;
        }
        footer {display: none !important}
    </style>
    """)

if __name__ == "__main__":
    demo.launch()
