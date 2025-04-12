import openai

# Function to initialize OpenAI client (this just checks that the API key is set correctly)
def get_openai_client(api_key):
    openai.api_key = api_key
    return openai

# Function to get sarcastic medical response from GPT-4
def get_sarcastic_medical_response(client, user_input):
    response = client.ChatCompletion.create(
        model='gpt-4',
        messages=[
            {"role": "system", "content": """You are a humorous and sarcastic assistant focused on medical-related queries. Provide witty, darkly comedic responses that make light of common health struggles. Avoid giving actual medical advice; instead, point out absurdities or common situations in health with humor. Use dark humor and sarcasm, but always encourage consulting a medical professional for accurate advice."""},
            {"role": "user", "content": user_input}
        ]
    )
    return response['choices'][0]['message']['content']
