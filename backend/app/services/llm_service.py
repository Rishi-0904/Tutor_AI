import os
import json
import re
import torch
import pickle
from google import genai as google_genai
from app.core.config import settings
from app.services.history_service import HistoryMessage
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# Global singletons — exported so expert_service.py can reuse them
_embedder = None
_router_classifier = None
_tokenizer = None
_peft_model = None
_is_loaded = False

# Shared confidence threshold used by expert_service.py
CONFIDENCE_THRESHOLD = 0.35

SUBJECT_SYSTEM_PROMPTS = {
    "physics": (
        "You are TutorAI, an expert IIT-JEE Physics tutor. "
        "Solve the following problem step-by-step. "
        "You MUST wrap your reasoning inside <think> </think> tags. "
        "You MUST wrap your final answer inside \\boxed{}."
    ),
    "chemistry": (
        "You are TutorAI, an expert IIT-JEE Chemistry tutor. "
        "Solve the following problem step-by-step. "
        "You MUST wrap your reasoning inside <think> </think> tags. "
        "You MUST wrap your final answer inside \\boxed{}."
    ),
    "mathematics": (
        "You are TutorAI, an expert IIT-JEE Mathematics tutor. "
        "Solve the following problem step-by-step. "
        "You MUST wrap your reasoning inside <think> </think> tags. "
        "You MUST wrap your final answer inside \\boxed{}."
    ),
    "general": (
        "You are TutorAI, an expert IIT-JEE tutor. "
        "Solve the following problem step-by-step. "
        "You MUST wrap your reasoning inside <think> </think> tags. "
        "You MUST wrap your final answer inside \\boxed{}."
    ),
}

def load_models():
    """Lazy-load the MoE backend (Base Model + Multiple LoRA Adapters)."""
    global _embedder, _router_classifier, _tokenizer, _peft_model, _is_loaded
    if _is_loaded:
        return True
        
    try:
        print("[MoE] Loading Context-Aware Router...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2", token=settings.hf_token or True)
        
        # Resolve absolute path statically so it never fails based on cwd
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        router_path = os.path.join(base_dir, "minilm_router_brain.pkl")
        
        with open(router_path, "rb") as f:
            _router_classifier = pickle.load(f)
            
        print("[MoE] Loading Base Model (Quantized 4-bit)...")
        # Ensure we use the official model as Unsloth repo's custom code is incompatible with transformers 5.x
        base_name = os.getenv("BASE_MODEL_NAME", "microsoft/Phi-4-mini-instruct")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            llm_int8_enable_fp32_cpu_offload=True
        )
        
        _tokenizer = AutoTokenizer.from_pretrained(base_name, token=settings.hf_token or None)
        if getattr(_tokenizer, "pad_token_id") is None:
            _tokenizer.pad_token_id = _tokenizer.eos_token_id
            
        base_model = AutoModelForCausalLM.from_pretrained(
            base_name,
            quantization_config=bnb_config,
            device_map="auto",
            low_cpu_mem_usage=True,
            token=settings.hf_token or None
        )
        
        print("[MoE] Mounting LoRA Adapters...")
        project_root = os.path.dirname(base_dir)  # tutor_ai_model root
        
        ADAPTER_PATHS = {
            "physics": os.path.join(project_root, "physics_model", "jee-physics-grpo-final"),
            "chemistry": os.path.join(project_root, "chem_model", "grpo_chem", "my_chemistry_lora"),
            "mathematics": os.path.join(project_root, "math_model", "grpo_final_model_updated"),
        }
        
        first_adapter_name = list(ADAPTER_PATHS.keys())[0]
        first_adapter_path = ADAPTER_PATHS[first_adapter_name]
        
        if os.path.exists(first_adapter_path):
            _peft_model = PeftModel.from_pretrained(base_model, first_adapter_path, adapter_name=first_adapter_name, token=settings.hf_token or None)
            for name, path in list(ADAPTER_PATHS.items())[1:]:
                if os.path.exists(path):
                    _peft_model.load_adapter(path, adapter_name=name, token=settings.hf_token or None)
            print("[MoE] All adapters mounted successfully!")
        else:
            print("[MoE] Warning: First adapter missing. Running Base model only.")
            _peft_model = base_model
            
        _is_loaded = True
        return True
    except Exception as e:
        print(f"[MoE] Error initializing models: {e}")
        return False

