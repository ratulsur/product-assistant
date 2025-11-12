import os
import sys
import asyncio
from dotenv import load_dotenv

# --- Internal imports (corrected paths) ---
from product_assistant.logger.custom_logger import CustomLogger
from product_assistant.utils.config_loader import load_config
from product_assistant.exception.custom_exception import ProductAssistantException

# --- External dependencies ---
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

# -----------------------------------------------------------------------------
# SETUP
# -----------------------------------------------------------------------------
load_dotenv()
log = CustomLogger().get_logger(__name__)

# -----------------------------------------------------------------------------
# API KEY MANAGER
# -----------------------------------------------------------------------------
class ApiKeyManager:
    def __init__(self):
        self.api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        }

        for key, val in self.api_keys.items():
            if val:
                log.info(f"{key} loaded successfully")
            else:
                log.warning(f"{key} is missing in environment")

    def get(self, key: str):
        return self.api_keys.get(key)


# -----------------------------------------------------------------------------
# MODEL LOADER
# -----------------------------------------------------------------------------
class ModelLoader:
    def __init__(self):
        try:
            self.api_mgr = ApiKeyManager()
            self.config = load_config()
            log.info("Configuration loaded successfully")
        except Exception as e:
            log.error(f"Error during ModelLoader init: {e}")
            raise ProductAssistantException("ModelLoader initialization failed", e)

    # ------------------------------
    def load_embeddings(self):
        try:
            emb_conf = self.config.get("embedding_model", {})
            model_name = emb_conf.get("model_name")

            if not model_name:
                raise ProductAssistantException("Missing embedding_model.model_name", sys)

            log.info(f"Loading Embedding Model: {model_name}")

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

            google_key = self.api_mgr.get("GOOGLE_API_KEY")
            if not google_key:
                raise ProductAssistantException("GOOGLE_API_KEY not found", sys)

            return GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=google_key)

        except Exception as e:
            log.error(f"Failed to load embeddings: {e}")
            raise ProductAssistantException("Failed to load embedding model", e)

    # ------------------------------
    def load_llm(self):
        try:
            llm_cfg = self.config.get("llm", {}).get("openai", {})
            model_name = llm_cfg.get("model_name", "gpt-4o-mini")
            temperature = llm_cfg.get("temperature", 0.2)

            log.info(f"Loading LLM model: {model_name}")

            openai_key = self.api_mgr.get("OPENAI_API_KEY")
            if not openai_key:
                raise ProductAssistantException("OPENAI_API_KEY not found", sys)

            return ChatOpenAI(model=model_name, api_key=openai_key, temperature=temperature)

        except Exception as e:
            log.error(f"Failed to load LLM: {e}")
            raise ProductAssistantException("Failed to load LLM", e)


# -----------------------------------------------------------------------------
# MAIN TEST BLOCK
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        loader = ModelLoader()

        # Test Embeddings
        embeddings = loader.load_embeddings()
        print("✅ Embedding model loaded:", embeddings)

        vec = embeddings.embed_query("Hello world!")
        print("✅ Embedding vector length:", len(vec))

        # Test LLM
        llm = loader.load_llm()
        print("✅ LLM loaded:", llm)

        res = llm.invoke("Say hello in one line.")
        print("✅ LLM Response:", getattr(res, "content", res))

    except Exception as e:
        log.error(f"Fatal error in ModelLoader: {e}")
        raise
