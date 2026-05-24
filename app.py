from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
import os
import re
from dotenv import load_dotenv
import requests

load_dotenv()

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
if not HF_API_TOKEN:
    raise ValueError("HF_API_TOKEN not found in .env")

HF_MODEL_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2-1.5B-Instruct"

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

app = Flask(__name__)

LOGS_FILE = "chat_logs.json"


def load_logs():
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_log(user_message, bot_response):
    logs = load_logs()
    logs.append(
        {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "bot": bot_response,
        }
    )
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


conversation_memory = {
    "history": [],
    "last_response": "",
    "name": None,
    "last_intent": None,
    "last_subintent": None,
    "language": "mixed",
    "confirmed_timing": None,  # NEW: track confirmed demo timing
    "pending_followup": None,  # NEW: track what we're waiting for
    "team_size": None,
}



# AI ENHANCER — called AFTER pick_response() to make replies feel natural
def enhance_with_llm(base_response, user_input, intent, conversation_memory):
    """
    Takes a rule-based base_response and uses Hugging Face to expand /
    rewrite it conversationally. Returns enhanced text or falls back to
    base_response if LLM fails or produces garbage.
    """
    try:
        name = conversation_memory.get("name", "")
        lang = conversation_memory.get("language", "mixed")
        history_text = "\n".join(conversation_memory["history"][-4:])

        # Build a tight, focused system prompt
        system_hint = (
            "You are a friendly Hindi + Telugu multilingual AI assistant. "
            "You speak natural Hinglish mixed with simple Telugu words naturally. "
            "Your replies should feel casual, regional and conversational. "
            "Do NOT sound corporate or formal. "
            "Avoid heavy business English words. "
            "Use simple Telugu flavor words like: untundi, cheddam, kavala, avuthundi, andi, mee kosam. "
            "Keep replies warm, short and natural. "
            "Reply in 2-3 conversational lines maximum. "
            "Use only 1 emoji maximum. "
            "Do NOT sound like a customer support executive."
        )

        lang_instruction = {
            "hindi": "Reply primarily in Hindi (Devanagari + Roman Hinglish mix).",
            "telugu": "Reply in Hindi + Telugu mixed conversational style. Use Telugu words lightly and naturally.",
            "mixed": "Reply in natural Hinglish — casual Hindi + English mix.",
        }.get(lang, "Reply in natural Hinglish.")

        prompt = f"""<|im_start|>system
{system_hint}
{lang_instruction}
User name: {name if name else 'not known yet'}
Detected intent: {intent}
Recent conversation:
{history_text}
<|im_end|>
<|im_start|>user
Rewrite this draft reply to sound more conversational, warm and natural.
Keep the core meaning. Add a relevant follow-up question if missing.
Draft: "{base_response}"
Original user message: "{user_input}"
<|im_end|>
<|im_start|>assistant
"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 120,
                "temperature": 0.72,
                "top_p": 0.9,
                "repetition_penalty": 1.15,
                "return_full_text": False,
            },
        }

        response = requests.post(
            HF_MODEL_URL, headers=headers, json=payload, timeout=25
        )
        result = response.json()

        if isinstance(result, list) and result:
            generated = result[0].get("generated_text", "").strip()
            # Clean up common LLM artifacts
            generated = generated.replace("</s>", "").replace("<|im_end|>", "").strip()
            generated = re.sub(
                r"^(Assistant:|Bot:)\s*", "", generated, flags=re.IGNORECASE
            )

            # Sanity checks — if the LLM produces something useless, fall back
            if (
                len(generated) > 15
                and len(generated) < 600
                and generated.lower() != base_response.lower()
                and not generated.startswith("I am a language model")
                and not generated.startswith("As an AI")
            ):
                return generated

    except Exception as e:
        print("LLM ENHANCE ERROR:", e)

    return base_response  # safe fallback



# MAIN GENERATE FUNCTION — architecture preserved, logic improved
def generate_response(user_input, conversation_history=None):

    import random

    global conversation_memory

    
    # SAFETY MEMORY INIT
    
    for key, default in [
        ("history", []),
        ("last_response", ""),
        ("name", None),
        ("last_intent", None),
        ("language", "mixed"),
        ("confirmed_timing", None),
        ("pending_followup", None),
    ]:
        if key not in conversation_memory:
            conversation_memory[key] = default

    
    # INPUT CLEANING
    
    text = user_input.lower().strip()
    text = re.sub(r"\s+", " ", text)
    words = re.findall(r"\w+", text, re.UNICODE)

    conversation_memory["history"].append(user_input)
    if len(conversation_memory["history"]) > 12:
        conversation_memory["history"] = conversation_memory["history"][-12:]

    
    # RESPONSE PICKER — unchanged signature
    
    def pick_response(responses):
        last = conversation_memory["last_response"]
        available = [r for r in responses if r != last]
        if not available:
            available = responses
        response = random.choice(available)
        conversation_memory["last_response"] = response
        return response

    # some necessary followups
    def is_short_followup(text):
        short_patterns = [
            "haan",
            "yes",
            "ok",
            "okay",
            "hmm",
            "continue",
            "aur",
            "फिर",
            "again",
            "interested",
            "detail",
            "comparison",
            "compare",
            "send",
            "bhejo",
            "कर दो",
        ]

        # very short message
        if len(text.split()) <= 4:
            return True

        # continuation words
        if any(p in text for p in short_patterns):
            return True

        return False

    
    # KEYWORD HELPERS — now with semantic fallback aliases
    
    def contains_keyword(keywords):
        for keyword in keywords:
            if keyword.lower() in text:
                return True
        return False

    def semantic_match(primary_keywords, aliases):
        """
        Checks primary keywords first, then tries aliases for indirect intent.
        aliases = list of indirect phrases that still map to this intent.
        """
        if contains_keyword(primary_keywords):
            return True
        for alias in aliases:
            if alias.lower() in text:
                return True
        return False

    
    # MULTILINGUAL KEYWORD LISTS
    
    greetings = [
        "hello",
        "hi",
        "hey",
        "namaste",
        "namaskar",
        "good morning",
        "good evening",
        "हेलो",
        "ही",
        "हाय",
        "नमस्ते",
        "नमस्कार",
        "హలో",
        "హాయ్",
        "నమస్తే",
        "hello andi",
        "hi andi",
    ]

    help_keywords = [
        "help",
        "assist",
        "support",
        "madad",
        "sahayam",
        "guide",
        "explain",
        "मदद",
        "सहायता",
        "समझाओ",
        "హెల్ప్",
        "సహాయం",
        "cheppu",
        "explain cheyyi",
        "help kavali",
    ]

    demo_keywords = [
        "demo",
        "डेमो",
        "demonstration",
        "demo kavali",
        "demo chahiye",
        "software demo",
        "live demo",
        "show demo",
        "demo chupinchu",
        "dikhao",
        "dikha",
        "show karo",
        "provide karo",
        "arrange demo",
        "schedule demo",
        "book demo",
        "demo arrange",
        "demo cheyyi",
        "demo cheddam",
        "de do",
        "kavali",
        "chahiye",
        "book",
    ]

    product_keywords = [
        "product",
        "software",
        "app",
        "application",
        "solution",
        "feature",
        "crm",
        "automation",
        "ai tool",
        "tool",
        "प्रोडक्ट",
        "सॉफ्टवेयर",
        "फीचर",
        "product enti",
        "software enti",
        "feature kya",
        "details cheppu",
        "automation",
    ]

    pricing_keywords = [
        "price",
        "pricing",
        "cost",
        "rate",
        "fees",
        "plan",
        "plans",
        "pricing details",
        "pricing batao",
        "kitna",
        "kitne",
        "kitna cost",
        "price batao",
        "कीमत",
        "प्राइस",
        "धर",
        "ధర",
        "pricing kavala",
        "plan enti",
        "amount",
        "subscription",
        "monthly plan",
    ]

    thanks_keywords = [
        "thanks",
        "thank you",
        "thankyou",
        "thanks a lot",
        "thx",
        "thank you so much",
        "thanks bro",
        "thanks andi",
        "थैंक यू",
        "धन्यवाद",
        "शुक्रिया",
        "बहुत धन्यवाद",
        "ధన్యవాదాలు",
        "thanks anna",
        "thanks akka",
        "thank you andi",
    ]

    bye_keywords = [
        "bye",
        "goodbye",
        "see you",
        "take care",
        "alvida",
        "bye andi",
        "बाय",
        "फिर मिलेंगे",
        "टाटा",
        "వెళ్తాను",
        "bye anna",
        "bye akka",
    ]

    timing_morning = [
        "morning",
        "morning mein",
        "subah",
        "सुबह",
        "मॉर्निंग",
        "early morning",
        "udayam",
        "morning kavali",
        "morning better",
    ]

    contact_keywords = [
        "email",
        "mail",
        "gmail",
        "contact",
        "number",
        "phone",
        "mobile",
        "email id",
        "contact details",
        "ईमेल",
        "मेल",
        "नंबर",
        "मोबाइल",
        "कॉन्टैक्ट",
        "mail id",
        "phone number",
        "gmail id",
        "contact cheptha",
    ]

    timing_evening = [
        "evening",
        "evening mein",
        "sham",
        "शाम",
        "इवनिंग",
        "sanjhe",
        "night",
        "raat",
        "saayantram",
        "evening better",
        "night lo",
    ]

    timing_flexible = [
        "anytime",
        "flexible",
        "koi bhi",
        "any time",
        "doesnt matter",
        "kuch bhi",
        "whenever",
        "mee ishtam",
        "eppudaina",
        "timing flexible",
    ]

    
    

    # DETECT LANGUAGE STYLE from current message
    

    has_hindi = bool(re.search(r"[\u0900-\u097F]", user_input))

    has_telugu_script = bool(re.search(r"[\u0C00-\u0C7F]", user_input))

    # Telugu words written in English
    telugu_words = [
        "andi",
        "cheppu",
        "cheyyi",
        "cheddam",
        "kavali",
        "untundi",
        "avuthundi",
        "mee",
        "meeru",
        "bagundi",
        "baguntundi",
        "ela",
        "inka",
        "enti",
        "em",
        "matlad",
        "matladam",
        "avuna",
        "kadha",
        "parledu",
        "sare",
        "chala",
        "kosam",
        "pampandi",
    ]

    # Hindi/Hinglish words
    hinglish_words = [
        "karo",
        "chahiye",
        "batao",
        "hain",
        "hai",
        "mein",
        "nahi",
        "kya",
        "aur",
        "demo",
        "pricing",
        "madad",
    ]

    has_telugu_words = any(word in text for word in telugu_words)

    has_hinglish = any(word in text for word in hinglish_words)

    # FINAL LANGUAGE DETECTION
    if has_telugu_script or has_telugu_words:

        detected_lang = "telugu"

    elif has_hindi:

        detected_lang = "hindi"

    elif has_hinglish:

        detected_lang = "mixed"

    else:

        detected_lang = conversation_memory.get("language", "mixed")

        
    # NAME DETECTION
    

    name_patterns = [
        # English
        r"(?:my name is)\s+([a-zA-Z\u0900-\u097F\u0C00-\u0C7F]+)",
        r"(?:i am)\s+([a-zA-Z\u0900-\u097F\u0C00-\u0C7F]+)",
        r"(?:iam)\s+([a-zA-Z\u0900-\u097F\u0C00-\u0C7F]+)",
        # Hindi
        r"(?:mera naam)\s+([a-zA-Z\u0900-\u097F\u0C00-\u0C7F]+)",
        r"(?:मेरा नाम)\s+([^\s]+)",
        r"(?:माय नेम इस)\s+([^\s]+)",
        # Telugu transliteration
        r"(?:naa peru)\s+([^\s]+)",
        r"(?:na peru)\s+([^\s]+)",
        r"(?:naa per)\s+([^\s]+)",
        r"(?:na per)\s+([^\s]+)",
        # Telugu script
        r"(?:నా పేరు)\s+([^\s]+)",
    ]

    for pattern in name_patterns:

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            name = match.group(1).strip()

            name = re.sub(r"[^\w\u0900-\u097F\u0C00-\u0C7F]", "", name)

            conversation_memory["name"] = name

            base = pick_response(
                [
                    f"Namaste {name} ji 😊 Meeku demo kavala ya pricing details?",
                    f"Hello {name}! Ela help cheyyali andi? Demo or product info kavala?",
                    f"Welcome {name} 😊 Mee kosam demo arrange cheddama?",
                    f"Hi {name} 😊 Software details, pricing ya demo lo deni gurinchi telusukovali?",
                    f"{name} ji 😊 CRM, automation ya AI tools gurinchi explain cheyyala?",
                ]
            )

            return enhance_with_llm(base, user_input, "greeting_name", conversation_memory)

    
    # SMALL TALK
    
    how_are_you_patterns = [
        "how are you",
        "hows are you",
        "how r you",
        "हाउ आर यू",
        "कैसे हो",
        "कैसी हो",
        "kese ho",
        "kaise ho",
        "ela unnaru",
    ]

    if any(p in text for p in how_are_you_patterns):
        base = pick_response(
            [
                "Main bagunnanu, Meeru cheppandi, demo ya pricing kavala?",
                "All good, Meeku ela help cheyyali?",
                "Baagunnanu, Software demo arrange cheddama?",
                "Super, Mee requirement enti cheppandi.",
            ]
        )
        return enhance_with_llm(base, user_input, "small_talk", conversation_memory)

    if contains_keyword(["ready", "रेडी"]):
        base = pick_response(
            [
                "Ready andi, Demo arrange cheddama?",
                "Haan ji, Meeku em help kavali?",
                "Ready unna, Pricing ya demo details kavala?",
            ]
        )
        return enhance_with_llm(base, user_input, "small_talk", conversation_memory)

    if "samajh" in text or "समझ" in text:
        base = pick_response(
            [
                "Ardam ayyindi, Inka cheppandi.",
                "Haan ji samajh gaya, Meeku next em kavali?",
                "Okay, Continue cheyyandi.",
            ]
        )
        return enhance_with_llm(base, user_input, "small_talk", conversation_memory)

    if "kya kar sakte" in text or "क्या कर सकते" in text or "kya help" in text:
        base = pick_response(
            [
                "Main AI assistant ni, Demo arrange cheyyagalanu, pricing explain cheyyagalanu and software features chupisthanu.",
                "Software demo, pricing details and AI tools information anni available unnayi",
                "Mee kosam demo, automation tools and CRM details explain cheyyagalanu",
            ]
        )
        return enhance_with_llm(base, user_input, "capabilities", conversation_memory)

    
    # LANGUAGE PREFERENCE
    
    if any(w in text for w in ["hindi", "हिंदी"]):
        conversation_memory["language"] = "hindi"
        return "Zaroor ji! Ab main Hindi mein baat karunga. Kya chahiye aapko?"

    if any(w in text for w in ["telugu", "తెలుగు", "telgu"]):
        conversation_memory["language"] = "telugu"
        return "Sure! Ab se Telugu mix lo maatladtaanu. Ela help cheyali?"

    
    # TIMING CONFIRMATION — check BEFORE broad demo re-detection
    # so "evening mein kar do" doesn't re-trigger demo question loop
    
    if conversation_memory["last_intent"] == "demo":

        # Morning confirmed
        if contains_keyword(timing_morning):
            conversation_memory["confirmed_timing"] = "morning"
            conversation_memory["last_intent"] = "timing_confirmed"
            conversation_memory["pending_followup"] = "contact"
            base = pick_response(
                [
                    "Morning slot confirm ayyindi, Online demo kavala ya live session?",
                    "Perfect! Morning timing fix chesanu. Online lo continue cheddama?",
                    "Morning demo arrange chestanu, Google Meet ya office visit better aa?",
                ]
            )
            return enhance_with_llm(
                base, user_input, "timing_morning", conversation_memory
            )

        # Evening confirmed
        if contains_keyword(timing_evening):
            conversation_memory["confirmed_timing"] = "evening"
            conversation_memory["last_intent"] = "timing_confirmed"
            conversation_memory["pending_followup"] = "contact"
            base = pick_response(
                [
                    "Evening slot confirm ayyindi, Online demo kavala ya direct meeting?",
                    "Great, Evening demo arrange chestanu. Email ID share cheyyandi.",
                    "Perfect, Evening timing baguntundi. Online session continue cheddama?",
                ]
            )
            return enhance_with_llm(
                base, user_input, "timing_evening", conversation_memory
            )

    # Flexible
    if contains_keyword(timing_flexible):

        conversation_memory["confirmed_timing"] = "flexible"
        conversation_memory["pending_followup"] = "contact"

        base = pick_response(
            [
                "Flexible timing aa, Parledu, best slot arrange chestanu. Email ID share cheyyandi.",
                "No problem, Meeku convenient timing lo demo schedule cheddam. Contact details pampandi.",
                "Sure! Flexible ga arrange cheyyachu. Online demo kavala ya office visit?",
            ]
        )

        return enhance_with_llm(
            base, user_input, "timing_flexible", conversation_memory
        )

    online_keywords = ["online", "ऑनलाइन", "google meet", "zoom", "virtual"]

    offline_keywords = ["office", "offline", "in person", "ऑफिस"]

    if conversation_memory["pending_followup"] == "contact":

        # ONLINE DEMO
        if contains_keyword(online_keywords):

            base = pick_response(
                [
                    "Perfect! Online demo arrange chestanu. Mee email ID share cheyyandi.",
                    "Sure! google Meet session setup cheddam. Contact email pampandi.",
                    "Online demo fix cheddam. Email details share chestara?",
                ]
            )

            return enhance_with_llm(
                base, user_input, "online_demo", conversation_memory
            )

        # OFFLINE DEMO
        elif contains_keyword(offline_keywords):

            base = pick_response(
                [
                    "Great! Offline meeting arrange cheddam. Mee contact details share cheyyandi.",
                    "Sure! Office visit schedule cheyyachu. Phone number pampandi.",
                    "Live demo arrange chestanu. Contact info share cheyyandi.",
                ]
            )

            return enhance_with_llm(
                base, user_input, "offline_demo", conversation_memory
            )

    
    # CONTACT / EMAIL
    if conversation_memory.get("pending_followup") == "contact":

        email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)

        phone_match = re.search(r"\b\d{3,15}\b", text)

        has_contact_intent = (
            contains_keyword(contact_keywords) or email_match or phone_match
        )

        if has_contact_intent:

            conversation_memory["pending_followup"] = None

            contact_info = None

            if email_match:
                contact_info = email_match.group()

            elif phone_match:
                contact_info = phone_match.group()

            base = pick_response(
                [
                    "Perfect andi 😊 Details note chesanu. Demo team tondarlo contact chestundi.",
                    "Great 😊 Mee contact details receive ayyayi. Demo confirmation soon share chestam.",
                    "Super 😊 Demo schedule process start chestanu. Team mimmalni contact chestundi.",
                ]
            )

            return enhance_with_llm(
                base, user_input, "contact_confirmed", conversation_memory
            )

    
    # GREETINGS
    if contains_keyword(greetings):
        name = conversation_memory.get("name")
        if name:
            base = pick_response(
                [
                    f"Welcome back {name}! Kya help karein?",
                    f"Hello {name} ji! Demo ya pricing — kya chahiye?",
                ]
            )
        else:
            base = pick_response(
                [
                    "Namaste 😊 Main aapka AI assistant hoon. Demo, pricing ya product info — kya chahiye?",
                    "Hello ji! Kya main kuch help kar sakta hoon?",
                ]
            )
        return enhance_with_llm(base, user_input, "greeting", conversation_memory)

    
    # HELP
    if contains_keyword(help_keywords):
        conversation_memory["last_intent"] = "help"
        conversation_memory["pending_followup"] = None
        base = pick_response(
            [
                "Main demos schedule karna, pricing explain karna aur product features batana — sab kar sakta hoon!",
                "Aapko demo chahiye, pricing details chahiye, ya kuch aur? Batao!",
            ]
        )
        return enhance_with_llm(base, user_input, "help", conversation_memory)

    
    # DEMO — with semantic aliases for indirect phrasing
    demo_aliases = [
        "provide karo",
        "de do",
        "dikhao",
        "book kar",
        "arrange kar",
        "schedule kar",
        "dekhna hai",
        "dekhna chahta",
        "show karo",
    ]
    if semantic_match(demo_keywords, demo_aliases):
        conversation_memory["last_intent"] = "demo"
        conversation_memory["confirmed_timing"] = None
        conversation_memory["pending_followup"] = None

        if detected_lang == "hindi" or conversation_memory["language"] == "hindi":
            base = pick_response(
                [
                    "Bilkul! Main aapke liye software demo arrange kar sakta hoon. Morning ya evening — kaunsa time comfortable rahega?",
                    "Zaroor! Demo schedule karte hain. Aapko kab convenient rahega?",
                ]
            )
        elif detected_lang == "telugu" or conversation_memory["language"] == "telugu":
            base = pick_response(
                [
                    "Sure! Meeru kosam demo arrange chestanu. Morning convenient ga untundaa?",
                    "Oka demo schedule cheyyali. Mee preferred timing cheppandi!",
                ]
            )
        else:
            base = pick_response(
                [
                    "Bilkul 😊 Demo arrange cheddam. Morning ya evening convenient untundi?",
                    "Sure 😊 Demo schedule cheddam. Meeku morning better aa evening?",
                ]
            )
        return enhance_with_llm(base, user_input, "demo", conversation_memory)

    
    # PRICING — with semantic aliases
    pricing_aliases = [
        "kitna lagega",
        "kitne mein",
        "mention karo",
        "pricing batao",
        "cost kya hai",
        "fees kya",
        "plan chahiye",
        "plans batao",
    ]
    if semantic_match(pricing_keywords, pricing_aliases):
        conversation_memory["last_intent"] = "pricing"
        conversation_memory["last_subintent"] = "pricing_intro"
        conversation_memory["pending_followup"] = None
        base = pick_response(
            [
                "Basic plan ₹999/month nundi start avuthundi 😊 Premium lo automation features untayi. Detailed comparison kavala?",
                "Pricing flexible untundi — small teams ki basic plan baguntundi. Mee team size enti?",
                "Premium plan lo AI automation and CRM features untayi 😊",
            ]
        )
        return enhance_with_llm(base, user_input, "pricing", conversation_memory)

    
    # PRICING COMPARISON FOLLOW-UP
    comparison_keywords = [
        "comparison",
        "compare",
        "difference",
        "detail comparison",
        "compare karo",
        "कंपैरिजन",
        "डिटेल",
        "difference batao",
    ]
    if conversation_memory.get("last_intent") == "pricing" and contains_keyword(
        comparison_keywords
    ):

        conversation_memory["last_subintent"] = "pricing_comparison"

        base = pick_response(
            [
                "Basic plan lo CRM and support features untayi. Premium plan lo AI automation kuda available untundi. Mee team size enti?",
                "₹999 basic plan small teams ki baguntundi. Premium plan lo extra automation and smart features untayi. Mee requirement enti?",
                "Premium plan lo AI automation, reporting and advanced features untayi 😊 Basic plan simple usage kosam better untundi. Detailed comparison kavala?",
                "Small business ki basic plan saripothundi. Bigger teams ki premium features ekkuva useful avuthayi.",
            ]
        )

        return enhance_with_llm(
            base, user_input, "pricing_comparison", conversation_memory
        )

        
    # TEAM SIZE DETECTION
    team_match = re.search(r"(\d+)", text)

    if conversation_memory.get("last_intent") == "pricing" and team_match:

        team_size = int(team_match.group(1))

        conversation_memory["team_size"] = team_size

        if team_size <= 10:

            base = pick_response(
                [
                    f"{team_size} members ki team kiite premium CRM plan baguntundi .Automation and reporting features kuda untayi.",
                    f"{team_size} users unna team ki advanced automation chaala useful avuthundi. Demo arrange cheddama?",
                    f"{team_size} member team kosam premium features better ga work avuthayi .CRM and automation rendu available unnayi.",
                    f"{team_size} members ki premium plan best option avuthundi .Inka feature comparison kavala?",
                ]
            )

        else:

            base = pick_response(
                [
                    f"{team_size} members unna large team ki premium automation solutions baguntayi. Custom features kuda available unnayi.",
                    f"Large teams kosam advanced CRM and automation tools chaala useful avuthayi 😊",
                    f"{team_size} member team ki scalable software solutions better ga work avuthayi. Demo lo complete ga explain chestanu.",
                    f"Big teams ki AI automation and reporting features chaala help avuthayi. Inka details kavala?",
                ]
            )

        return enhance_with_llm(
            base, user_input, "team_size_detection", conversation_memory
        )

    
    # PRODUCT
    if contains_keyword(product_keywords):
        conversation_memory["last_intent"] = "product"
        conversation_memory["pending_followup"] = None
        base = pick_response(
            [
                "Maa daggara AI CRM tools, automation software and custom solutions unnayi. Mee requirement enti?",
                "AI-based software solutions available unnayi. Demo lo complete ga chupisthanu. Interested aa?",
                "CRM, automation and AI tools unnayi. Mee business ki ela use avuthundo explain cheyyala?",
                "Custom software solutions kuda available unnayi. Demo arrange cheddama?",
            ]
        )
        return enhance_with_llm(base, user_input, "product", conversation_memory)

    
    # THANKS
    if any(keyword in text for keyword in thanks_keywords):
        base = pick_response(
            [
                "Parledu, Inkemaina help kavala?",
                "Happy ga help chestanu. Demo or pricing gurinchi inkemaina adagala?",
                "Anytime , Mee kosam help cheyadaniki ready ga unnaanu.",
            ]
        )
        return enhance_with_llm(base, user_input, "thanks", conversation_memory)

    
    # BYE
    if contains_keyword(bye_keywords):
        name = conversation_memory.get("name", "")
        base = pick_response(
            [
                (
                    f"Bye {name} ji, Malli kaluddam! Inkemaina help kavali ante anytime message cheyyandi."
                    if name
                    else "Bye ji, Take care andi!"
                ),
                "Alvida, Demo ya pricing gurinchi eppudaina contact cheyyandi.",
                "Sare andi, Malli matladkundam. Have a nice day!",
            ]
        )
        return enhance_with_llm(base, user_input, "bye", conversation_memory)

        
    # CONTEXT-AWARE FOLLOW-UP — intent memory
    last_intent = conversation_memory.get("last_intent")

    # DEMO FOLLOW-UP
    if (
        last_intent == "demo"
        and not contains_keyword(help_keywords)
        and not contains_keyword(greetings)
        and not contains_keyword(product_keywords)
        and not contains_keyword(pricing_keywords)
        and is_short_followup(text)
    ):

        base = pick_response(
            [
                "Demo kosam morning better aa evening convenient untundi?",
                "Mee convenience prakaram morning ya evening lo demo arrange cheddam?",
                "Timing cheppandi andi — morning aa evening?",
            ]
        )

        return enhance_with_llm(base, user_input, "demo_followup", conversation_memory)

    # PRICING FOLLOW-UP
    if last_intent == "pricing" and is_short_followup(text):

        base = pick_response(
            [
                "Pricing gurinchi inka details kavala? Feature comparison kuda explain cheyyagalanu.",
                "Mee team ki ye plan better untundo explain cheyyala?",
                "Basic and premium plans madhya difference cheppana?",
            ]
        )

        return enhance_with_llm(
            base, user_input, "pricing_followup", conversation_memory
        )

    # PRODUCT FOLLOW-UP
    if last_intent == "product" and is_short_followup(text):

        base = pick_response(
            [
                "Product gurinchi inka details kavala? Demo arrange cheddama?",
                "Ye feature gurinchi telusukovali andi?",
                "Software working ela untundo explain cheyyala?",
            ]
        )

        return enhance_with_llm(
            base, user_input, "product_followup", conversation_memory
        )

    
    # PURE LLM FALLBACK — for genuinely unknown inputs
    try:
        history_text = "\n".join(conversation_memory["history"][-5:])
        name = conversation_memory.get("name", "")
        lang = conversation_memory.get("language", "mixed")

        lang_instruction = {
            "hindi": "Reply in Hinglish (Hindi + English mix).",
            "telugu": "Mix Telugu words naturally in your Hinglish reply.",
            "mixed": "Reply in casual Hinglish.",
        }.get(lang, "Reply in casual Hinglish.")

        prompt = f"""<|im_start|>system
