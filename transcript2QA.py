import re
import os
import sys
import json
import logging
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content

# Configure logging: adjust level and format as needed.
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def parse_video_id(url: str) -> str:
    """Extracts the YouTube video ID from a URL."""
    logging.debug("Parsing video ID from URL: %s", url)
    match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11})', url)
    if match:
        video_id = match.group(1)
        logging.debug("Found video ID: %s", video_id)
        return video_id
    else:
        logging.error("Unable to find a valid video ID in the given URL.")
        raise ValueError("Unable to find a valid video ID in the given URL.")

def get_title_and_uploader(url: str):
    """Retrieves the title and uploader of the YouTube video using yt-dlp."""
    logging.info("Fetching title and uploader for URL: %s", url)
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'Unknown_Title')
        uploader = info.get('uploader', 'Unknown_Uploader')
        logging.debug("Extracted title: %s, uploader: %s", title, uploader)
        return title, uploader

def fetch_transcripts(video_id: str, language: str = 'en'):
    """Fetches manual transcript if available, else auto-generated transcript."""
    logging.info("Fetching transcripts for video ID: %s", video_id)
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        manual_transcript, auto_transcript = "", ""
        # Try to get a manually created transcript.
        try:
            manual_trans = transcript_list.find_manually_created_transcript([language])
            manual_transcript = "\n".join([item['text'] for item in manual_trans.fetch()])
            logging.info("Manual transcript retrieved successfully.")
        except Exception as e:
            logging.warning("No manual transcript found: %s", e)
        # Try to get an auto-generated transcript.
        try:
            auto_trans = transcript_list.find_generated_transcript([language])
            auto_transcript = "\n".join([item['text'] for item in auto_trans.fetch()])
            logging.info("Auto-generated transcript retrieved successfully.")
        except Exception as e:
            logging.warning("No auto-generated transcript found: %s", e)
        
        return manual_transcript, auto_transcript
    except Exception as e:
        logging.error("Could not retrieve transcripts for video ID %s. Error: %s", video_id, e)
        return "", ""

def split_text_into_chunks(text: str, max_words: int = 2000):
    """
    Splits text into chunks of roughly max_words.
    Uses full stops as natural breakpoints.
    """
    logging.info("Splitting transcript into chunks of up to %d words", max_words)
    sentences = re.split(r'(?<=\.)\s+', text)
    chunks = []
    current_chunk = []
    current_word_count = 0

    for sentence in sentences:
        words = sentence.split()
        if current_word_count + len(words) > max_words and current_chunk:
            chunk = " ".join(current_chunk)
            chunks.append(chunk)
            logging.debug("Created a chunk with %d words", current_word_count)
            current_chunk = []
            current_word_count = 0
        current_chunk.append(sentence)
        current_word_count += len(words)
    if current_chunk:
        chunk = " ".join(current_chunk)
        chunks.append(chunk)
        logging.debug("Created final chunk with %d words", current_word_count)
    logging.info("Total chunks created: %d", len(chunks))
    return chunks

def extract_qa_from_chunk(chunk_text: str, chat_session):
    """
    Sends a transcript chunk to the generative model to extract Q/A pairs.
    Uses XML-wrapped JSON for structured extraction.
    """
    response = chat_session.send_message(chunk_text).text
    
    print("\n=== RAW MODEL RESPONSE ===\n")
    print(response)
    print("\n=========================\n")

    # Extract content inside <json_QA>...</json_QA> tags
    start_tag = "<json_QA>"
    end_tag = "</json_QA>"
    
    start_idx = response.find(start_tag)
    end_idx = response.find(end_tag)
    
    if start_idx == -1 or end_idx == -1:
        print("Error: Could not find <json_QA> tags in response.")
        return []

    start_idx += len(start_tag)
    json_text = response[start_idx:end_idx].strip()

    try:
        qa_data = json.loads(json_text)
        return qa_data.get("QA_pairs", [])
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return []

