# Anti-Normie-Meter

## Overview
The Anti-Normie Meter is a novel system designed to quantify how “Normie” (i.e., mainstream or AI-aligned) a piece of content is. It does so by measuring the divergence between human (guest) opinions and AI-generated responses to the same set of questions. This metric, akin to financial alpha and beta, serves as an indicator of content originality and independent thought.

## 1. Problem Statement & Hypothesis

### Problem
With the increasing proliferation of AI-generated content, the internet is at risk of being flooded with homogenized “AI slop.” This saturation diminishes genuine, independent perspectives and undermines diverse opinions.

### Hypothesis
Content that deviates from typical AI-generated responses (i.e., has a lower similarity to AI outputs) is more original and “anti-normie.” Conversely, content that aligns closely with AI answers is more mainstream.

## 2. System Architecture & Workflow

### Agent 1: Transcript Fetcher
- **Function**: Fetches YouTube transcripts (manual or auto-generated) using a custom script built on top of `yt_dlp` and `youtube_transcript_api`.
- **Key Detail**: Extracts metadata (title, uploader) and sanitizes file names for saving transcripts (see `fetch_transcript.py`).

### Agent 2: Transcript to Q/A Extractor
- **Function**: Processes transcript text by splitting it into manageable chunks and extracts complete question-answer (Q/A) pairs using a generative model with a specialized XML/JSON-wrapped prompt.
- **Key Detail**: Ensures each question is self-contained and merges related follow-ups if necessary (see `transcript2QA.py`).

### Agent 3: AI Q/A Generator
- **Function**: For every extracted question, generates an AI answer using the Google Generative AI API with tailored system instructions.
- **Key Detail**: The guest answer (from the original content) and the AI-generated answer are both preserved for comparison (see `QAtoAIQA.py`).

### Agent 4: Similarity Evaluator
- **Function**: Compares the guest’s answer to the AI’s answer using another AI model that outputs a binary similarity flag (1 for similar, 0 for dissimilar).
- **Key Detail**: Aggregates these flags to produce a final “normie score,” reflecting the overall alignment of the content with mainstream AI opinion (see `similarity.py`).

## 3. Implementation Details

### From Scratch, No Boilerplate
Every component of the system has been coded from scratch using Python. There is no dependency on frameworks such as LangChain; the implementation relies solely on direct API calls (e.g., Google Generative AI API) and custom logic.

### Agentic Design
Each module functions as an independent agent focused on a single responsibility—from transcript fetching to similarity scoring. This modular approach enhances maintainability and scalability.

### Use of APIs
The system leverages the Google Generative AI API (configured via `GEMINI_API_KEY`) to generate and compare responses.

### Error Handling & Logging
Robust error handling (e.g., transcript retrieval failures) and detailed logging are built into each agent, ensuring smooth operation and easier debugging.

## 4. Novelty & Differentiators

### Agentic Implementation
The system’s architecture is composed of distinct, purpose-built agents that work sequentially to transform raw content into a quantifiable metric.

### Originality Measurement
Unlike typical watermark or content-based filters, the Anti-Normie Meter quantifies opinion divergence—serving as an “alpha” score in content quality.

### From-Scratch Coding
The entire system is a custom-built solution without reliance on boilerplate libraries or frameworks, showcasing a unique, lean, and tailored approach to addressing content homogenization.

## Conclusion
The Anti-Normie Meter provides a groundbreaking method to evaluate content originality by comparing human opinions with AI-generated responses. By quantifying how divergent a guest’s opinions are from mainstream AI perspectives, it offers a clear, measurable insight into the creative diversity of digital content. This from-scratch, agent-based implementation not only addresses the issue of AI-generated content saturation but also opens avenues for more nuanced content curation and quality assurance in the digital age.
