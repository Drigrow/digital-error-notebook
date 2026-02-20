import json
import os
import traceback
from flask import current_app
from app.services.openrouter import OpenRouterService
from app.utils.image_utils import resize_image_for_upload, crop_image


DETECTION_PROMPT = """You are analyzing teacher-corrected homework/exam paper images from a Chinese student.

TASK: Detect all WRONG marks (叉, ×, X, or similar marks teachers use to indicate mistakes) in the image(s).

For each detected wrong mark, provide:
1. The bounding box of the question/answer region near the wrong mark (as fractions 0-1 of image dimensions)
2. The OCR text of the student's original question
3. The OCR text of the student's answer (if visible)
4. Whether a teacher's correction/correct answer exists nearby
5. If correction exists, the OCR text of the correction
6. Whether there is a diagram/geometry figure in the region
7. Your confidence score (0-1) for this detection

RESPOND WITH VALID JSON ONLY (no markdown fences). Use this exact schema:
{
  "mistakes": [
    {
      "image_index": 0,
      "bbox": {"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.15},
      "ocr_question": "...",
      "ocr_answer": "...",
      "has_correction": true,
      "correction_text": "...",
      "correction_bbox": {"x": ..., "y": ..., "w": ..., "h": ...},
      "has_diagram": false,
      "diagram_bbox": null,
      "confidence": 0.85
    }
  ]
}

If no mistakes are found, return: {"mistakes": []}
"""

RECONCILIATION_PROMPT = """You are performing a second-pass quality check on OCR results extracted from a teacher-corrected homework paper.

Below is the data extracted from the first pass. The crop image is also provided.

First-pass data:
{first_pass_json}

TASK:
1. Re-examine the crop image carefully.
2. Correct any OCR errors in question text, answer text, or correction text.
3. Verify the status: if a correction exists, status should be SOLVED; otherwise UNSOLVED.
4. Update the confidence score based on your re-examination.
5. If confidence is below 0.6, set needs_user_edit to true.

RESPOND WITH VALID JSON ONLY (no markdown fences):
{{
  "ocr_question": "refined text...",
  "ocr_answer": "refined text or null",
  "correction_text": "refined text or null",
  "status": "SOLVED or UNSOLVED",
  "has_diagram": true/false,
  "confidence": 0.9,
  "needs_user_edit": false
}}
"""


