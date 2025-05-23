import os
import anthropic
import datetime
from dotenv import load_dotenv

load_dotenv()
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

LOG_PATH = "claude_debug_logs.txt"

def log_claude_interaction(prompt, system_msg, response):
    if not response:  # Only log failures or empty returns
        timestamp = datetime.datetime.now().isoformat()
        with open(LOG_PATH, "a") as f:
            f.write(f"\n=== {timestamp} ===\n")
            f.write(f"System: {system_msg}\n")
            f.write(f"Prompt: {prompt}\n")
            f.write(f"Response: [NO RESPONSE]\n")
            f.write("=" * 40 + "\n")

def call_claude(prompt: str, model="claude-3-7-sonnet-20250219", system_msg=None, max_tokens=8000, temperature=0.7, log_on_empty=True):
    try:
        message = claude.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_msg or "You are a helpful writing assistant for seasonal home and yard content.",
            messages=[{"role": "user", "content": prompt}]
        )
        if not message.content:
            if log_on_empty:
                log_claude_interaction(prompt, system_msg, None)
            return None

        return message.content[0].text.strip()

    except Exception as e:
        if log_on_empty:
            log_claude_interaction(prompt, system_msg, f"[EXCEPTION] {e}")
        return None