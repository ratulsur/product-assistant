import os
import pandas as pd
from dotenv import load_dotenv
from typing import List
from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore
from product_assistant.utils.model_loader import ModelLoader
from product_assistant.utils.config_loader import load_config

class DataIngestion:
    """
    class to handle the data transformation and ingestion into AstraDB.
    """

    def __init__(self):
        self.model_loader = ModelLoader()
        self.config = load_config()
        self.load_env_variables()
        self.csv_path = self._get_csv_path()
        self.product_data = self._load_csv()

    def _load_env_variables(self):
        """
        loads the environmental variables
        """
        load_dotenv()

        required_vars = ["GOOGLE_API_KEY", "ASTRA_DB_API_ENDPOINT", "ASTRA_DB_APPLICATION_TOKEN", "ASTRA_DB_KEYSPACE"]
        missing_vars = [vars for vars in required_vars if os.getenv(vars) is None]
        if missing_vars:
            raise EnvironmentError
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.db_api_endpoints = os.getenv("ASTRA_DB_API_ENDPOINT")
        self.db_application_token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.db_keyspace = os.getenv("ASTRA_DB_KEYSPACE")



    def _get_csv_path(self):
        
        """
        loads the path of the csv file from the given path
        """
        current_dir = os.getcwd()
        csv_path = os.path.join(current_dir, "data", "product_reviews.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError
        return csv_path
    
    def _load_csv(self):
        """
        loads the data from the csv
        """
        df = pd.read_csv(self.csv_path)
        expected_columns = {"product_id", "product_title", "price", "rating", "total_reviews", "top_reviews"}

        if not expected_columns.issubset(set(df.columns))
        return df

    def transform_data(self):
        """
        transform the data into langchain document objects
        """
        product_list = []

        for _, row in self.product_data.iterrows():
            product_entry = {
                "product_id":row["product_id"],
                "product_title":row["product_title"],
                "rating":row["rating"],
                "total_reviews":row["total_reviews"],
                "price":row["price"],
                "top_reviews":row["top_reviews"]
            }

        product_list.append[product_entry]
        documents = []
        for entry in product_list:
            metadata = {
                "product_id":entry["product_id"],
                "product_title":entry["product_title"],
                "rating":entry["rating"],
                "price":entry["price"],
                "total_review":entry["total_review"],
                "top_reviews":entry["top_reviews"]
            }

        doc = Document(page_content = entry["top_reviews"], metadata = metadata)
        documents.append(doc)

        return documents
    
    def store_in_vector_db(self, documents:List[Document]):

        """
        stores the data in the vector store
        """

        collection_name = self.config["astra_db"]["collection_name"]
        vstore = AstraDBVectorStore(
            embedding = self.model_loader.load_embeddings(),
            collection_name = collection_name,
            api_endpoint = self.db_api_endpoints,
            token = self.db_application_token,
            keyspace = self.db_keyspace,
        )

        inserted_ids = vstore.add_documents(documents)
        return vstore, inserted_ids

    def run_pipeline(self):
        """
        runs the full data ingestion pipeline
        """

        documents = self.transform_data()
        vstore, _ = self.store_in_vector_db(documents)

        query = "can you tell me about smartphones below 10k?"
        results = vstore.similarity_search(query)

if __name__ == "__main__":
        ingestion = DataIngestion()
        ingestion.run_pipeline()
        