def run_vision_pipeline(image_paths, model, user):
    """
    Main vision pipeline: detection → crop → reconciliation.
    All steps use the same vision model.

    Args:
        image_paths: list of absolute file paths to uploaded images
        model: OpenRouter model ID to use
        user: current User object

    Returns:
        list of mistake item dicts ready for review
    """
    service = OpenRouterService(user=user)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    crop_dir = os.path.join(upload_folder, "crops")
    os.makedirs(crop_dir, exist_ok=True)

    # Step 1: Detection — send all images for analysis
    images_b64 = []
    for path in image_paths:
        full_path = os.path.join(upload_folder, path) if not os.path.isabs(path) else path
        images_b64.append(resize_image_for_upload(full_path))

    try:
        detection_raw = service.vision_completion(images_b64, DETECTION_PROMPT, model=model)
        # Clean response — remove markdown fences if present
        detection_raw = detection_raw.strip()
        if detection_raw.startswith("```"):
            lines = detection_raw.split("\n")
            detection_raw = "\n".join(lines[1:-1])
        detection_result = json.loads(detection_raw)
    except (json.JSONDecodeError, Exception) as e:
        current_app.logger.error(f"Detection failed: {e}\n{traceback.format_exc()}")
        return {"error": f"Detection failed: {str(e)}", "mistakes": []}

    mistakes_raw = detection_result.get("mistakes", [])
    if not mistakes_raw:
        return {"mistakes": [], "message": "No mistakes detected in the uploaded images."}

    # Step 2: Crop images based on bounding boxes
    results = []
    for idx, m in enumerate(mistakes_raw):
        img_index = m.get("image_index", 0)
        if img_index >= len(image_paths):
            img_index = 0

        img_path = image_paths[img_index]
        full_img_path = os.path.join(upload_folder, img_path) if not os.path.isabs(img_path) else img_path

        # Crop question region
        crop_filename = None
        try:
            bbox = m.get("bbox", {})
            if bbox:
                crop_filename = crop_image(full_img_path, bbox, crop_dir)
        except Exception as e:
            current_app.logger.warning(f"Crop failed for mistake {idx}: {e}")

        # Crop correction region if available
        correction_crop = None
        if m.get("has_correction") and m.get("correction_bbox"):
            try:
                correction_crop = crop_image(full_img_path, m["correction_bbox"], crop_dir)
            except Exception:
                pass

        # Crop diagram if detected
        diagram_crop = None
        if m.get("has_diagram") and m.get("diagram_bbox"):
            try:
                diagram_crop = crop_image(full_img_path, m["diagram_bbox"], crop_dir)
            except Exception:
                pass

        item = {
            "index": idx,
            "image_index": img_index,
            "crop_image_path": f"crops/{crop_filename}" if crop_filename else None,
            "correction_image_path": f"crops/{correction_crop}" if correction_crop else None,
            "diagram_image_path": f"crops/{diagram_crop}" if diagram_crop else None,
            "ocr_question": m.get("ocr_question", ""),
            "ocr_answer": m.get("ocr_answer"),
            "correction_text": m.get("correction_text"),
            "status": "SOLVED" if m.get("has_correction") else "UNSOLVED",
            "has_diagram": m.get("has_diagram", False),
            "bbox_json": json.dumps(m.get("bbox", {})),
            "confidence": m.get("confidence", 0.5),
            "needs_user_edit": False,
        }
        results.append(item)

    # Step 3: Reconciliation — second pass on each crop
    for item in results:
        if not item["crop_image_path"]:
            item["needs_user_edit"] = True
            continue

        crop_full_path = os.path.join(upload_folder, item["crop_image_path"])
        if not os.path.exists(crop_full_path):
            item["needs_user_edit"] = True
            continue

        try:
            crop_b64 = resize_image_for_upload(crop_full_path)
            first_pass_data = {
                "ocr_question": item["ocr_question"],
                "ocr_answer": item["ocr_answer"],
                "correction_text": item.get("correction_text"),
                "status": item["status"],
                "has_diagram": item.get("has_diagram", False),
                "confidence": item["confidence"],
            }
            prompt = RECONCILIATION_PROMPT.format(first_pass_json=json.dumps(first_pass_data, ensure_ascii=False))
            recon_raw = service.vision_completion([crop_b64], prompt, model=model)

            recon_raw = recon_raw.strip()
            if recon_raw.startswith("```"):
                lines = recon_raw.split("\n")
                recon_raw = "\n".join(lines[1:-1])
            recon = json.loads(recon_raw)

            # Update item with reconciled data
            item["ocr_question"] = recon.get("ocr_question", item["ocr_question"])
            item["ocr_answer"] = recon.get("ocr_answer", item["ocr_answer"])
            item["correction_text"] = recon.get("correction_text", item.get("correction_text"))
            item["status"] = recon.get("status", item["status"])
            item["confidence"] = recon.get("confidence", item["confidence"])
            item["needs_user_edit"] = recon.get("needs_user_edit", item["confidence"] < 0.6)
            item["has_diagram"] = recon.get("has_diagram", item.get("has_diagram", False))

        except Exception as e:
            current_app.logger.warning(f"Reconciliation failed for item {item['index']}: {e}")
            if item["confidence"] < 0.6:
                item["needs_user_edit"] = True

    return {"mistakes": results}


def suggest_subject_and_tags(mistakes, user):
    """Use the chat model to suggest a subject and tags based on the mistake content."""
    service = OpenRouterService(user=user)

    context = "\n".join([
        f"Question: {m.get('ocr_question', 'N/A')}, Answer: {m.get('ocr_answer', 'N/A')}"
        for m in mistakes
    ])

    prompt = f"""Based on these homework/exam mistake items from a Chinese student, suggest:
1. A subject name (e.g., 数学, 英语, 物理, 化学, 语文, etc.)
2. 3-5 relevant tags (e.g., 二次方程, 几何, 阅读理解, etc.)

Mistake items:
{context}

RESPOND WITH VALID JSON ONLY:
{{"subject": "...", "tags": ["tag1", "tag2", "tag3"]}}
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = service.chat_completion(messages, temperature=0.3, max_tokens=500)
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        return json.loads(response)
    except Exception as e:
        current_app.logger.warning(f"Subject/tag suggestion failed: {e}")
        return {"subject": "", "tags": []}