def route_question(question: str) -> str:
    """Detect subject with keyword heuristic + MiniLM ML fallback."""
    q_lower = question.lower()
    
    # Priority Heuristics for Chemistry
    chem_keywords = [
        'mole', 'compound', 'reaction', 'ph ', 'organic', 'element', 'atom', 'titration', 
        'solvent', 'catalyst', 'ether', 'alcohol', 'chemical', 'oxidation', 'reduction',
        'chiral', 'carbon', 'oxygen', 'reagent', 'hydrolysis', 'picric', 'salicylic',
        'isomers', 'orbital', 'polymer', 'periodic'
    ]
    if any(k in q_lower for k in chem_keywords):
        return "chemistry"
        
    # Priority Heuristics for Physics
    phys_keywords = [
        'velocity', 'acceleration', 'force', 'mass', 'kg ', 'newton', 'joules', 'charge',
        'resistance', 'voltage', 'circuit', 'current', 'capacitor', 'lens', 'mirror',
        'diffraction', 'electron', 'proton', 'magnetic', 'friction', 'momentum',
        'quantum', 'gravity', 'constant'
    ]
    if any(k in q_lower for k in phys_keywords):
        return "physics"

    # Fallback to ML Router
    if _embedder is None or _router_classifier is None:
        return "general"
        
    emb = _embedder.encode([question])
    
    # Handle both raw classifier and dict-wrapped classifier formats
    if isinstance(_router_classifier, dict):
        clf = _router_classifier.get('classifier')
        int_to_subj = _router_classifier.get('int_to_subject', {})
        if clf:
            pred_val = clf.predict(emb)[0]
            pred = int_to_subj.get(pred_val, str(pred_val))
            # Normalize 'maths' to 'mathematics' for adapter mapping
            if pred == 'maths' or pred == 'math':
                pred = 'mathematics'
            return pred
            
    # Legacy raw model format fallback
    pred = _router_classifier.predict(emb)[0]
    return str(pred)

def extract_topic_tags(question: str, answer: str) -> list[str]:
    """Uses Gemini to extract relevant JEE topic tags from the question and answer."""
    api_key = settings.gemini_api_key
    if not api_key:
        return ["jee-topic"]

    try:
        client = google_genai.Client(api_key=api_key)
        prompt = (
            f"Question: {question}\nAnswer: {answer}\n\n"
            "Extract 2-3 specific IIT-JEE topic tags (e.g., 'Rotational Dynamics', 'Organic Chemistry', 'Calculus'). "
            "Return ONLY a comma-separated list of tags."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        if response and response.text:
            return [tag.strip() for tag in response.text.split(",") if tag.strip()]
    except Exception:
        pass
    return ["jee-topic"]


def format_question_latex(question: str) -> str:
    """Uses Gemini to format the raw user question into accurate LaTeX."""
    api_key = settings.gemini_api_key
    if not api_key:
        return question

    try:
        client = google_genai.Client(api_key=api_key)
        sys_prompt = (
            "You are a math and science formatting assistant. "
            "Your ONLY job is to take the provided raw user text/question and format any mathematical, "
            "chemical, or physical formulas, variables, and expressions into perfectly accurate LaTeX. "
            "Do NOT answer the question. Do NOT add any extra conversational text. "
            "Simply output the formatted version of the question. Use $$ for block equations and $ for inline."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{sys_prompt}\n\nUser Question to format:\n{question}"
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"[Gemini] Error formatting question: {e}")

    return question

def process_image_with_gemini(image_bytes: bytes, prompt: str = "Extract the text from this image and format it as LaTeX where necessary.") -> str:
    """Uses Gemini Vision to extract text or analyze an image."""
    api_key = settings.gemini_api_key
    if not api_key:
        return "Error: Gemini API key missing."
    
    try:
        from google.genai import types
        client = google_genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            ]
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini Vision] Error: {e}")
        return f"Error: {str(e)}"

