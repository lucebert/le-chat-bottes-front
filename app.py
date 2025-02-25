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
                yield [
                    *history,
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": response}
                ], thread_state, run_id

def clear_conversation():
    return [], None, gr.update(visible=False)

with gr.Blocks(theme=gr.themes.Soft(), css="""
h1 {
    text-align: center;
}
.gradio-container {
    max-width: 800px !important;
}
.feedback-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px;
    margin-top: 12px;
}
.feedback-buttons {
    gap: 8px;
}
.selected-thumb {
    background: #e0e0e0 !important;
    border-color: #4CAF50 !important;
}
.examples .example {
    background: #f0f0f0;
    padding: 10px;
    margin: 5px;
    border-radius: 5px;
    cursor: pointer;
}
.examples .example:hover {
    background: #e0e0e0;
}
""") as demo:
    with gr.Column():
        with gr.Row():
            with gr.Column(scale=9):
                gr.Markdown("# Le Chat Bottes 👢😺👢")
        
        chatbot = gr.Chatbot(
            height=640,
            avatar_images=(
                "https://em-content.zobj.net/source/microsoft-teams/337/farmer_1f9d1-200d-1f33e.png",
                "https://em-content.zobj.net/source/microsoft-teams/363/robot_1f916.png"
            ),
            show_label=False,
            bubble_full_width=False,
            container=False,
            type="messages"
        )

        with gr.Column(visible=False) as feedback_card:
            with gr.Row():
                thumbs_up = gr.Button("👍", elem_classes="feedback-btn")
                thumbs_down = gr.Button("👎", elem_classes="feedback-btn")
            with gr.Row(visible=False) as feedback_input_row:
                feedback_comment = gr.Textbox(
                    placeholder="Commentaire (optionnel)",
                    show_label=False,
                    lines=2,
                    max_lines=3
                )
                feedback_send_btn = gr.Button("Envoyer", size="sm")
            
            thank_you_message = gr.HTML(
                "<div style='color: #4CAF50; margin-top: 8px; display: none'>Merci pour votre retour !</div>",
                visible=False
            )
        
        with gr.Row():
            txt = gr.Textbox(
                placeholder="Posez votre question ici...",
                show_label=False,
                container=False,
                scale=7,
                autofocus=True,
                max_lines=3,
            )
            submit_btn = gr.Button("Envoyer", scale=1, size="sm")
            clear_btn = gr.Button("Effacer", scale=1, size="sm")
        
        with gr.Row():
            gr.Examples(
                examples=[
                    "Comment stocker l'eau de pluie sur une exploitation agricole ?",
                    "Quelles rotations culturales favorisent l'adaptation climatique ?",
                    "Comment réduire l'impact du gel printanier sur les vignes ?"
                ],
                inputs=txt,
                label=""
            )
        

        feedback_alert = gr.HTML(visible=False)

        thread_state = gr.State()
        current_run_id = gr.State()
        selected_thumb = gr.State()

    txt.submit(
        respond,
        [txt, chatbot, thread_state],
        [chatbot, thread_state, current_run_id],
        api_name=False
    ).then(
        lambda: ("", gr.update(visible=True), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)),
        None,
        [txt, feedback_card, thank_you_message, thumbs_up, thumbs_down]
    )
    
    submit_btn.click(
        respond,
        [txt, chatbot, thread_state],
        [chatbot, thread_state, current_run_id],
        api_name=False
    ).then(
        lambda: ("", gr.update(visible=True), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)),
        None,
        [txt, feedback_card, thank_you_message, thumbs_up, thumbs_down]
    )

    def show_feedback_input(thumb):
        return (
            gr.update(visible=True),  # feedback_input_row
            thumb,                    # selected_thumb
            gr.update(visible=False), # thumbs_up
            gr.update(visible=False)  # thumbs_down
        )

    thumbs_up.click(
        show_feedback_input,
        inputs=[gr.Number(1, visible=False)],
        outputs=[feedback_input_row, selected_thumb, thumbs_up, thumbs_down]
    )
    
    thumbs_down.click(
        show_feedback_input,
        inputs=[gr.Number(0, visible=False)],
        outputs=[feedback_input_row, selected_thumb, thumbs_up, thumbs_down]
    )

    def submit_feedback(run_id, score, comment):
        asyncio.run(log_feedback(run_id, score, comment))
        return (
            gr.update(visible=True),  # thank_you_message
            gr.update(value=""),      # feedback_comment
            gr.update(visible=False), # feedback_input_row
            gr.update(visible=False), # thumbs_up
            gr.update(visible=False)  # thumbs_down
        )

    feedback_send_btn.click(
        submit_feedback,
        [current_run_id, selected_thumb, feedback_comment],
        [thank_you_message, feedback_comment, feedback_input_row, thumbs_up, thumbs_down]
    )
    
    feedback_comment.submit(
        submit_feedback,
        [current_run_id, selected_thumb, feedback_comment],
        [thank_you_message, feedback_comment, feedback_input_row, thumbs_up, thumbs_down]
    )

    clear_btn.click(
        clear_conversation,
        None,
        [chatbot, thread_state, feedback_card, thank_you_message],
        api_name=False
    )

if __name__ == "__main__":
    demo.launch(share=True)