def main():
    if len(sys.argv) < 2:
        logging.error("Usage: python transcript_to_qa.py <youtube_url>")
        sys.exit(1)
        
    youtube_url = sys.argv[1]
    logging.info("Processing YouTube URL: %s", youtube_url)
    
    video_id = parse_video_id(youtube_url)
    title, uploader = get_title_and_uploader(youtube_url)
    logging.info("Video Title: %s | Uploader: %s", title, uploader)
    
    manual_transcript, auto_transcript = fetch_transcripts(video_id)
    
    if manual_transcript:
        transcript = manual_transcript
        logging.info("Using manual transcript.")
    elif auto_transcript:
        transcript = auto_transcript
        logging.info("Using auto-generated transcript.")
    else:
        logging.error("No transcript available for this video.")
        sys.exit(1)
    
    chunks = split_text_into_chunks(transcript, max_words=2000)
    logging.info("Transcript split into %d chunk(s).", len(chunks))
    
    # Configure the Gemini generative model.
    logging.info("Configuring Gemini generative model.")
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    
    generation_config = {
      "temperature": 0.3,
      "top_p": 0.95,
      "top_k": 40,
      "max_output_tokens": 8192
    }
    
    system_instruction = (
    "You are a transcript Q/A extractor. Your task is to analyze a provided transcript chunk and extract all questions along with the corresponding guest answers.\n\n"

    "Guidelines:\n\n"

    "1. Verbatim Guest Answers:\n"
    "- Extract the guest’s response exactly as it appears.But in the case the answer is extremely incomplete paraphrase the guests answer. \n\n"

    "2. Complete, Self-Contained Questions:(very very important)\n"
    "- Identify every question present in the transcript chunk.\n"
    "- If a question appears only as a sub-question or seems incomplete, incorporate any surrounding context so that the **final 'Extracted_question' is a complete, standalone inquiry.**\n\n"

    "3. Extraction Requirements:\n"
    "- Only extract sections where a clear question is asked and a guest answer is provided.\n"
    "- Merge multi-part or follow-up questions into one coherent question if needed.\n\n"

    "4. Sequential Numbering:\n"
    "- Each Q/A pair must have a unique, sequential number.\n\n"

    "5. Structured Output Format:\n"
    "- Wrap the JSON inside `<json_QA>...</json_QA>` tags.\n\n"

    "**Important Instructions:**\n"
    "- **DO NOT** include anything outside the `<json_QA>` tags.\n"
    "- Make sure that each extracted_question is a complete, standalone inquiry. if not add context from the previous extracted_question/guest_answer \n"
    "- The JSON structure must strictly follow this format:\n\n"

    "<json_QA>\n"
    "{\n"
    '  "QA_pairs": [\n'
    '    {"number": 1, "Extracted_question": "Your complete question here?", "Guest_answer": "The guest’s answer exactly as spoken."},\n'
    '    {"number": 2, "Extracted_question": "...", "Guest_answer": "..."}\n'
    '  ]\n'
    '}\n'
    "</json_QA>\n\n"

    "- **DO NOT** generate explanations, metadata, or comments.\n"
)


    
    model = genai.GenerativeModel(
      model_name="gemini-2.0-flash",
      generation_config=generation_config,
      system_instruction=system_instruction,
    )
    
    chat_session = model.start_chat(history=[])
    logging.info("Chat session started with Gemini model.")
    
    all_qa_pairs = []
    for idx, chunk in enumerate(chunks, start=1):
        logging.info("Processing chunk %d...", idx)
        qa_pairs = extract_qa_from_chunk(chunk, chat_session)
        logging.debug("Chunk %d returned QA pairs: %s", idx, qa_pairs)
        all_qa_pairs.extend(qa_pairs)
    
    # Renumber the QA pairs sequentially.
    for i, qa in enumerate(all_qa_pairs, start=1):
        qa["number"] = i
    
    output_data = {"QA_pairs": all_qa_pairs}
    
    safe_title = re.sub(r'[^A-Za-z0-9_-]+', '_', title)
    output_filename = f"{safe_title}_QA.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    logging.info("QA pairs saved to %s", output_filename)

if __name__ == "__main__":
    main()
