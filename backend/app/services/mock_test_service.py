import pandas as pd
import json
import ast
import os
import re

_jee_df = None

def get_mock_test_questions(subject: str, num_questions: int = 10):
    global _jee_df
    
    if _jee_df is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        project_root = os.path.dirname(base_dir)
        csv_path = os.path.join(project_root, "preprocessing", "jee_data_all.csv")
        try:
            print(f"[MockTest] Loading JEE Dataset from {csv_path}...")
            # Load more columns for better context
            _jee_df = pd.read_csv(csv_path, usecols=[
                'question_id', 'subject', 'chapter', 'topic', 
                'question', 'options', 'correct_option', 
                'explanation', 'question_type'
            ])
            _jee_df = _jee_df[_jee_df['question_type'] == 'mcq']
        except Exception as e:
            print(f"Error loading jee dataset: {e}")
            return []
            
    filtered_df = _jee_df[_jee_df['subject'].str.lower() == subject.lower()]
    if filtered_df.empty:
        filtered_df = _jee_df
        
    sampled_df = filtered_df.sample(n=min(num_questions, len(filtered_df)))
    
    questions = []
    for idx, row in sampled_df.iterrows():
        try:
            # Parse options
            opts = row['options']
            try:
                options_raw = json.loads(opts)
            except:
                options_raw = ast.literal_eval(opts)
        except:
            continue
            
        try:
            # Parse correct answer
            corr = row['correct_option']
            try:
                correct_raw = json.loads(corr)[0]
            except:
                try:
                    correct_raw = ast.literal_eval(corr)[0]
                except:
                    correct_raw = str(corr).strip("[]'\"")
        except:
            correct_raw = "A"
            
        parsed_options = [opt['content'] for opt in options_raw]
        idx_map = {"A": 0, "B": 1, "C": 2, "D": 3}
        correct_idx = idx_map.get(correct_raw, 0)
        
        if len(parsed_options) > correct_idx:
            correct_answer = parsed_options[correct_idx]
        else:
            correct_answer = parsed_options[0] if parsed_options else ""

        # Extract image if present in question text
        question_text = str(row['question'])
        image_url = None
        img_match = re.search(r'src="([^"]+)"', question_text)
        if img_match:
            image_url = img_match.group(1)
            # Remove the img tag from text to avoid double rendering if desired, 
            # but usually it's better to keep it or handle it cleanly.
            # We'll extract it to a separate field for the UI to handle properly.

        # Check if diagram might be needed (keywords)
        needs_diagram = False
        if not image_url:
            keywords = ['figure', 'diagram', 'circuit', 'graph', 'shown in', 'plot', 'triangle', 'circle']
            if any(k in question_text.lower() for k in keywords):
                needs_diagram = True
            
        questions.append({
            "id": row['question_id'],
            "subject": row['subject'],
            "chapter": row['chapter'],
            "topic": row['topic'],
            "question": question_text,
            "options": parsed_options,
            "correct_answer": correct_raw, # Return A, B, C, D identifier
            "explanation": row['explanation'] if pd.notna(row['explanation']) else "",
            "image_url": image_url,
            "needs_diagram": needs_diagram
        })
        
    return questions
