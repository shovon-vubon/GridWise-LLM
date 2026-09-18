import os

from dotenv import load_dotenv


load_dotenv()


class Settings:

    # Groq
    GROQ_API_KEY = os.getenv(
        "GROQ_API_KEY",
        ""
    )

    GROQ_MODEL = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile"
    )


    # Gemini
    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        ""
    )

    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )


settings = Settings()