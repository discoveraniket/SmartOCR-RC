import logging

logger = logging.getLogger(__name__)

def save_to_file(text: str, output_path: str):
    """Saves the text to a file (overwrites)."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"File saved successfully to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save file {output_path}: {e}")

def append_llm_result(output_path: str, result: dict):
    """Appends LLM results (reasoning and answer) to the file."""
    try:
        with open(output_path, "a", encoding="utf-8") as f:
            f.write("\n" + "="*30 + "")
            f.write("LLM DATA CLEANING RESULT")
            f.write("="*30 + "\n")
            if result.get('thinking'):
                f.write(f"REASONING:{result['thinking']}")
            f.write(f"FINAL ANSWER:{result['answer']}")
        logger.info(f"LLM results appended to {output_path}")
    except Exception as e:
        logger.error(f"Failed to append LLM results to {output_path}: {e}")
