import csv
import os
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from groq import Groq

# =========================
# CONFIG
# =========================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RESTAURANT_NAME = "Bella Roma"
RESTAURANT_TAGLINE = "Authentic Italian Kitchen"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
BOOKINGS_FILE = "bookings.csv"
BOOKING_FIELDS = ["Name", "Date", "Time", "Guests", "Notes", "Booked At"]

# =========================
# GROQ CLIENT
# =========================
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
You are Sofia, a warm AI assistant for Bella Roma, an Italian restaurant.

STRICT RULES:
- You only talk about Bella Roma.
- Never behave like a general AI assistant.
- Keep replies short, warm, and helpful.
- Plain text only. No markdown tables.
- Use short bullet lists when useful.

MENU AND SPICE DISPLAY:
When the user asks for the menu, present sections clearly and include spice markers where relevant:
- No spice marker = not spicy
- 🌶 = mild
- 🌶🌶 = medium
- 🌶🌶🌶 = very spicy

Use these items:
Appetizers:
- Bruschetta — $9
- Calamari Fritti — $13 🌶
- Burrata & Tomato — $14

Pasta:
- Spaghetti Carbonara — $18
- Penne Arrabbiata — $16 🌶🌶🌶
- Truffle Tagliatelle — $24

Pizza:
- Margherita — $15 (Vegetarian)
- Prosciutto e Rucola — $19
- Quattro Formaggi — $20

Mains:
- Chicken Parmigiana — $22
- Grilled Sea Bass — $28
- Eggplant Parmigiana — $17 (Vegetarian) 🌶

Desserts:
- Tiramisu — $8
- Panna Cotta — $7
- Gelato — $6

Drinks:
- Espresso — $3
- House Wine — $10
- San Pellegrino — $4
- Limoncello — $7

SMART RECOMMENDATIONS:
- Spicy → Penne Arrabbiata
- Vegetarian → Eggplant Parmigiana, Margherita Pizza
- Light → Grilled Sea Bass, Burrata & Tomato
- Rich → Truffle Tagliatelle, Quattro Formaggi, Tiramisu

RESERVATIONS:
If the user wants to book a table, collect:
1. Name
2. Date
3. Time
4. Guests
5. Notes

Once you have all five, output exactly this on its own line:
BOOKING_CONFIRMED: name=... | date=... | time=... | guests=... | notes=...

Always end with one helpful follow-up question unless a booking is already confirmed.
"""

MENU_TEXT = """Here is our menu:

Appetizers
- Bruschetta — $9
- Calamari Fritti — $13 🌶
- Burrata & Tomato — $14

Pasta
- Spaghetti Carbonara — $18
- Penne Arrabbiata — $16 🌶🌶🌶
- Truffle Tagliatelle — $24

Pizza
- Margherita — $15 (Vegetarian)
- Prosciutto e Rucola — $19
- Quattro Formaggi — $20

Mains
- Chicken Parmigiana — $22
- Grilled Sea Bass — $28
- Eggplant Parmigiana — $17 (Vegetarian) 🌶

Desserts
- Tiramisu — $8
- Panna Cotta — $7
- Gelato — $6

Drinks
- Espresso — $3
- House Wine — $10
- San Pellegrino — $4
- Limoncello — $7

Spice guide:
- 🌶 Mild
- 🌶🌶 Medium
- 🌶🌶🌶 Very spicy

Would you like a vegetarian, spicy, or light recommendation?"""

VEG_TEXT = """Our vegetarian options are:

- Margherita Pizza — $15
- Eggplant Parmigiana — $17 🌶
- Penne Arrabbiata — $16 🌶🌶🌶
- Burrata & Tomato — $14

If you want something classic, go for the Margherita.
If you want something bold, Penne Arrabbiata is the spicy choice.

Would you like me to recommend the best vegetarian main or pasta?"""

SPICY_TEXT = """If you enjoy spicy dishes, I recommend:

- Penne Arrabbiata — $16 🌶🌶🌶
- Eggplant Parmigiana — $17 🌶
- Calamari Fritti — $13 🌶

Best spicy pick:
Penne Arrabbiata, because it has a bold tomato-chili kick and is one of our most flavorful pasta dishes.

Would you like me to suggest a drink pairing too?"""

RESERVE_TEXT = """Of course. I can help with a reservation.

Please send me these details:
- Name
- Date
- Time
- Number of guests
- Any special requests

