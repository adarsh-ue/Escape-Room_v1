"""AI Escape Room - Version 1 (LLM as Game Master).

Run:  streamlit run app.py
"""
import streamlit as st

from config import ConfigError, load_config
from llm import GameMaster, LLMError
from prompts import build_system_prompt, load_room

st.set_page_config(page_title="AI Escape Room", page_icon="🗝️", layout="centered")

room = load_room()

try:
    API_KEY, MODEL = load_config()
except ConfigError as e:
    st.title("🗝️ AI Escape Room")
    st.error(str(e))
    st.stop()


def reset_game():
    st.session_state.history = []          # what is sent to Gemini (role/text)
    st.session_state.display = [           # what is shown in the chat
        {"role": "assistant", "text": room["intro"]}
    ]
    st.session_state.inventory = []
    st.session_state.solved = []
    st.session_state.escaped = False
    st.session_state.turns = 0


if "history" not in st.session_state:
    reset_game()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("🎒 Inventory")
    if st.session_state.inventory:
        for item in st.session_state.inventory:
            st.write(f"- {item}")
    else:
        st.caption("Empty")

    st.header("🧩 Puzzles solved")
    st.write(f"{len(st.session_state.solved)} / {len(room['puzzles'])}")
    st.caption(f"Turns: {st.session_state.turns}  ·  Model: {MODEL}")

    st.divider()
    if st.button("🔄 Restart game", use_container_width=True):
        reset_game()
        st.rerun()

# ---------- Main ----------
st.title(f"🗝️ {room['title']}")
with st.expander("How to play", expanded=st.session_state.turns == 0):
    for line in room["instructions"]:
        st.markdown(f"- {line}")

for msg in st.session_state.display:
    avatar = "🧙" if msg["role"] == "assistant" else "🧑"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["text"])

if st.session_state.escaped:
    st.success(f"🎉 You escaped in {st.session_state.turns} turns! Press Restart to play again.")
    st.stop()

player_input = st.chat_input("What do you do?")
if player_input:
    st.session_state.display.append({"role": "user", "text": player_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(player_input)

    pending = st.session_state.history + [{"role": "user", "text": player_input}]
    with st.chat_message("assistant", avatar="🧙"):
        with st.spinner("The Game Master is thinking..."):
            try:
                gm = GameMaster(API_KEY, MODEL, build_system_prompt(room))
                reply = gm.respond(pending)
            except LLMError as e:
                st.error(str(e))
                st.session_state.display.pop()  # let the player retry the same turn
                st.stop()
        st.markdown(reply.narration)

    # Model turn is stored as full JSON so Gemini remembers inventory/progress.
    st.session_state.history = pending + [{"role": "model", "text": reply.model_dump_json()}]
    st.session_state.display.append({"role": "assistant", "text": reply.narration})
    st.session_state.inventory = reply.inventory
    st.session_state.solved = reply.solved
    st.session_state.turns += 1
    if reply.escaped:
        st.session_state.escaped = True
        st.balloons()
    st.rerun()
