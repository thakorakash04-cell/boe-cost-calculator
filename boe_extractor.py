import os
import json
import re
import pdfplumber
import time

from google import genai
from google.genai import types

EXTRACTION_PROMPT = """
You are an expert Indian Customs Bill of Entry (BOE) data extractor.
Extract ALL data from the provided Bill of Entry and return STRICTLY valid JSON matching this exact schema:

{
  "header": {
    "total_weight_kg": 0.0,
    "exchange_rate": 0.0,
    "invoice_value_fc": 0.0,
    "freight_inr": 0.0,
    "insurance_percent": 0.0,
    "misc_charges": 0.0
  },
  "items": [
    {
      "sr_no": 1,
      "material_name": "string - exact description as shown in BOE",
      "hsn_code": "string",
      "unit_price_fc": 0.0,
      "quantity": 0.0,
      "bcd_rate_percent": 0.0,
      "sws_rate_percent": 10.0,
      "igst_rate_percent": 18.0
    }
  ]
}

Ensure all numbers are floats. Return only JSON.
"""

def extract_text_from_pdf(pdf_path: str) -> str:
    pages_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip(): pages_text.append(f"PAGE {i + 1}:\n{text.strip()}")
    except Exception: pass
    return "\n".join(pages_text)

def generate_with_fallback(client, contents):
    """Try multiple Gemini models if one is busy (503)."""
    models = ["gemini-3.6-flash", "gemini-flash-latest", "gemini-2.5-pro", "gemini-2.5-flash"]
    last_err = None

    for model_name in models:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            return res.text
        except Exception as e:
            last_err = e
            # If model strictly not found, try next immediately.
            # If 503, wait briefly and try next model.
            if "503" in str(e):
                time.sleep(2)
            continue

    raise RuntimeError(f"All Google Gemini models failed. Last error: {last_err}")


def extract_boe_data(pdf_path: str, api_key: str = None) -> dict:
    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("Google AI API Key required.")

    client = genai.Client(api_key=api_key)
    raw_text = ""

    # Strategy 1: Try text extraction
    pdf_text = extract_text_from_pdf(pdf_path)
    if pdf_text.strip():
        try:
            contents = f"{EXTRACTION_PROMPT}\n\n[Document Text]:\n{pdf_text}"
            raw_text = generate_with_fallback(client, contents)
        except Exception:
            pass

    # Strategy 2: If text fails, try sending file directly
    if not raw_text:
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            contents = [
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                EXTRACTION_PROMPT
            ]
            raw_text = generate_with_fallback(client, contents)
        except Exception as err:
            raise RuntimeError(f"Extraction failed: {err}")

    # Parse JSON
    clean_json = raw_text.strip()
    if clean_json.startswith("```json"): clean_json = clean_json[7:]
    elif clean_json.startswith("```"): clean_json = clean_json[3:]
    if clean_json.endswith("```"): clean_json = clean_json[:-3]

    match = re.search(r'\{[\s\S]*\}', clean_json)
    if match: clean_json = match.group(0)

    try:
        data = json.loads(clean_json)
    except json.JSONDecodeError:
        raise RuntimeError("AI returned invalid JSON structure.")

    if "header" not in data: data["header"] = {}
    if "items" not in data: data["items"] = []

    for idx, item in enumerate(data["items"]):
        item.setdefault("sr_no", idx + 1)
        item.setdefault("sws_rate_percent", 10.0)
        item.setdefault("igst_rate_percent", 18.0)
        item.setdefault("quantity", 0.0)

    return data