What name should I book the table under?"""


# =========================
# HELPERS
# =========================
def save_booking(name, date, time, guests, notes=""):
    file_exists = os.path.exists(BOOKINGS_FILE)
    with open(BOOKINGS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(BOOKING_FIELDS)
        writer.writerow(
            [name, date, time, guests, notes, datetime.now().strftime("%Y-%m-%d %H:%M")]
        )


def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        return []
    with open(BOOKINGS_FILE, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def delete_booking(index):
    bookings = load_bookings()
    if index < 0 or index >= len(bookings):
        return False
    bookings.pop(index)
    with open(BOOKINGS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BOOKING_FIELDS)
        writer.writeheader()
        writer.writerows(bookings)
    return True


def check_and_save_booking(reply):
    if "BOOKING_CONFIRMED:" not in reply:
        return reply, None

    try:
        raw = reply.split("BOOKING_CONFIRMED:", 1)[1].strip().split("\n", 1)[0]
        parts = {}

        for item in raw.split("|"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                parts[key.strip().lower()] = value.strip()

        required = ["name", "date", "time", "guests", "notes"]
        if not all(field in parts for field in required):
            return reply, None

        save_booking(
            parts["name"],
            parts["date"],
            parts["time"],
            parts["guests"],
            parts["notes"],
        )
        clean_reply = reply.split("BOOKING_CONFIRMED:", 1)[0].strip()
        return clean_reply, parts
    except Exception:
        return reply, None


def get_local_reply(text):
    normalized = text.strip().lower()

    if normalized in {
        "show me the menu",
        "menu",
        "show me full menu",
        "show me the full menu with prices",
    }:
        return MENU_TEXT

    if normalized in {
        "vegetarian options",
        "what are your vegetarian options?",
        "veg",
    }:
        return VEG_TEXT

    if normalized in {
        "recommend something spicy",
        "i love spicy food, what do you recommend?",
        "spicy",
    }:
        return SPICY_TEXT

    if normalized in {
        "i want to book a table",
        "i'd like to make a reservation",
        "reserve",
        "reservation",
    }:
        return RESERVE_TEXT

    return None


def scroll_to_bottom():
    components.html(
        """
        <script>
            const parentDoc = window.parent.document;
            const chatInput = parentDoc.querySelector('[data-testid="stChatInput"]');
            if (chatInput) {
                chatInput.scrollIntoView({ behavior: "smooth", block: "end" });
            }
            window.parent.scrollTo({
                top: parentDoc.body.scrollHeight,
                behavior: "smooth"
            });
        </script>
        """,
        height=0,
    )


# =========================
# PAGE SETUP
# =========================
st.set_page_config(
    page_title=f"{RESTAURANT_NAME} | AI Assistant",
    page_icon="🍝",
    layout="wide",
)

# =========================
# STYLING
# =========================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(255,153,0,0.10), transparent 30%),
        radial-gradient(circle at top right, rgba(255,255,255,0.05), transparent 25%),
        linear-gradient(135deg, #0b0f1a 0%, #121826 45%, #0f172a 100%);
    color: #f5f7fb;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a2031 0%, #222738 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1280px;
}

.hero-card {
    background: linear-gradient(135deg, rgba(10,14,24,0.95), rgba(20,27,42,0.92));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 2rem 2rem 1.6rem 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.28);
    margin-bottom: 1.25rem;
}

.hero-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
    line-height: 1.1;
}

.hero-tagline {
    font-size: 1.05rem;
    color: #f2d7a6;
    margin-top: 0.35rem;
    margin-bottom: 0.7rem;
}

.hero-sub {
    color: #b7c1d3;
    font-size: 1rem;
    margin-top: 0.6rem;
}

.info-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 1.2rem;
}

.pill {
    display: inline-block;
    background: rgba(255, 166, 0, 0.10);
    border: 1px solid rgba(255, 179, 71, 0.25);
    color: #ffd38a;
    padding: 8px 14px;
    border-radius: 999px;
    font-size: 0.85rem;
}

.section-label {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 1.6px;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 0.4rem 0 0.7rem 0;
}

.stButton > button {
    width: 100% !important;
    min-height: 54px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    background: rgba(17, 24, 39, 0.75) !important;
    color: #f8fafc !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}

.stButton > button:hover {
    border-color: rgba(255, 183, 77, 0.85) !important;
    background: rgba(29, 41, 61, 0.95) !important;
    color: #ffe3b0 !important;
}

.quick-grid {
    margin-top: 0.2rem;
    margin-bottom: 0.7rem;
}

.chat-tip {
    background: rgba(15, 23, 42, 0.76);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 0.9rem 1rem;
    color: #cbd5e1;
    margin-bottom: 0.9rem;
}

.booking-success {
    background: linear-gradient(135deg, rgba(10,60,35,0.92), rgba(16,88,50,0.86));
    border: 1px solid rgba(74, 222, 128, 0.35);
    border-radius: 16px;
    padding: 1rem 1.1rem;
    color: #dcfce7;
    margin-top: 0.7rem;
}

[data-testid="stChatMessage"] {
    background: rgba(15, 23, 42, 0.70);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 18px;
    padding: 0.35rem 0.55rem;
    margin-bottom: 0.7rem;
}

[data-testid="stChatInput"] {
    background: rgba(15,23,42,0.92);
}

hr {
    border-color: rgba(255,255,255,0.08);
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# SIDEBAR ADMIN
# =========================
with st.sidebar:
    st.markdown("## 🔐 Admin")
    st.caption("Restaurant staff only")

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        pwd = st.text_input("Password", type="password", placeholder="Enter admin password")
        if st.button("Login", use_container_width=True):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Wrong password")
    else:
        st.success("Logged in as Admin")
        if st.button("Logout", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.markdown("---")
        bookings = load_bookings()
        st.markdown(f"**Total reservations:** {len(bookings)}")

        if bookings:
            for i, booking in enumerate(bookings):
                title = f"{booking['Name']} | {booking['Date']} {booking['Time']} | {booking['Guests']} guests"
                with st.expander(title):
                    st.write(f"Notes: {booking.get('Notes', '') or 'N/A'}")
                    st.write(f"Booked at: {booking.get('Booked At', '') or 'N/A'}")
                    if st.button("Delete reservation", key=f"delete_{i}", use_container_width=True):
                        if delete_booking(i):
                            st.rerun()
                        else:
                            st.error("Could not delete this booking.")

            if os.path.exists(BOOKINGS_FILE):
                with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
                    csv_data = f.read()
                st.download_button(
                    "Download bookings CSV",
                    data=csv_data,
                    file_name="bella_roma_bookings.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        else:
            st.info("No reservations yet.")

# =========================
# HEADER
# =========================
st.markdown(
    f"""
