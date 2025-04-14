import litellm
import os
import json
import requests
from flask import Flask, request, jsonify
from config import AI_ROUTER_API_KEY  
from twilio.twiml.messaging_response import MessagingResponse
from langdetect import detect
from deep_translator import GoogleTranslator
from textblob import TextBlob

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "your_twilio_account_sid")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "your_twilio_phone_number")

ZENTOI_API_KEY = os.getenv("ZENTOI_API_KEY", "102c697b14ec4874bad0e9c68464c46683c7fa497a724245b538929c4ab9bc16")
ZENTOI_GUEST_URL = "https://api.zenoti.com/v1/guests"
ZENTOI_BOOKINGS_URL = os.getenv("ZENTOI_BOOKINGS_URL", "https://api.zenoti.com/v1/bookings?is_double_booking_enabled=true")
ZENTOI_GUESTS_URL = os.getenv("ZENTOI_GUESTS_URL", "https://api.zenoti.com/v1/guests")


OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://api.openrouter.ai/v1/chat/completions")   

HEADERS = {
    "Authorization": "apikey 102c697b14ec4874bad0e9c68464c46683c7fa497a724245b538929c4ab9bc16",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Load services from services.json
SERVICES_FILE_PATH = "services.json"
try:
    with open(SERVICES_FILE_PATH, "r") as file:
        services_data = json.load(file)
        services_list = services_data.get("services", [])
except FileNotFoundError:
    print(f"⚠️ Error: {SERVICES_FILE_PATH} not found.")
    services_list = []

# Group services by category
services_by_category = {}
for service in services_list:
    category = service.get("category", "Uncategorized")
    if category not in services_by_category:
        services_by_category[category] = []
    services_by_category[category].append(service)

session_data = {}

def get_categories_list():
    """Returns a formatted list of categories."""
    if not services_by_category:
        return "⚠️ No categories available at the moment."
    return "\n".join(f"- {category}" for category in services_by_category.keys())

def get_services_in_category(category):
    """Returns a formatted list of services in a specific category."""
    services = services_by_category.get(category, [])
    if not services:
        return f"⚠️ No services available in the category '{category}'."
    return "\n".join(f"- {service['name']}" for service in services)

def create_guest(full_name, gender, mobile_number, email, date_of_birth="1983-12-24T00:00:00"):
    # Ensure gender is correctly handled
    gender_value = 0 if gender.lower() == "female" else 1
    gender_name = gender.capitalize()

    # Ensure the full name is correctly split into first and last name
    name_parts = full_name.split()
    first_name = name_parts[0]
    last_name = name_parts[-1]
    user_name = full_name.replace(" ", "").lower()

    # Build the payload
    payload = {
        "center_id": "2bbedaec-1354-4770-8bc0-ae065081ca25",
        "personal_info": {
            "user_name": user_name,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "gender": gender_value,
            "gender_name": gender_name,
            "date_of_birth": date_of_birth,  
            "is_minor": False,
            "nationality_id": 48,
            "mobile_phone": {
                "country_code": 171, 
                "phone_code": 0,
                "number": mobile_number
            }
        }
    }

    # Print the payload with double quotes for debugging
    import json
    print("Payload:", json.dumps(payload, indent=4))

    try:
        # Send the POST request
        response = requests.post(ZENTOI_GUEST_URL, json=payload, headers=HEADERS)

        # Handle the response
        if response.status_code == 200:
            guest_id = response.json().get("id")
            print(f"Guest created successfully. Guest ID: {guest_id}")
            return guest_id
        else:
            print(f"Guest creation failed. Status: {response.status_code}")
            print("Response:", response.text)
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
        return None
    

def book_appointment(full_name, gender, mobile_number, email, service_id):
    """Creates a guest, then books an appointment using their ID."""
    guest_id = create_guest(full_name, gender, mobile_number, email)
    if not guest_id:
        return "⚠️ Failed to create guest."

    payload = {
        "is_only_catalog_employees": True,
        "guests": [
            {
                "id": guest_id, 
                "items": [
                    {
                        "item": {"id": service_id},  
                        "therapist": {"gender": "1", "id": "07855496-bc49-4eaf-9bf5-d27a1df54a2b"}
                    }
                ]
            }
        ],
        "center_id": "2bbedaec-1354-4770-8bc0-ae065081ca25",
        "date": "2025-04-08"
    }

    print("Booking Appointment Payload:", json.dumps(payload, indent=4))

    response = requests.post(ZENTOI_BOOKINGS_URL, json=payload, headers=HEADERS)

    print("Booking Response Status:", response.status_code)
    print("Booking Response JSON:", response.json())
    print("Booking Response Text:", response.text)

    if response.status_code == 200:
        return "✅ Appointment booked successfully!"
    else:
        return f"⚠️ Booking failed: {response.json().get('message', response.text)}"


def parse_appointment_request(user_message):
    """Extracts appointment details from user message."""
    parts = user_message.lower().replace("book appointment:", "").strip().split(",")
    parts = [part.strip() for part in parts] 
    
    if len(parts) == 4:
        return parts[0], parts[1], parts[2], parts[3]
    
    return None

def translate_to_english(text):
    """Translates text to English."""
    try:
        return GoogleTranslator(source='ar', target='en').translate(text)
    except Exception as e:
        print(f"Translation to English failed: {e}")
        return text

def translate_to_arabic(text):
    """Translates text to Arabic."""
    try:
        return GoogleTranslator(source='en', target='ar').translate(text)
    except Exception as e:
        print(f"Translation to Arabic failed: {e}")
        return text
    
def correct_spelling(text):
    """Corrects spelling mistakes in the input text."""
    return str(TextBlob(text).correct())

def get_ai_response(user_id, user_message):
    """Handles user queries, predefined responses, and appointment booking (step-by-step)."""

    user_message = correct_spelling(user_message)

    # Detect language
    try:
        user_language = detect(user_message)
    except Exception as e:
        user_language = "en"  # Default to English if detection fails

    # Translate Arabic input to English for processing
    if user_language == "ar":
        user_message = translate_to_english(user_message)

    lower_message = user_message.lower()

    # Handle "exit" or "cancel" to reset the flow
    if lower_message in ["exit", "cancel"]:
        if user_id in session_data:
            del session_data[user_id]
        response = "You have exited the current flow. How can I assist you further?"
        return translate_to_arabic(response) if user_language == "ar" else response

    # General question detection (e.g., symptoms, diseases, treatments)
    general_question_keywords = ["symptoms", "disease", "treatment", "causes", "health issue", "medicine", "cure"]
    if any(keyword in lower_message for keyword in general_question_keywords):
        try:
            # Use litellm model for general questions
            response = litellm.completion(
                model="groq/llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": user_message}],
                temperature=0.7,
                api_key=AI_ROUTER_API_KEY
            )
            response_text = response["choices"][0]["message"]["content"]
            return translate_to_arabic(response_text) if user_language == "ar" else response_text
        except Exception as e:
            print(f"Error with litellm model: {e}")
            response = "⚠️ Sorry, I couldn't fetch the information at the moment. Please try again later."
            return translate_to_arabic(response) if user_language == "ar" else response

    # Phrases to trigger the booking flow
    booking_phrases = [
        "i want to book an appointment",
        "i need to schedule an appointment",
        "can i book an appointment?",
        "i'd like to make an appointment",
        "how do i book an appointment?",
        "i want to connect with the doctor",
        "schedule a meeting with the doctor",
        "book a session"
    ]

    # Check if the user's message matches any booking phrase
    if any(phrase in lower_message for phrase in booking_phrases):
        session_data[user_id] = {
            "step": "category_selection",
            "data": {},
            "is_booking": True  # Flag to indicate booking process
        }
        categories = get_categories_list()
        response = (
            "Sure! Let's book an appointment. Here are the categories of services we offer:\n"
            f"{categories}\n\nPlease select a category to proceed."
        )
        return translate_to_arabic(response) if user_language == "ar" else response

    # Handle "view services" request
    if "services" in lower_message and not any(phrase in lower_message for phrase in booking_phrases):
        session_data[user_id] = {
            "step": "category_selection",
            "data": {},
            "is_booking": False  # Flag to indicate viewing services only
        }
        categories = get_categories_list()
        response = (
            "Here are the categories of services we offer:\n"
            f"{categories}\n\nPlease select a category to see the services."
        )
        return translate_to_arabic(response) if user_language == "ar" else response

    # Continue step-by-step process
    if user_id in session_data:
        step_info = session_data[user_id]
        step = step_info["step"]
        user_data = step_info["data"]
        is_booking = step_info["is_booking"]

        if step == "category_selection":
            selected_category = next(
                (category for category in services_by_category.keys() if category.lower() == lower_message), None
            )
            if not selected_category:
                response = "⚠️ Please choose a valid category from the list above or type 'exit' to cancel."
                return translate_to_arabic(response) if user_language == "ar" else response
            user_data["category"] = selected_category
            step_info["step"] = "service_selection"
            services = get_services_in_category(selected_category)
            response = (
                f"Great! Here are the services under '{selected_category}':\n"
                f"{services}\n\nPlease select a service or type 'exit' to cancel."
            )
            return translate_to_arabic(response) if user_language == "ar" else response

        elif step == "service_selection":
            selected_service = next(
                (service for service in services_by_category[user_data["category"]] if service["name"].lower() == lower_message),
                None
            )
            if not selected_service:
                response = "⚠️ Please choose a valid service from the list above or type 'exit' to cancel."
                return translate_to_arabic(response) if user_language == "ar" else response
            user_data["service_id"] = selected_service["id"]
            user_data["service_name"] = selected_service["name"]

            if is_booking:
                step_info["step"] = "full_name"
                response = f"Great choice! You selected '{selected_service['name']}'. What's your full name?"
                return translate_to_arabic(response) if user_language == "ar" else response
            else:
                # If not booking, just show the service details
                del session_data[user_id]  # Exit the flow after showing service details
                response = (
                    f"Here are the details for '{selected_service['name']}':\n"
                    f"Description: {selected_service.get('description', 'No description available')}\n"
                    f"Duration: {selected_service.get('duration', 'N/A')} minutes\n"
                    f"Price: {selected_service['price_info'].get('final_price', 'N/A')} {selected_service['price_info'].get('currency_id', '')}\n"
                    "Let me know if you'd like to book this service or type 'exit' to cancel."
                )
                return translate_to_arabic(response) if user_language == "ar" else response

        elif step == "full_name":
            user_data["full_name"] = user_message.strip()
            step_info["step"] = "gender"
            response = "Thanks! What is your gender? (Male/Female) or type 'exit' to cancel."
            return translate_to_arabic(response) if user_language == "ar" else response

        elif step == "gender":
            if "male" not in lower_message and "female" not in lower_message:
                response = "⚠️ Please enter either 'Male' or 'Female' or type 'exit' to cancel."
                return translate_to_arabic(response) if user_language == "ar" else response
            user_data["gender"] = user_message.strip()
            step_info["step"] = "mobile_number"
            response = "Got it. Can you please provide your mobile number or type 'exit' to cancel?"
            return translate_to_arabic(response) if user_language == "ar" else response

        elif step == "mobile_number":
            if not user_message.replace(" ", "").isdigit():
                response = "⚠️ That doesn't look like a valid number. Please enter digits only or type 'exit' to cancel."
                return translate_to_arabic(response) if user_language == "ar" else response
            user_data["mobile_number"] = user_message.strip()
            step_info["step"] = "email"
            response = "Almost done! Please provide your email address or type 'exit' to cancel."
            return translate_to_arabic(response) if user_language == "ar" else response

        elif step == "email":
            if "@" not in user_message or "." not in user_message:
                response = "⚠️ Please enter a valid email address or type 'exit' to cancel."
                return translate_to_arabic(response) if user_language == "ar" else response
            user_data["email"] = user_message.strip()

            # Booking complete
            full_name = user_data["full_name"]
            gender = user_data["gender"]
            mobile_number = user_data["mobile_number"]
            email = user_data["email"]
            service_id = user_data["service_id"]

            # Call the booking function
            response = book_appointment(full_name, gender, mobile_number, email, service_id)

            # Clear session
            del session_data[user_id]

            if response.startswith("✅"):
                response = (
                    f"{response}\n\n📅 Your appointment for *{user_data['service_name']}* is confirmed!\n"
                    "Is there anything else I can help you with today?"
                )
                return translate_to_arabic(response) if user_language == "ar" else response
            return translate_to_arabic(response) if user_language == "ar" else response

    # Fallback predefined responses
    CUSTOM_RESPONSES = {
        "location": "Find our location here: https://maps.app.goo.gl/1eWMncokFvpimaeg8 📍",
        "contact information": "You can contact us at:\n📞 +974 4433 9444\n📞 +974 6693 0569\n📧 info@thewellnesslab.qa",
        "business hours": "Our hours:\nWednesday: 10 AM – 12 AM\nThursday: 10 AM – 12 AM\nFriday: Closed\nSaturday: 10 AM – 12 AM\nSunday: 10 AM – 12 AM\nMonday: 10 AM – 12 AM\nTuesday: 10 AM – 12 AM",
        "pre-treatment instructions": "Follow your specialist’s advice. Stay hydrated! 💧",
        "post-treatment care instructions": "Drink water and avoid excessive sun exposure. 🌿",
        "prices": "Pricing depends on the service. Could you specify which treatment you need?",
        "discounts": "We occasionally offer promotions! Check our website or contact us directly.",
        "who are you": "I am *Wellness Labs* chatbot, here to assist you! 😊",
        "wellness lab": "Yes! This is *Wellness Labs*, your trusted wellness center. How may I assist you?",
    }

    for key, response in CUSTOM_RESPONSES.items():
        if key in lower_message:
            response = response
            return translate_to_arabic(response) if user_language == "ar" else response

    # Default fallback to AI model
    try:
        response = litellm.completion(
            model="groq/llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": user_message}],
            temperature=0.7,
            api_key=AI_ROUTER_API_KEY
        )
        response_text = response["choices"][0]["message"]["content"]
        return translate_to_arabic(response_text) if user_language == "ar" else response_text
    except Exception as e:
        print(f"Error with AI model: {e}")

    # Final fallback response
    fallback_response = (
        "I'm sorry, I couldn't find the information you're looking for. "
        "Please try rephrasing your question or let me connect you to a human agent for further assistance."
    )
    return translate_to_arabic(fallback_response) if user_language == "ar" else fallback_response


@app.route("/twilio-webhook", methods=["POST"])
def twilio_webhook():
    """Handles incoming Twilio messages and responds using AI chatbot."""
    incoming_msg = request.form.get("Body", "").strip()  
    sender_number = request.form.get("From", "")  
    
    print(f"📩 Received from {sender_number}: {incoming_msg}")

    bot_response = get_ai_response(sender_number, incoming_msg)
    
    twilio_response = MessagingResponse()
    twilio_response.message(bot_response)
    
    print(f"🤖 Responding: {bot_response}")
    return str(twilio_response)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