def generate_answer_stream(question: str, history: list[HistoryMessage], subject: str = "general", raw_answer: str = ""):
    """Stream a structured answer using Google's Gemini API based on a raw local answer."""
    api_key = settings.gemini_api_key
    if not api_key:
        yield "System Error: `GEMINI_API_KEY` is not set in `.env`. Please add it and restart the server.\n"
        return

    try:
        client = google_genai.Client(api_key=api_key)
        sys_prompt = (
            "You are a formatting assistant. You will receive a user's question and a raw, unformatted "
            "step-by-step answer generated by a local expert physics/chemistry/math model. "
            "Your ONLY job is to properly format, structure, and render this raw answer using beautiful Markdown and strict LaTeX "
            "(use $$ for block equations and $ for inline). "
            "Clean up and trim any repetitive or redundant lines from the local model, keeping the final output concise and professional. "
            "Do NOT change the underlying technical logic, numbers, or invent new theoretical steps."
        )
        prompt = (
            f"System Guidelines: {sys_prompt}\n\n"
            f"User Question: {question}\n\n"
            f"Raw Unformatted Local Answer:\n{raw_answer}"
        )
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt
        ):
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"\n\nError communicating with Gemini API: {str(e)}\n"

def generate_answer(question: str, history: list[HistoryMessage], subject: str = "general") -> dict:
    if not load_models():
        return {"answer": f"Mock answer to '{question}'. (Models not loaded)", "topic_tags": ["mock"]}
        
    detected_subject = route_question(question)
    print(f"[Router] Swapping Adapter to: {detected_subject}")
    
    if hasattr(_peft_model, "set_adapter"):
        try:
            _peft_model.set_adapter(detected_subject)
        except ValueError:
            pass # fallback to whatever is active
            
    sys_prompt = SUBJECT_SYSTEM_PROMPTS.get(detected_subject, SUBJECT_SYSTEM_PROMPTS["general"])
    prompt = f"System: {sys_prompt}\n"
    for msg in history:
        prompt += f"{msg.role.capitalize()}: {msg.content}\n"
    prompt += f"User: {question}\nAssistant:"
    
    inputs = _tokenizer(prompt, return_tensors="pt").to(_peft_model.device)
    
    with torch.no_grad():
        outputs = _peft_model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.3,
            top_p=0.9,
            pad_token_id=_tokenizer.pad_token_id
        )
        
    ans_text = _tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    return {"answer": ans_text, "topic_tags": extract_topic_tags(question, ans_text)}

def generate_quiz(weak_topics: list[str], subject: str) -> dict:
    if not load_models():
        return {
            "questions": [{
                "id": 1, "question": "Mock Question", "options": ["A", "B", "C", "D"],
                "correct_answer": "A", "explanation": "Mock."
            }]
        }
        
    topics_str = ", ".join(weak_topics) if weak_topics else subject
    
    if hasattr(_peft_model, "set_adapter"):
        try:
            _peft_model.set_adapter(subject.lower())
        except ValueError:
            pass

    prompt = f"""Generate exactly 5 IIT-JEE level multiple choice questions on these {subject} topics: {topics_str}.
Return ONLY a valid JSON object with this exact structure:
{{
  "questions": [
    {{
      "id": 1,
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer": "A",
      "explanation": "..."
    }}
  ]
}}
"""
    inputs = _tokenizer(prompt, return_tensors="pt").to(_peft_model.device)
    with torch.no_grad():
        outputs = _peft_model.generate(**inputs, max_new_tokens=2048, temperature=0.4)
        
    raw = _tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass

    return {
        "questions": [{
            "id": 1, "question": "AI JSON Error", "options": ["A", "B", "C", "D"],
            "correct_answer": "A", "explanation": "Failed to parse generation."
        }]
    }
