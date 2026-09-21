import os
import json
import time
import logging
import random
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from groq import Groq
import docx2txt
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
load_dotenv()

groq_client = Groq() 
GROQ_MODEL = 'openai/gpt-oss-20b'

class EmailClassification(BaseModel):
    category: str = Field(description="Must be one of: 'BL_COMPARISON', 'SI_REQUEST', 'INVOICE_QUERY', 'GENERAL', 'SPAM'")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    
class ShipmentDetails(BaseModel):
    shipper: Optional[str] = Field(default=None, description="Name of the shipper. Null if unreadable.")
    consignee: Optional[str] = Field(default=None, description="Name of the consignee. Null if unreadable.")
    notify_party: Optional[str] = Field(default=None, description="Name of the notify party. Null if unreadable.")
    port_of_loading: Optional[str] = Field(default=None, description="Port of loading. Null if unreadable.")
    port_of_discharge: Optional[str] = Field(default=None, description="Port of discharge. Null if unreadable.")
    container_count: Optional[int] = Field(default=None, description="Total number of containers. Null if unreadable.")
    gross_weight_kg: Optional[float] = Field(default=None, description="Total gross weight strictly in kilograms. Null if unreadable.")
    requires_human_review: bool = Field(default=False, description="Set to true if document is blurry, contradictory, or missing data.")

class DocumentVerificationSystem:
    def __init__(self, data_dir: str):
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.inbox_dir = os.path.join(base_path, data_dir, "inbox")
        self.attachments_dir = os.path.join(base_path, data_dir, "attachments")
        self.output_file = os.path.join(base_path, "sample_submission.json")

    def classify_email(self, email_data: Dict) -> EmailClassification:
        prompt = f"""Analyze the following email and classify it into one of these exact categories: 'BL_COMPARISON', 'SI_REQUEST', 'INVOICE_QUERY', 'GENERAL', 'SPAM'.
You MUST output valid JSON matching this schema: {{"category": "<category_name>", "confidence": <float>}}
Subject: {email_data.get('subject', '')}
Body: {email_data.get('body', '')}"""
        
        for attempt in range(5):
            try:
                response = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                return EmailClassification.model_validate_json(response.choices[0].message.content)
            except Exception as e:
                time.sleep(4 * (2 ** attempt))
        return EmailClassification(category="GENERAL", confidence=0.0)

    def extract_text_from_file(self, file_path: str) -> str:
        ext = file_path.lower().split('.')[-1]
        try:
            if ext == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f: return f.read()
            elif ext == 'docx':
                return docx2txt.process(file_path)
            elif ext == 'xlsx':
                return pd.read_excel(file_path).to_string()
            return ""
        except Exception as e:
            logging.error(f"Failed to read {file_path}: {e}")
            return ""

    def extract_document_data(self, filename: str) -> ShipmentDetails:
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(self.attachments_dir, safe_filename)
        
        if not os.path.exists(file_path):
            return ShipmentDetails(requires_human_review=True)

        doc_text = self.extract_text_from_file(file_path)
        if not doc_text.strip():
            return ShipmentDetails(requires_human_review=True)

        prompt = f"""Extract the following shipping details from this document text: shipper, consignee, notify party, port of loading, port of discharge, container count, and gross weight in kilograms. If missing, leave null.
You MUST output valid JSON matching the exact schema requirements.
Document Text:
{doc_text[:4000]}"""

        for attempt in range(5):
            try:
                response = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                return ShipmentDetails.model_validate_json(response.choices[0].message.content)
            except Exception as e:
                time.sleep(4 * (2 ** attempt))
        return ShipmentDetails(requires_human_review=True)

    def normalize_string(self, val: Any) -> str:
        if val is None: return ""
        return str(val).lower().strip().replace('\n', ' ')

    def compare_documents(self, si_data: ShipmentDetails, bl_data: ShipmentDetails) -> Dict[str, Any]:
        mismatches = {}
        fields = ['shipper', 'consignee', 'notify_party', 'port_of_loading', 'port_of_discharge', 'container_count', 'gross_weight_kg']
        for field in fields:
            si_val, bl_val = getattr(si_data, field), getattr(bl_data, field)
            if str(si_val).lower().strip() != str(bl_val).lower().strip():
                mismatches[field] = {"SI": si_val, "BL": bl_val}
        return mismatches

    def process_single_email(self, email_id: str) -> Dict[str, Any]:
        file_path = os.path.join(self.inbox_dir, f"{email_id}.json")
        with open(file_path, 'r') as f:
            email_data = json.load(f)

        classification = self.classify_email(email_data)
        record = {"category": classification.category, "needs_human_review": False, "mismatch_found": False, "discrepancies": {}}

        if classification.category == "BL_COMPARISON":
            attachments = email_data.get("attachments", [])
            si_file = next((f for f in attachments if "SI" in f), None)
            bl_file = next((f for f in attachments if "BL" in f), None)

            if not si_file or not bl_file:
                record["needs_human_review"] = True
            else:
                si_data = self.extract_document_data(si_file)
                bl_data = self.extract_document_data(bl_file)

                if si_data.requires_human_review or bl_data.requires_human_review:
                    record["needs_human_review"] = True
                else:
                    mismatches = self.compare_documents(si_data, bl_data)
                    if mismatches:
                        record["mismatch_found"] = True
                        record["discrepancies"] = mismatches
                    else:
                        record["mismatch_found"] = False
                        record["discrepancies"] = "No mismatch detected."
        return record

    def process_inbox(self, progress_callback=None, limit=None):
        submission_result = {}
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r') as f: submission_result = json.load(f)
            except json.JSONDecodeError: pass

        all_email_files = [f for f in os.listdir(self.inbox_dir) if f.endswith(".json")]
        
        # Filter to only emails we haven't processed yet
        pending_files = [f for f in all_email_files if f.replace(".json", "") not in submission_result]
        
        # Apply the user's limit (e.g., 5 emails)
        if limit is not None and limit != "All":
            pending_files = pending_files[:int(limit)]
            
        total = len(pending_files)
        
        if total == 0:
            if progress_callback: progress_callback(1, 1, "System", "No new emails found.")
            return

        for index, email_file in enumerate(pending_files):
            email_id = email_file.replace(".json", "")

            record = self.process_single_email(email_id)
            submission_result[email_id] = record
            
            with open(self.output_file, "w") as f: json.dump(submission_result, f, indent=4)
            
            if progress_callback: 
                progress_callback(index + 1, total, email_id, record["category"])
            
            # Pacing to avoid API bans
            time.sleep(3)

if __name__ == "__main__":
    system = DocumentVerificationSystem(data_dir="data")
    system.process_inbox()