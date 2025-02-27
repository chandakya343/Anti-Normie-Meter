import re
import json
import os
import google.generativeai as genai
import time
from google.api_core.exceptions import ResourceExhausted

def extract_sml_response(text):
    """
    Extracts and returns the content within <sml_response>...</sml_response> tags.
    If the tags are not found, returns None.
    """
    pattern = r"<sml_response>(.*?)</sml_response>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def get_similarity_flag(guest_answer, ai_answer, chat_session):
    prompt = (
        "You are a mainstream expert. Your task is to evaluate whether two answers express essentially the same idea.\n\n"
        "Answer 1 (Guest Answer):\n" + guest_answer + "\n\n"
        "Answer 2 (AI Answer):\n" + ai_answer + "\n\n"
        "If the answers are similar in meaning, output only the digit 1. If they are not similar, output only the digit 0.\n"
        "Respond solely with your answer enclosed within <sml_response>...</sml_response> tags, and nothing else."
    )
    while True:
        try:
            response = chat_session.send_message(prompt)
            flag_text = extract_sml_response(response.text)
            flag = int(flag_text) if flag_text in ("0", "1") else 0
            return flag
        except ResourceExhausted:
            print("Rate limit reached. Sleeping for 60 seconds before retrying...")
            time.sleep(60)

# Load the JSON file that contains your existing records.
with open("final_QA.json", "r", encoding="utf-8") as f:
    data = json.load(f)

records = data.get("QA_pairs", [])

# Configure the generative model for similarity evaluation.
# Ensure your GEMINI_API_KEY environment variable is set.
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
similarity_generation_config = {
    "temperature": 0.3,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1024,
    "response_mime_type": "text/plain",
}

similarity_system_instruction = (
    "You are a mainstream expert. Your task is to evaluate whether two answers express essentially the same idea.\n\n"
    "Answer 1 (Guest Answer): {guest_answer}\n\n"
    "Answer 2 (AI Answer): {ai_answer}\n\n"
    "If the answers are similar in meaning, output only the digit 1. If they are not similar, output only the digit 0.\n"
    "Respond solely with your answer enclosed within <sml_response>...</sml_response> tags, and nothing else."
)

similarity_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",  # or your chosen model
    generation_config=similarity_generation_config,
    system_instruction=similarity_system_instruction,
)
similarity_chat_session = similarity_model.start_chat(history=[])

# Process each record to add a similarity flag.
similarity_flags = []
for record in records:
    guest_answer = record.get("guest_answer", "")
    ai_answer = record.get("LLM_answer", "")
    flag = get_similarity_flag(guest_answer, ai_answer, similarity_chat_session)
    record["similarity"] = flag
    similarity_flags.append(flag)

# Calculate the final normie score (average similarity across all QA pairs).
if records:
    final_normie_score = sum(similarity_flags) / len(records)
else:
    final_normie_score = 0

# Add the final normie score to the JSON data.
data["final_normie_score"] = final_normie_score

# Save the updated JSON to a new file.
with open("final_QA_with_similarity.json", "w", encoding="utf-8") as outfile:
    json.dump(data, outfile, indent=2)

print("Updated JSON with similarity field and final normie score saved to 'final_QA_with_similarity.json'")
