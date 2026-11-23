"""Test Gemini with system instruction."""

from google import genai
from config import Config
from services.ai_fill import _load_system_instruction


def main():
    cfg = Config()
    if not cfg.gemini_api_key:
        print("Error: gemini_api_key not set in config.py")
        return

    system = _load_system_instruction(cfg)
    print(f"Category: {cfg.gemini_category}")
    print(f"Model:    {cfg.gemini_model}")
    print(f"System:   {len(system)} chars loaded\n")
    print("--- Sending test message ---\n")

    client = genai.Client(api_key=cfg.gemini_api_key)
    try:
        chat = client.chats.create(
            model=cfg.gemini_model,
            # config={"system_instruction": system},
        )
        resp = chat.send_message("邓紫棋是谁？")
        print(resp.text)
        print("\nOK")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