<div class="hero-card">
    <div class="hero-title">🍝 {RESTAURANT_NAME}</div>
    <div class="hero-tagline">{RESTAURANT_TAGLINE}</div>
    <div class="hero-sub">AI assistant for reservations, menu guidance, and tailored recommendations</div>
    <div class="info-pills">
        <span class="pill">📍 123 Main Street</span>
        <span class="pill">🕐 12pm to 11pm daily</span>
        <span class="pill">📞 +1-555-0199</span>
        <span class="pill">🚚 UberEats and DoorDash</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# SESSION STATE
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Ciao! I'm Sofia. I can show you the menu, help with a reservation, or recommend something based on your taste. What would you like today?",
        }
    ]

# =========================
# QUICK ACTIONS
# =========================
st.markdown('<div class="section-label">Quick actions</div>', unsafe_allow_html=True)
st.markdown('<div class="quick-grid">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4, gap="medium")
quick = None

with c1:
    if st.button("📋 Menu", use_container_width=True):
        quick = "Show me the menu"

with c2:
    if st.button("📅 Reserve", use_container_width=True):
        quick = "I want to book a table"

with c3:
    if st.button("🌶 Spicy", use_container_width=True):
        quick = "Recommend something spicy"

with c4:
    if st.button("🌿 Veg", use_container_width=True):
        quick = "Vegetarian options"

st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="chat-tip">Tip: Ask for the full menu, vegetarian dishes, a spicy recommendation, or a table booking.</div>',
    unsafe_allow_html=True,
)

# =========================
# CHAT HISTORY
# =========================
for msg in st.session_state.messages:
    avatar = "🍝" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])


# =========================
# MESSAGE FLOW
# =========================
def send_message(text):
    st.session_state.messages.append({"role": "user", "content": text})

    with st.chat_message("user", avatar="👤"):
        st.write(text)

    with st.chat_message("assistant", avatar="🍝"):
        local_reply = get_local_reply(text)

        if local_reply is not None:
            raw_reply = local_reply
            st.write(raw_reply)
        elif not client:
            raw_reply = (
                "The AI service is not configured yet. Please add GROQ_API_KEY in your local environment or deployment secrets."
            )
            st.warning(raw_reply)
        else:
            try:
                with st.spinner("Sofia is typing..."):
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages,
                        temperature=0.7,
                        max_tokens=600,
                    )
                    raw_reply = response.choices[0].message.content or "Sorry, I could not generate a reply right now."
                st.write(raw_reply)
            except Exception as e:
                raw_reply = f"Sorry, there was a problem contacting the AI service: {e}"
                st.error(raw_reply)

        clean_reply, booking_data = check_and_save_booking(raw_reply)

        if booking_data:
            st.markdown(
                f"""
<div class="booking-success">
✅ Reservation confirmed<br>
👤 {booking_data.get('name', '')} &nbsp;|&nbsp;
📅 {booking_data.get('date', '')} at {booking_data.get('time', '')} &nbsp;|&nbsp;
👥 {booking_data.get('guests', '')} guests
</div>
""",
                unsafe_allow_html=True,
            )

    stored_reply = clean_reply if booking_data else raw_reply
    st.session_state.messages.append({"role": "assistant", "content": stored_reply})


if quick:
    send_message(quick)
    scroll_to_bottom()
    st.rerun()

user_input = st.chat_input("Ask Sofia anything about Bella Roma...")
if user_input:
    send_message(user_input)
    scroll_to_bottom()
st.markdown("---")
st.caption("Bella Roma AI Assistant | Powered by Groq and Streamlit")
