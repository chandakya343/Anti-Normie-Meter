import os
import re
import json
import google.generativeai as genai

def extract_xml_response(text):
    """
    Extracts and returns the content within <xml_response>...</xml_response> tags.
    If the tags are not found, returns the full text.
    """
    pattern = r"<xml_response>(.*?)</xml_response>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return text.strip()

def get_llm_answer(question, chat_session):
    """
    Sends the host question to the LLM via the chat session.
    Expects the answer to be enclosed in <xml_response> tags.
    Returns the extracted answer.
    """
    response = chat_session.send_message(question)
    llm_answer = extract_xml_response(response.text)
    return llm_answer

def main():
    # Load the input JSON file that contains the host questions and guest answers.
    input_filename = "Satya_Nadella_Microsoft_s_AGI_Plan_Quantum_Breakthrough_QA.json"  # Change this to your actual input file name.
    with open(input_filename, "r", encoding="utf-8") as infile:
        input_data = json.load(infile)
    
    # Configure the Google generative AI model.
    # Ensure the GEMINI_API_KEY environment variable is set.
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    
    # Define generation configuration.
    generation_config = {
        "temperature": 0.3,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 1024,
        "response_mime_type": "text/plain",
    }
    
    # Updated system instruction prompt.
    system_instruction = (
        "You are a mainstream expert and will be asked questions you need to answer professionally. "
        "For every question provided, please return your expert answer solely within XML tags as follows: "
        "<xml_response>Your simple text answer here</xml_response>. "
        "Do not include any additional commentary, explanations, or text outside of these XML tags. "
        "No extra xml tags should be included, only the <xml_response>...</xml_response tags> with the answer inside. "
        "The answer should be plain text no xml tags to be used here "
        "Answer the question completely and in a self-contained manner."
    )
    
    # Create the model instance using the Google generative AI API.
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite-preview-02-05",  # or another valid model name
        generation_config=generation_config,
        system_instruction=system_instruction,
    )
    
    # Start a new chat session.
    chat_session = model.start_chat(history=[])
    
    output_QA = []
    # Process each QA pair from the input.
    for pair in input_data.get("QA_pairs", []):
        host_question = pair.get("Extracted_question", "")
        guest_answer = pair.get("Guest_answer", "")
        # Send the host question to the LLM and get its expert answer.
        llm_answer = get_llm_answer(host_question, chat_session)
        # Create a new record with host question, guest answer, and LLM answer.
        print(f"Host Question: {host_question}")
        print(f"LLM Answer: {llm_answer}")
        output_record = {
            "host_question": host_question,
            "guest_answer": guest_answer,
            "LLM_answer": llm_answer
        }
        output_QA.append(output_record)
    
    final_output = {"QA_pairs": output_QA}
    
    # Save the final JSON output.
    output_filename = "final_QA.json"
    with open(output_filename, "w", encoding="utf-8") as outfile:
        json.dump(final_output, outfile, indent=2)
    
    print(f"Final JSON saved to {output_filename}")

if __name__ == "__main__":
    main()