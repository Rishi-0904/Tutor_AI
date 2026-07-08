"""
composer.py
-----------
Response Composer Node — assembles markdown blocks (deterministic).

Collects outputs from all agents (visualization, quiz, roadmap, teach-back,
research citations) and formats them into clean, client-renderable markdown.
Pushes blocks to the stream queue and saves the full concatenated result.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.runnables import RunnableConfig
from app.agents.context import AgentContext


def _format_visualization(viz) -> str:
    """Format visualization JSON into frontend custom markdown code blocks."""
    viz_type = viz.viz_type
    data = viz.data
    
    if viz_type == "function_plot":
        return (
            f"\n\n### 📊 Mathematical Function Plot\n"
            f"*(Generating interactive curve grid for expression: `{data.get('expression')}`)*\n"
            f"```visualizer_chart\n"
            f"{json.dumps(data)}\n"
            f"```\n"
        )
    elif viz_type == "flowchart":
        return (
            f"\n\n### 🗺️ Concept Map: {data.get('title', 'Diagram')}\n"
            f"*(Rendering interactive structural map)*\n"
            f"```visualizer_flow\n"
            f"{json.dumps(data)}\n"
            f"```\n"
        )
    elif viz_type == "dp_table":
        return (
            f"\n\n### 📝 Step-by-Step DP Table: {data.get('problem', 'Knapsack')}\n"
            f"*(Interactive calculation grid loaded successfully)*\n"
            f"```visualizer_dp\n"
            f"{json.dumps(data)}\n"
            f"```\n"
        )
    return ""


def _format_quiz(quiz) -> str:
    """Format MCQ quiz questions beautifully."""
    q = quiz.question
    if not q or "question" not in q:
        return ""
        
    quiz_markdown = f"\n\n### 📝 Concept Check\n**{q['question']}**\n"
    options = q.get("options", ["Option A", "Option B", "Option C", "Option D"])
    for idx, opt in enumerate(options):
        letter = chr(65 + idx)
        quiz_markdown += f"- **{letter})** {opt}\n"
    return quiz_markdown


def _format_roadmap(roadmap, subject: str) -> str:
    """Format learning roadmaps."""
    steps = roadmap.steps
    if not steps:
        return ""
        
    roadmap_md = f"\n\n### 🗺️ Your {subject.capitalize()} Study Roadmap\n"
    for s in steps:
        status_icon = "✅" if s.get("status") == "completed" else "⚡" if s.get("status") == "in-progress" else "🔒"
        roadmap_md += f"- **{status_icon} {s.get('topic')}**\n"
    return roadmap_md


def _format_scorecard(tb, subject: str) -> str:
    """Format teach-back scorecards."""
    coverage_bullets = "\n".join(f"  - {c}" for c in tb.coverage) if tb.coverage else "  - None identified."
    missing_bullets = "\n".join(f"  - {m}" for m in tb.missing_concepts) if tb.missing_concepts else "  - No missing concepts! Great job."
    misconception_bullets = "\n".join(f"  - {mis}" for mis in tb.misconceptions) if tb.misconceptions else "  - None detected! Excellent conceptual clarity."
    
    scorecard = (
        f"\n\n### 🎓 Teach-Back Scorecard\n\n"
        f"> **Concept:** *{tb.concept or subject.capitalize()}*\n\n"
        f"| Metric | Rating |\n"
        f"| :--- | :--- |\n"
        f"| **Active Recall Score** | **`{tb.score}/100`** |\n"
        f"| **Explanation Confidence** | `{tb.confidence}` |\n\n"
        f"#### 🔍 Explanation Breakdown\n"
        f"* **✅ Concept Coverage:**\n{coverage_bullets}\n"
        f"* **❌ Missing Points:**\n{missing_bullets}\n"
        f"* **⚠️ Misconceptions Detected:**\n{misconception_bullets}\n\n"
        f"> [!TIP]\n"
        f"> **IIT-JEE Tutor Feedback:**\n"
        f"> {tb.feedback}\n"
    )
    return scorecard


def _clean_response(text: str) -> str:
    """
    Clean up the raw LLM response before delivery.
    - Strips DeepSeek <think>...</think> reasoning tags
    - Removes excessive blank lines
    - Trims leading/trailing whitespace
    """
    import re
    
    # Strip DeepSeek reasoning blocks: <think>...</think>
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Strip any remaining XML-like tags that aren't markdown
    text = re.sub(r'<\/?think>', '', text)
    
    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Trim leading/trailing whitespace
    text = text.strip()
    
    return text


async def composer_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Response Composer.

    Gathers outputs from all processed agents, formats them into a final consolidated
    response, pushes them to the stream queue, and records the final output.
    """
    ctx = AgentContext(**state["context"])
    
    # Load parallel outputs from state if available
    from app.agents.context import ResearchResult, VisualizationResult
    if state.get("research_output"):
        ctx.research = ResearchResult(**state["research_output"])
    if state.get("visual_output"):
        ctx.visualization = VisualizationResult(**state["visual_output"])
        
    queue = config.get("configurable", {}).get("stream_queue")

    composed_parts = []
    
    # 1. Start with the core tutor response (cleaned)
    cleaned_answer = _clean_response(ctx.tutor_answer)
    composed_parts.append(cleaned_answer)

    # 2. Append Visualization
    if ctx.visualization and ctx.visualization.viz_type:
        viz_markdown = _format_visualization(ctx.visualization)
        if viz_markdown:
            composed_parts.append(viz_markdown)
            if queue:
                await queue.put(viz_markdown)

    # 3. Append Quiz
    if ctx.quiz and ctx.quiz.question:
        quiz_markdown = _format_quiz(ctx.quiz)
        if quiz_markdown:
            composed_parts.append(quiz_markdown)
            if queue:
                await queue.put(quiz_markdown)

    # 4. Append Roadmap
    if ctx.roadmap and ctx.roadmap.steps:
        roadmap_markdown = _format_roadmap(ctx.roadmap, ctx.subject)
        if roadmap_markdown:
            composed_parts.append(roadmap_markdown)
            if queue:
                await queue.put(roadmap_markdown)

    # 5. Append Teach-Back Scorecard
    if ctx.teach_back and ctx.teach_back.score > 0:
        scorecard_markdown = _format_scorecard(ctx.teach_back, ctx.subject)
        if scorecard_markdown:
            composed_parts.append(scorecard_markdown)
            if queue:
                await queue.put(scorecard_markdown)

    # Combine into full output
    final_response = "\n".join(composed_parts)
    ctx.metadata["composed_response"] = final_response

    print(f"[Composer] Final response composed. Total length: {len(final_response)}")
    return {"context": ctx.model_dump()}
