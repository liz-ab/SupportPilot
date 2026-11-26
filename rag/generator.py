"""Steps 3 and 4: context augmentation and resolution generation."""
import json
import re
import urllib.request
import config
from models.schemas import Resolution, ResolutionStep

LOW_CONFIDENCE = 0.15   # below this relevance the agent is warned to double-check the steps
STOP = set("the a an and or to of in on for with is are was be it this that my i we you not no at as by from "
           "please can could cannot unable since".split())


def build_context(results):
    """Combine the retrieved articles into one context block for the generator."""
    context = ""
    for doc in results:
        context += f"""
SOURCE: {doc.id}
TITLE: {doc.title}
RELEVANCE: {doc.score:.2f}

{doc.content}

=============================
"""
    return context


def create_prompt(ticket, context):
    return f"""
You are an enterprise IT support assistant.

Your task is to troubleshoot the following support ticket.

TICKET
------
Title:
{ticket.get('title', '')}

Description:
{ticket.get('description', '')}

Priority:
{ticket.get('priority', '')}

KNOWLEDGE BASE
--------------
{context}

INSTRUCTIONS
------------
1. Use the knowledge base as the primary source.
2. Do not invent company-specific policies.
3. Provide numbered troubleshooting steps and end each step with its source id in square brackets, for example [KB001].
4. Explain the likely cause when possible.
5. If the knowledge base does not contain enough information,
   clearly state that additional investigation is required.
6. Keep the response concise and suitable for a support agent.

Generate the recommended resolution.
"""


def _split_article(content):
    steps, intro = [], []
    for line in content.splitlines():
        line = line.strip()
        match = re.match(r"^\d+[.)]\s+(.*)", line)
        if match:
            steps.append(match.group(1).strip())
        elif line:
            intro.append(line)
    return " ".join(intro), steps


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP}


def _format(steps):
    lines = ["Recommended Resolution", ""]
    for step in steps:
        lines.append(f"{step.number}. {step.text}")
        lines.append(f"   Source: {step.source_id} – {step.source_title}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _insufficient():
    return Resolution(
        status="INSUFFICIENT_KNOWLEDGE",
        text="No sufficiently relevant knowledge-base articles were found. Additional investigation "
             "is required; escalate this ticket to the IT support team.",
        summary="No sufficiently relevant knowledge-base articles were found.", escalate=True)


def _needs_escalation(analysis):
    return (analysis.priority == "P1") or (analysis.severity == "Critical")


def generate_from_knowledge(ticket, documents, analysis):
    """Grounded generator: it only reuses steps written in the retrieved articles."""
    if not documents:
        return _insufficient()
    query_words = _words(analysis.query)
    chosen, seen = [], []
    for rank, doc in enumerate(documents):
        intro, steps = _split_article(doc.content)
        if rank == 0:
            picked = steps[:6]
        else:
            if doc.score < 0.8 * documents[0].score:
                continue
            picked = [s for s in steps if len(_words(s) & query_words) >= 2][:3]
        for text in picked:
            words = _words(text)
            if any(len(words & old) / max(1, len(words | old)) > 0.6 for old in seen):
                continue
            seen.append(words)
            chosen.append((text, doc))
        if len(chosen) >= 8:
            break
    if not chosen:
        return _insufficient()
    steps = [ResolutionStep(i, text, doc.id, doc.title) for i, (text, doc) in enumerate(chosen, 1)]
    intro, _ = _split_article(documents[0].content)
    escalate = _needs_escalation(analysis)
    text = _format(steps)
    text += ("\n\nThis is a high-priority ticket. Escalate immediately if these steps do not restore service."
             if escalate else
             "\n\nIf the issue persists, escalate to the IT support team with the steps tried and any "
             "error messages.")
    low_confidence = documents[0].score < LOW_CONFIDENCE
    if low_confidence:
        text += "\n\nNote: the match with the knowledge base is weak. Verify these steps before applying them."
    return Resolution(status="OK", text=text, steps=steps, escalate=escalate, mode="knowledge-base",
                      low_confidence=low_confidence,
                      summary=f"Most relevant guidance: {documents[0].title}. {intro}".strip())


def _call_llm(prompt):
    payload = json.dumps({
        "model": config.LLM_MODEL, "temperature": 0.2,
        "messages": [{"role": "system", "content": "You are an enterprise IT support assistant."},
                     {"role": "user", "content": prompt}]}).encode()
    request = urllib.request.Request(config.LLM_API_URL, data=payload, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {config.LLM_API_KEY}"})
    with urllib.request.urlopen(request, timeout=config.LLM_TIMEOUT) as response:
        return json.loads(response.read())["choices"][0]["message"]["content"]


def generate_with_llm(ticket, documents, analysis, context):
    """Ask the LLM for a resolution; only steps citing a retrieved article are accepted."""
    answer = _call_llm(create_prompt(ticket, context))
    titles = {d.id: d.title for d in documents}
    steps = []
    for line in answer.splitlines():
        match = re.match(r"^\s*\d+[.)]\s+(.*?)\s*\[?(KB[X\d]+)\]?\s*$", line)
        if match and match.group(2) in titles:
            steps.append(ResolutionStep(len(steps) + 1, match.group(1).strip(" -"),
                                        match.group(2), titles[match.group(2)]))
    if not steps:
        raise ValueError("LLM answer had no cited steps")
    escalate = _needs_escalation(analysis)
    return Resolution(status="OK", text=_format(steps), steps=steps, mode="llm", escalate=escalate,
                      summary=f"Generated from {len(documents)} knowledge-base article(s).")


def generate_resolution(ticket, documents, analysis, context=""):
    if not documents:
        return _insufficient()
    if config.LLM_API_KEY:
        try:
            return generate_with_llm(ticket, documents, analysis, context or build_context(documents))
        except Exception:
            pass  # fall back to the grounded generator
    return generate_from_knowledge(ticket, documents, analysis)