You are a warm multilingual Indian AI sales assistant for a software company.
{lang_instruction}
User name: {name if name else 'unknown'}
Keep reply to 2-3 sentences max. End with a helpful question.
Never say you are an AI language model.
<|im_end|>
<|im_start|>user
Conversation so far:
{history_text}

Latest message: "{user_input}"
<|im_end|>
<|im_start|>assistant
"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 100,
                "temperature": 0.75,
                "top_p": 0.9,
                "repetition_penalty": 1.15,
                "return_full_text": False,
            },
        }

        response = requests.post(
            HF_MODEL_URL, headers=headers, json=payload, timeout=25
        )
        result = response.json()

        if isinstance(result, list) and result:
            generated = result[0].get("generated_text", "").strip()
            generated = generated.replace("</s>", "").replace("<|im_end|>", "").strip()
            generated = re.sub(
                r"^(Assistant:|Bot:)\s*", "", generated, flags=re.IGNORECASE
            )

            if (
                len(generated) > 15
                and len(generated) < 500
                and not generated.lower().startswith("i am a language model")
                and not generated.lower().startswith("as an ai")
            ):
                return generated

    except Exception as e:
        print("LLM FALLBACK ERROR:", e)

    
    # FINAL FALLBACK
    return pick_response(
        [
            "Konchem clear ga cheppandi, Better ga help cheyagalanu.",
            "Ardam chesukuntunna Demo, pricing ya product gurinchi aa?",
            "Inka konchem detail iste better ga explain chestanu ",
        ]
    )



