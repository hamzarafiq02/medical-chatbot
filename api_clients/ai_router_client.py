import litellm
import os
import requests
from flask import Flask, request, jsonify
from config import AI_ROUTER_API_KEY  
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__) 

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_twilio_account_sid")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "your_twilio_phone_number")

ZENTOI_API_KEY = os.getenv("ZENTOI_API_KEY", "your_zentoi_api_key")
ZENTOI_BASE_URL = os.getenv("ZENTOI_BASE_URL", "https://api.zentoi.com/booking")

OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://api.openrouter.ai/v1/chat/completions")   



CUSTOM_RESPONSES = {
    "location": "Find our location here: https://maps.app.goo.gl/1eWMncokFvpimaeg8 📍",
    "contact information": "You can contact us at:\n📞 +974 4433 9444\n📞 +974 6693 0569\n📧 info@thewellnesslab.qa",
    "services": "We offer:\n- Hair Treatment 💇‍♀️\n- Face Treatment 💆\n- Nutrition & Wellness 🥗\n- Slimming 🌿\n- Physiotherapy 🏋️\n\nLet me know if you need more details!",
    "booking": "To book an appointment, use this format:\n📅 *book appointment: name, phone, service, datetime*",
    "appointments": "Use this format to book:\n📅 *book appointment: name, phone, service, datetime*",
    "business hours": "Our hours:\n🕰 Wednesday - Tuesday: 10 AM – 12 AM\n🚫 Friday: Closed",
    
    "pre-treatment instructions": "Follow your specialist’s advice. Stay hydrated! 💧",
    "post-treatment care instructions": "Drink water and avoid excessive sun exposure. 🌿",
    "prices": "Pricing depends on the service. Could you specify which treatment you need?",
    "discounts": "We occasionally offer promotions! Check our website or contact us directly.",
    "who are you": "I am *Wellness Labs* chatbot, here to assist you! 😊",
    "wellness lab": "Yes! This is *Wellness Labs*, your trusted wellness center. How may I assist you?",
}

def get_ai_response(user_message, model="deepseek/deepseek-r1"):
    headers = {
        "Authorization": f"Bearer {AI_ROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    lower_message = user_message.lower()
    for key in CUSTOM_RESPONSES:
        if key in lower_message:
            return CUSTOM_RESPONSES[key]

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": user_message}],
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an error for 4xx, 5xx responses
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print(get_ai_response("I have a headache"))
