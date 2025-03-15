import logging
from datetime import datetime
import json
import os
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import faiss
from sqlalchemy import create_engine, Column, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pickle

Base = declarative_base()

class Document(Base):
    """SQLite model for storing document metadata"""
    __tablename__ = 'documents'
    
    id = Column(String, primary_key=True)
    data_type = Column(String, nullable=False)
    doc_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class VectorStore:
    """Vector database using FAISS for storing and retrieving scraped renewable energy data"""
    
    def __init__(self):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize SQLite database
        db_path = os.path.join(os.getcwd(), "data", "vector_store", "metadata.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize FAISS indices
        self.indices = {}
        self.index_paths = {
            "eia": os.path.join(os.getcwd(), "data", "vector_store", "eia.index"),
            "solar": os.path.join(os.getcwd(), "data", "vector_store", "solar.index"),
            "wind": os.path.join(os.getcwd(), "data", "vector_store", "wind.index")
        }
        
        # Load or create FAISS indices
        for data_type, path in self.index_paths.items():
            if os.path.exists(path):
                self.indices[data_type] = faiss.read_index(path)
                self.logger.info(f"Loaded existing FAISS index for {data_type}")
            else:
                # Create a new L2 index
                self.indices[data_type] = faiss.IndexFlatL2(384)  # 384 is the dimension of all-MiniLM-L6-v2 embeddings
                self.logger.info(f"Created new FAISS index for {data_type}")
        
        # Initialize sentence transformer model
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            self.logger.error(f"Error loading sentence transformer model: {e}")
            raise

    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embeddings for input text."""
        try:
            embedding = self.model.encode(text)
            return embedding.astype(np.float32)  # FAISS requires float32
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            raise

    def _prepare_document(self, data: Dict[str, Any]) -> str:
        """Convert data dictionary to a text document for embedding."""
        try:
            return json.dumps(data, sort_keys=True, default=str)
        except Exception as e:
            self.logger.error(f"Error preparing document: {e}")
            raise

    def store_data(self, data: Dict[str, Any], data_type: str) -> bool:
        """Store data in FAISS index and SQLite database."""
        try:
            # Prepare document and generate embedding
            doc_text = self._prepare_document(data)
            embedding = self._generate_embedding(doc_text)
            
            # Add to FAISS index
            self.indices[data_type].add(embedding.reshape(1, -1))
            
            # Save index to disk
            faiss.write_index(self.indices[data_type], self.index_paths[data_type])
            
            # Store metadata in SQLite
            doc_id = f"{data_type}_{datetime.now().isoformat()}"
            with self.Session() as session:
                doc = Document(
                    id=doc_id,
                    data_type=data_type,
                    doc_metadata=data
                )
                session.add(doc)
                session.commit()
            
            self.logger.info(f"Successfully stored {data_type} data with ID: {doc_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error storing data: {e}")
            return False

    def query_data(self, query: str, data_type: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query the vector store for similar data."""
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Search FAISS index
            D, I = self.indices[data_type].search(
                query_embedding.reshape(1, -1),
                n_results
            )
            
            # Get metadata from SQLite
            with self.Session() as session:
                # Get all documents of this type
                docs = session.query(Document).filter_by(data_type=data_type).all()
                # Sort by similarity scores
                results = []
                for idx, score in zip(I[0], D[0]):
                    if idx < len(docs):  # Make sure we have metadata for this index
                        doc = docs[idx]
                        result = doc.doc_metadata.copy()
                        result['similarity_score'] = float(score)
                        results.append(result)
            
            return results
        except Exception as e:
            self.logger.error(f"Error querying data: {e}")
            return []

    def get_similar_data(self, data: Dict[str, Any], data_type: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Find similar data points to the input data."""
        try:
            query_doc = self._prepare_document(data)
            return self.query_data(query_doc, data_type, n_results)
        except Exception as e:
            self.logger.error(f"Error finding similar data: {e}")
            return [] 