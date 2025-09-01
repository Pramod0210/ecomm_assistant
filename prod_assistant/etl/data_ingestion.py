import os
import pandas as pd
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore
from prod_assistant.utils.config_loader import load_config
from prod_assistant.utils.model_loader import ModelLoader

class DataIngestion:
    """
    Class for ingesting data from various sources and storing it in a vector store.
    """
    def __init__(self):
        pass

    def _load_env_variables(self):
        if os.getenv("ENV", "local").lower() != "production":
            load_dotenv()
            log.info("Running in LOCAL mode: .env loaded")
        else:
            log.info("Running in PRODUCTION mode")
    
    def _get_csv_path(self):
        pass

    def _load_csv(self):
        pass

    def transform_data(self):
        pass

    def store_in_vector_db(self):
        pass

    