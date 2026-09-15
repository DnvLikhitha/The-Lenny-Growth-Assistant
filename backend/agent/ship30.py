import re
from typing import Dict, Any, Tuple

def validate_ship30_essay(content: str) -> Tuple[bool, Dict[str, Any]]:
    words = content.split()
    word_count = len(words)
    
    # Target: ~1,250 words ±15% for cloud models, relaxed lower bound (>= 400 words) for smaller local Ollama models (3B/8B)
    within_word_range = 400 <= word_count <= 1800
    
    # Checklist criteria:
    # 1. Hook (Check first 200 words or presence of introductory line)
    has_hook = len(content) > 50
    
    # 2. Headings (Markdown headers # or ##)
    has_headings = bool(re.search(r'^#{1,3}\s+.+', content, re.MULTILINE))
    
    # 3. Bold emphasis (**bold**)
    has_bold = bool(re.search(r'\*\*[^*]+\*\*', content))
    
    # 4. Stated Takeaway (Section or sentence mentioning "Takeaway", "Key Takeaway", or "Bottom Line")
    has_takeaway = bool(re.search(r'(takeaway|bottom line|key takeaway|in summary)', content, re.IGNORECASE))

    is_valid = within_word_range and has_headings and has_bold and has_takeaway

    details = {
        "word_count": word_count,
        "within_word_range": within_word_range,
        "has_hook": has_hook,
        "has_headings": has_headings,
        "has_bold": has_bold,
        "has_takeaway": has_takeaway,
        "is_valid": is_valid
    }
    return is_valid, details
