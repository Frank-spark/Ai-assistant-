"""Knowledge Base Retriever for Reflex Executive Assistant."""

import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import asyncio

from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers import VectorStoreRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever

from ..config import get_settings
from ..storage.db import get_db_session
from ..storage.models import KnowledgeDocument, DocumentChunk, DocumentSource

logger = logging.getLogger(__name__)


class KnowledgeBaseRetriever:
    """Knowledge base retriever for company context and information."""
    
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=self.settings.openai_api_key,
            model=self.settings.openai_embedding_model
        )
        
        # Initialize vector store
        self.vector_store = None
        self.retriever = None
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.kb_chunk_size,
            chunk_overlap=self.settings.kb_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize company context cache
        self._company_context_cache = {}
        self._cache_expiry = {}
        self._cache_ttl = timedelta(hours=1)
        
        logger.info("KnowledgeBaseRetriever initialized")
    
    async def initialize(self) -> None:
        """Initialize the vector store and retriever."""
        try:
            if self.settings.vector_db_type == "pinecone":
                await self._initialize_pinecone()
            elif self.settings.vector_db_type == "weaviate":
                await self._initialize_weaviate()
            elif self.settings.vector_db_type == "milvus":
                await self._initialize_milvus()
            else:
                logger.warning(f"Unsupported vector DB type: {self.settings.vector_db_type}")
                return
            
            # Initialize retriever
            if self.vector_store:
                self.retriever = VectorStoreRetriever(
                    vectorstore=self.vector_store,
                    search_type="similarity",
                    search_kwargs={"k": self.settings.kb_search_k}
                )
                
                # Use multi-query retriever for better results
                self.retriever = MultiQueryRetriever.from_llm(
                    retriever=self.retriever,
                    llm=None  # Will use default OpenAI model
                )
                
                logger.info("Knowledge base retriever initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}", exc_info=True)
    
    async def _initialize_pinecone(self) -> None:
        """Initialize Pinecone vector store."""
        try:
            import pinecone
            
            # Initialize Pinecone
            pinecone.init(
                api_key=self.settings.pinecone_api_key,
                environment=self.settings.pinecone_environment
            )
            
            # Get or create index
            index_name = self.settings.pinecone_index_name
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=self.settings.openai_embedding_dimension,
                    metric="cosine"
                )
            
            # Connect to index
            index = pinecone.Index(index_name)
            
            # Create vector store
            self.vector_store = Pinecone(
                index=index,
                embedding_function=self.embeddings.embed_query,
                text_key="text"
            )
            
            logger.info(f"Pinecone vector store initialized with index: {index_name}")
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone: {e}", exc_info=True)
            raise
    
    async def _initialize_weaviate(self) -> None:
        """Initialize Weaviate vector store."""
        try:
            from langchain.vectorstores import Weaviate
            
            # TODO: Implement Weaviate initialization
            logger.info("Weaviate initialization not yet implemented")
            
        except Exception as e:
            logger.error(f"Error initializing Weaviate: {e}", exc_info=True)
            raise
    
    async def _initialize_milvus(self) -> None:
        """Initialize Milvus vector store."""
        try:
            from langchain.vectorstores import Milvus
            
            # TODO: Implement Milvus initialization
            logger.info("Milvus initialization not yet implemented")
            
        except Exception as e:
            logger.error(f"Error initializing Milvus: {e}", exc_info=True)
            raise
    
    async def add_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        source_type: str = "manual",
        source_id: Optional[str] = None
    ) -> str:
        """Add a document to the knowledge base."""
        try:
            # Split content into chunks
            chunks = self.text_splitter.split_text(content)
            
            # Store document in database
            db_session = get_db_session()
            
            # Create source record
            source = DocumentSource(
                type=source_type,
                source_id=source_id,
                created_at=datetime.utcnow()
            )
            db_session.add(source)
            db_session.commit()
            
            # Create main document record
            doc = KnowledgeDocument(
                title=metadata.get("title", "Untitled"),
                content=content,
                source_id=source.id,
                metadata=metadata,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db_session.add(doc)
            db_session.commit()
            
            # Create chunk records and add to vector store
            documents = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    **metadata,
                    "document_id": doc.id,
                    "source_id": source.id,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                
                # Store chunk in database
                chunk_record = DocumentChunk(
                    document_id=doc.id,
                    content=chunk,
                    chunk_index=i,
                    metadata=chunk_metadata
                )
                db_session.add(chunk_record)
                
                # Prepare for vector store
                documents.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))
            
            db_session.commit()
            
            # Add to vector store
            if self.vector_store:
                await self._add_documents_to_vector_store(documents)
            
            logger.info(f"Added document '{doc.title}' with {len(chunks)} chunks")
            return str(doc.id)
            
        except Exception as e:
            logger.error(f"Error adding document: {e}", exc_info=True)
            raise
    
    async def _add_documents_to_vector_store(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        try:
            if self.vector_store:
                # Add documents in batches
                batch_size = 100
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    await self.vector_store.aadd_documents(batch)
                
                logger.info(f"Added {len(documents)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}", exc_info=True)
            raise
    
    async def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Retrieve relevant documents for a query."""
        try:
            if not self.retriever:
                logger.warning("Retriever not initialized, returning empty results")
                return []
            
            # Set search parameters
            search_k = k or self.settings.kb_search_k
            
            # Perform retrieval
            if filter_metadata:
                # Apply metadata filters
                docs = await self.retriever.aget_relevant_documents(
                    query,
                    k=search_k
                )
                # Filter by metadata (basic implementation)
                filtered_docs = [
                    doc for doc in docs
                    if all(
                        doc.metadata.get(key) == value
                        for key, value in filter_metadata.items()
                    )
                ]
                return filtered_docs[:search_k]
            else:
                docs = await self.retriever.aget_relevant_documents(
                    query,
                    k=search_k
                )
                return docs
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}", exc_info=True)
            return []
    
    async def get_company_context(self, query: str) -> str:
        """Get company context for a specific query."""
        try:
            # Check cache first
            cache_key = query.lower().strip()
            if cache_key in self._company_context_cache:
                if datetime.utcnow() < self._cache_expiry.get(cache_key, datetime.min):
                    return self._company_context_cache[cache_key]
                else:
                    # Remove expired cache entry
                    del self._company_context_cache[cache_key]
                    del self._cache_expiry[cache_key]
            
            # Retrieve relevant documents
            docs = await self.retrieve(query, k=5)
            
            if not docs:
                return "No relevant company context found for this query."
            
            # Build context from retrieved documents
            context_parts = []
            for doc in docs:
                title = doc.metadata.get("title", "Unknown")
                content = doc.page_content[:500]  # Limit content length
                context_parts.append(f"From '{title}': {content}")
            
            context = "\n\n".join(context_parts)
            
            # Cache the result
            self._company_context_cache[cache_key] = context
            self._cache_expiry[cache_key] = datetime.utcnow() + self._cache_ttl
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting company context: {e}", exc_info=True)
            return "Company context unavailable."
    
    async def get_policy_guidance(self, topic: str) -> str:
        """Get policy guidance for a specific topic."""
        try:
            # Search for policy-related documents
            policy_query = f"policy {topic} guidelines rules"
            docs = await self.retrieve(policy_query, k=3)
            
            if not docs:
                return f"No specific policy guidance found for '{topic}'."
            
            # Extract policy information
            policy_info = []
            for doc in docs:
                if "policy" in doc.metadata.get("title", "").lower():
                    policy_info.append(f"Policy: {doc.page_content[:300]}")
                elif "guideline" in doc.metadata.get("title", "").lower():
                    policy_info.append(f"Guideline: {doc.page_content[:300]}")
            
            if policy_info:
                return "\n\n".join(policy_info)
            else:
                return f"No specific policy guidance found for '{topic}'."
            
        except Exception as e:
            logger.error(f"Error getting policy guidance: {e}", exc_info=True)
            return "Policy guidance unavailable."
    
    async def get_company_overview(self) -> str:
        """Get a general company overview."""
        try:
            # Check cache
            cache_key = "company_overview"
            if cache_key in self._company_context_cache:
                if datetime.utcnow() < self._cache_expiry.get(cache_key, datetime.min):
                    return self._company_context_cache[cache_key]
            
            # Search for company overview documents
            docs = await self.retrieve("company overview mission vision values", k=3)
            
            if not docs:
                return "Company overview information not available."
            
            # Build overview
            overview_parts = []
            for doc in docs:
                if any(keyword in doc.metadata.get("title", "").lower() 
                      for keyword in ["overview", "mission", "vision", "about"]):
                    overview_parts.append(doc.page_content[:400])
            
            if overview_parts:
                overview = "\n\n".join(overview_parts)
                
                # Cache the result
                self._company_context_cache[cache_key] = overview
                self._cache_expiry[cache_key] = datetime.utcnow() + self._cache_ttl
                
                return overview
            else:
                return "Company overview information not available."
            
        except Exception as e:
            logger.error(f"Error getting company overview: {e}", exc_info=True)
            return "Company overview unavailable."
    
    async def search_documents(
        self,
        query: str,
        source_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search documents with advanced filtering."""
        try:
            db_session = get_db_session()
            
            # Build query
            query_obj = db_session.query(KnowledgeDocument)
            
            if source_type:
                query_obj = query_obj.join(DocumentSource).filter(
                    DocumentSource.type == source_type
                )
            
            if date_from:
                query_obj = query_obj.filter(
                    KnowledgeDocument.created_at >= date_from
                )
            
            if date_to:
                query_obj = query_obj.filter(
                    KnowledgeDocument.created_at <= date_to
                )
            
            # Add text search if query provided
            if query:
                query_obj = query_obj.filter(
                    KnowledgeDocument.content.ilike(f"%{query}%")
                )
            
            # Execute query
            documents = query_obj.order_by(
                KnowledgeDocument.updated_at.desc()
            ).limit(limit).all()
            
            # Format results
            results = []
            for doc in documents:
                results.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                    "source_type": doc.source.type if doc.source else None,
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat(),
                    "metadata": doc.metadata
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}", exc_info=True)
            return []
    
    async def update_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update an existing document."""
        try:
            db_session = get_db_session()
            
            # Get document
            doc = db_session.query(KnowledgeDocument).filter(
                KnowledgeDocument.id == document_id
            ).first()
            
            if not doc:
                logger.warning(f"Document {document_id} not found")
                return False
            
            # Update content and metadata
            doc.content = content
            if metadata:
                doc.metadata.update(metadata)
            doc.updated_at = datetime.utcnow()
            
            # Remove old chunks
            db_session.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            
            # Create new chunks
            chunks = self.text_splitter.split_text(content)
            documents = []
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    **doc.metadata,
                    "document_id": doc.id,
                    "source_id": doc.source_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                
                # Store chunk in database
                chunk_record = DocumentChunk(
                    document_id=doc.id,
                    content=chunk,
                    chunk_index=i,
                    metadata=chunk_metadata
                )
                db_session.add(chunk_record)
                
                # Prepare for vector store
                documents.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))
            
            db_session.commit()
            
            # Update vector store
            if self.vector_store:
                # Remove old vectors and add new ones
                # Note: This is a simplified approach - in production you might want
                # to use vector store specific update methods
                await self._add_documents_to_vector_store(documents)
            
            logger.info(f"Updated document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document: {e}", exc_info=True)
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the knowledge base."""
        try:
            db_session = get_db_session()
            
            # Get document
            doc = db_session.query(KnowledgeDocument).filter(
                KnowledgeDocument.id == document_id
            ).first()
            
            if not doc:
                logger.warning(f"Document {document_id} not found")
                return False
            
            # Remove chunks
            db_session.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            
            # Remove document
            db_session.delete(doc)
            db_session.commit()
            
            # Note: Vector store cleanup would need to be implemented
            # based on the specific vector store being used
            
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}", exc_info=True)
            return False
    
    async def get_document_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        try:
            db_session = get_db_session()
            
            # Count documents
            total_docs = db_session.query(KnowledgeDocument).count()
            
            # Count chunks
            total_chunks = db_session.query(DocumentChunk).count()
            
            # Count sources
            total_sources = db_session.query(DocumentSource).count()
            
            # Get recent activity
            recent_docs = db_session.query(KnowledgeDocument).filter(
                KnowledgeDocument.updated_at >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            return {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "total_sources": total_sources,
                "recent_activity_7d": recent_docs,
                "vector_store_initialized": self.vector_store is not None,
                "retriever_initialized": self.retriever is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting document stats: {e}", exc_info=True)
            return {}
    
    async def clear_cache(self) -> None:
        """Clear the company context cache."""
        self._company_context_cache.clear()
        self._cache_expiry.clear()
        logger.info("Knowledge base cache cleared")


# Global instance
_kb_retriever_instance = None


def get_kb_retriever() -> KnowledgeBaseRetriever:
    """Get the global knowledge base retriever instance."""
    global _kb_retriever_instance
    if _kb_retriever_instance is None:
        _kb_retriever_instance = KnowledgeBaseRetriever()
    return _kb_retriever_instance


async def initialize_kb_retriever() -> None:
    """Initialize the global knowledge base retriever."""
    retriever = get_kb_retriever()
    await retriever.initialize() 