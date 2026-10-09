import os
import time
import random

from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiService:
    """
    Central Gemini AI service for CareerAI.

    Handles:
    - Gemini API connection
    - retries
    - exponential backoff
    - 429 quota errors
    - 503 temporary unavailability
    - automatic fallback models
    """

    def __init__(self):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set in the .env file"
            )

        self.client = genai.Client(
            api_key=api_key
        )

        # Primary model
        self.primary_model = "gemini-3-flash-preview"

        self.fallback_models = [
       "gemini-3.1-flash-lite",
       "gemini-3.5-flash-lite" 
        ]

        # Retry count
        self.max_retries = 2

    def generate(
        self,
        prompt,
        response_mime_type=None
    ):
        """
        Generate content using Gemini with
        automatic retry and model fallback.
        """

        models = [
            self.primary_model,
            *self.fallback_models
        ]

        last_error = None

        for model_index, model in enumerate(models):

            print()
            print(
                f"GEMINI: Selecting model: {model}"
            )

            for attempt in range(self.max_retries):

                try:

                    print(
                        f"GEMINI: Trying model={model}, "
                        f"attempt={attempt + 1}/{self.max_retries}"
                    )

                    config = None

                    if response_mime_type:

                        config = {
                            "response_mime_type":
                                response_mime_type
                        }

                    response = (
                        self.client.models.generate_content(
                            model=model,
                            contents=prompt,
                            config=config
                        )
                    )

                    print(
                        f"GEMINI: SUCCESS using {model}"
                    )

                    return response

                except Exception as e:

                    last_error = e

                    error_text = str(e).lower()

                    print(
                        f"GEMINI ERROR "
                        f"(model={model}): {e}"
                    )

                    # --------------------------------------------------
                    # QUOTA / RATE LIMIT
                    # --------------------------------------------------

                    if (
                        "429" in error_text
                        or "resource_exhausted" in error_text
                        or "quota" in error_text
                    ):

                        print(
                            f"GEMINI: Quota/rate limit detected "
                            f"for {model}."
                        )

                        print(
                            "GEMINI: Moving directly to fallback model."
                        )

                        break

                    # --------------------------------------------------
                    # TEMPORARY SERVER ERROR
                    # --------------------------------------------------

                    if (
                        "503" in error_text
                        or "unavailable" in error_text
                        or "500" in error_text
                        or "internal" in error_text
                        or "504" in error_text
                        or "deadline" in error_text
                    ):

                        if attempt < self.max_retries - 1:

                            delay = (
                                2 ** attempt
                                + random.uniform(0, 0.5)
                            )

                            print(
                                f"GEMINI: Temporary error."
                                f" Waiting {delay:.2f}s..."
                            )

                            time.sleep(delay)

                            continue

                        print(
                            f"GEMINI: {model} unavailable "
                            f"after retries."
                        )

                        break

                    # --------------------------------------------------
                    # PERMANENT ERROR
                    # --------------------------------------------------

                    print(
                        f"GEMINI: Non-retryable error "
                        f"from {model}."
                    )

                    break

            # ----------------------------------------------------------
            # MOVE TO NEXT MODEL
            # ----------------------------------------------------------

            if model_index < len(models) - 1:

                next_model = models[model_index + 1]

                print(
                    f"GEMINI: Falling back from "
                    f"{model} -> {next_model}"
                )

        # --------------------------------------------------------------
        # ALL MODELS FAILED
        # --------------------------------------------------------------

        raise RuntimeError(
            "All configured Gemini models failed. "
            f"Last error: {last_error}"
        )
    def embed(self, text):
        """
        Generate an embedding vector using Gemini's
        dedicated embedding model.

        Used by M2 Job Retrieval / FAISS.
        """

        if not text or not text.strip():
            raise ValueError(
                "Embedding text cannot be empty."
            )

        print(
            "GEMINI: Creating embedding using "
            "gemini-embedding-001"
        )

        response = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config={
                "task_type": "RETRIEVAL_QUERY",
                "output_dimensionality": 768
            }
        )

        print(
            "GEMINI: Embedding created successfully."
        )

        return response