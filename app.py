import os
import gradio as gr
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langsmith import Client
import asyncio
import logging

LANGGRAPH_DEPLOYMENT = "https://le-chat-bottes-08847786c41355da87302fa1e0f41f4a.us.langgraph.app/"

client = get_client(url=LANGGRAPH_DEPLOYMENT)
langsmith_client = Client()

async def log_feedback(run_id, score, comment=""):
    """Log feedback to LangSmith"""
    try:
        langsmith_client.create_feedback(
            run_id=run_id,
            key="user_feedback",
            score=score,
            comment=comment
        )
        logging.info(f"Successfully logged feedback for run_id: {run_id} with score: {score}")
        return True
    except Exception as e:
        logging.error(f"Error logging feedback for run_id: {run_id}: {e}")
        return False

async def respond(message, history, thread_state):
    assistants = await client.assistants.search(
        graph_id="retrieval_graph", metadata={"created_by": "system"}
    )
    
    if not thread_state:
        thread = await client.threads.create()
        thread_state = thread["thread_id"]
    
    response = ""
    run_id = None
    
    async for chunk in client.runs.stream(
        thread_id=thread_state,
        assistant_id=assistants[0]["assistant_id"],
        input={"messages": message},
        stream_mode="events",
    ):
        if chunk.event == "events":
            if chunk.data["event"] == "on_chat_model_stream":
                if run_id is None and "run_id" in chunk.data:
                    run_id = chunk.data["run_id"]
                token = chunk.data["data"]["chunk"]["content"]
                response += token
                yield history + [{"role": "user", "content": message}, 
                               {"role": "assistant", "content": response}], thread_state, run_id

def clear_conversation():
    return [], None

async def give_positive_feedback(run_id):
    if run_id is not None:
        await log_feedback(run_id, 1.0)
    else:
        logging.warning("Attempted to give positive feedback but run_id was None")

async def give_negative_feedback(run_id):
    if run_id is not None:
        await log_feedback(run_id, 0.0)
    else:
        logging.warning("Attempted to give negative feedback but run_id was None")

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
            type="messages"
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
            thumbs_up = gr.Button("👍")
            thumbs_down = gr.Button("👎")
        
        thread_state = gr.State()
        current_run_id = gr.State()

    txt.submit(
        respond,
        [txt, chatbot, thread_state],
        [chatbot, thread_state, current_run_id],
        api_name=False
    ).then(
        lambda: "",
        None,
        [txt]
    )
    
    submit_btn.click(
        respond,
        [txt, chatbot, thread_state],
        [chatbot, thread_state, current_run_id],
        api_name=False
    ).then(
        lambda: "",
        None,
        [txt]
    )

    thumbs_up.click(
        lambda x: asyncio.run(give_positive_feedback(x)),
        [current_run_id],
        None,
        api_name=False
    )
    
    thumbs_down.click(
        lambda x: asyncio.run(give_negative_feedback(x)),
        [current_run_id],
        None,
        api_name=False
    )

    clear_btn.click(
        clear_conversation,
        None,
        [chatbot, thread_state],
        api_name=False
    )

if __name__ == "__main__":
    demo.launch(share=True)