# ask_llm — preserved for any direct external usage
def ask_llm(user_input, history=None):

    try:

        history_text = "\n".join(history[-5:]) if history else ""

        prompt = f"""<|im_start|>system
You are a friendly Hindi + Telugu multilingual AI assistant.

IMPORTANT RULES:
- Speak in natural Hindi + Telugu mixed conversational style.
- Use simple Telugu words naturally inside Hinglish.
- Sound casual, warm and human-like.
- Do NOT sound corporate or robotic.
- Avoid heavy business English words.
- Keep replies short and conversational.
- Maximum 2-3 sentences.
- Use Telugu flavor words naturally like:
  andi, untundi, cheddam, kavala, avuthundi, mee kosam.
- Do NOT overuse Telugu.
- Maintain 70% Hindi/Hinglish + 30% Telugu flavor.
- Ask soft follow-up questions naturally.
- Sound like a friendly Indian assistant.

Examples:
User: demo chahiye
Assistant: Sure! Demo arrange cheddam. Morning ya evening convenient untundi?

User: pricing batao
Assistant: Basic plan ₹999/month nundi start avuthundi, Detailed comparison kavala?

User: thank you
Assistant: Parledu, Inkemaina help kavala?

<|im_end|>

<|im_start|>user
Recent conversation:
{history_text}

User: {user_input}
<|im_end|>

<|im_start|>assistant
"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 100,
                "temperature": 0.78,
                "top_p": 0.92,
                "repetition_penalty": 1.15,
                "return_full_text": False,
            },
        }

        response = requests.post(
            HF_MODEL_URL, headers=headers, json=payload, timeout=30
        )

        result = response.json()

        if isinstance(result, list):

            generated = result[0].get("generated_text", "").strip()

            generated = generated.replace("</s>", "").strip()

            generated = re.sub(
                r"^(Assistant:|Bot:)\s*", "", generated, flags=re.IGNORECASE
            )

            if len(generated) > 10:
                return generated

        return "Konchem clear ga cheppandi, Better ga help cheyagalanu."

    except Exception as e:

        print("LLM ERROR:", e)

        return "Server konchem busy undi, Konni seconds tarvata try cheyyandi."



# FLASK ROUTES — unchanged
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    conversation_history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    bot_response = generate_response(user_message, conversation_history)
    save_log(user_message, bot_response)

    return jsonify({"response": bot_response, "user_message": user_message})


@app.route("/logs", methods=["GET"])
def get_logs():
    logs = load_logs()
    return jsonify(logs)


@app.route("/clear-logs", methods=["POST"])
def clear_logs():
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    app.run(debug=True, host="0.0.0.0", port=5000)
