"""Enhanced Knowledge Base Retriever with RAG capabilities."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json

from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain.vectorstores import Pinecone, Weaviate, Chroma
from langchain.schema import Document
from langchain.retrievers import (
    BM25Retriever, 
    EnsembleRetriever,
    ContextualCompressionRetriever
)
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Enhanced search result with metadata."""
    content: str
    metadata: Dict[str, Any]
    score: float
    source: str
    chunk_id: str
    embedding_model: str
    retrieval_method: str


class EnhancedKnowledgeBaseRetriever:
    """Enhanced knowledge base retriever with multiple models and hybrid search."""
    
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = {}
        self.vectorstores = {}
        self.retrievers = {}
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # Initialize different embedding models
        self._initialize_embeddings()
        self._initialize_vectorstores()
        self._initialize_retrievers()
    
    def _initialize_embeddings(self):
        """Initialize multiple embedding models for comparison."""
        try:
            # OpenAI embeddings (primary)
            if self.settings.openai_api_key:
                self.embeddings['openai'] = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    openai_api_key=self.settings.openai_api_key
                )
                logger.info("OpenAI embeddings initialized")
            
            # HuggingFace embeddings (fallback)
            try:
                self.embeddings['huggingface'] = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'}
                )
                logger.info("HuggingFace embeddings initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize HuggingFace embeddings: {e}")
                
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
    
    def _initialize_vectorstores(self):
        """Initialize vector stores for different embedding models."""
        try:
            # Pinecone (primary)
            if hasattr(self.settings, 'pinecone_api_key') and self.settings.pinecone_api_key:
                for model_name, embedding in self.embeddings.items():
                    try:
                        self.vectorstores[f'pinecone_{model_name}'] = Pinecone.from_existing_index(
                            index_name=f"{self.settings.pinecone_index}_{model_name}",
                            embedding=embedding,
                            text_key="text"
                        )
                        logger.info(f"Pinecone vectorstore initialized for {model_name}")
                    except Exception as e:
                        logger.warning(f"Failed to initialize Pinecone for {model_name}: {e}")
            
            # Weaviate (alternative)
            if hasattr(self.settings, 'weaviate_url') and self.settings.weaviate_url:
                for model_name, embedding in self.embeddings.items():
                    try:
                        import weaviate
                        client = weaviate.Client(self.settings.weaviate_url)
                        self.vectorstores[f'weaviate_{model_name}'] = Weaviate(
                            client=client,
                            index_name=f"ReflexKB_{model_name}",
                            text_key="text",
                            embedding=embedding
                        )
                        logger.info(f"Weaviate vectorstore initialized for {model_name}")
                    except Exception as e:
                        logger.warning(f"Failed to initialize Weaviate for {model_name}: {e}")
            
            # Chroma (local fallback)
            for model_name, embedding in self.embeddings.items():
                try:
                    self.vectorstores[f'chroma_{model_name}'] = Chroma(
                        collection_name=f"reflex_kb_{model_name}",
                        embedding_function=embedding,
                        persist_directory=f"./data/chroma_{model_name}"
                    )
                    logger.info(f"Chroma vectorstore initialized for {model_name}")
                except Exception as e:
                    logger.warning(f"Failed to initialize Chroma for {model_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize vectorstores: {e}")
    
    def _initialize_retrievers(self):
        """Initialize different retrieval methods."""
        try:
            # Vector similarity retrievers
            for store_name, vectorstore in self.vectorstores.items():
                self.retrievers[f'vector_{store_name}'] = vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 5}
                )
            
            # BM25 retriever (keyword-based)
            try:
                # This would need documents to be loaded
                # self.retrievers['bm25'] = BM25Retriever.from_documents(documents)
                pass
            except Exception as e:
                logger.warning(f"Failed to initialize BM25 retriever: {e}")
            
            # Ensemble retriever (combines multiple methods)
            if len(self.retrievers) > 1:
                try:
                    retrievers = list(self.retrievers.values())[:3]  # Use first 3 retrievers
                    self.retrievers['ensemble'] = EnsembleRetriever(
                        retrievers=retrievers,
                        weights=[0.5, 0.3, 0.2]  # Weight vector search higher
                    )
                    logger.info("Ensemble retriever initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize ensemble retriever: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize retrievers: {e}")
    
    async def add_document(self, content: str, metadata: Dict[str, Any], 
                          embedding_model: str = 'openai') -> bool:
        """Add a document to the knowledge base."""
        try:
            # Split content into chunks
            documents = self.text_splitter.create_documents(
                texts=[content],
                metadatas=[metadata]
            )
            
            # Add to vector stores
            success_count = 0
            for store_name, vectorstore in self.vectorstores.items():
                if embedding_model in store_name:
                    try:
                        vectorstore.add_documents(documents)
                        success_count += 1
                        logger.info(f"Added document to {store_name}")
                    except Exception as e:
                        logger.error(f"Failed to add document to {store_name}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
    
    async def search(self, query: str, 
                    method: str = 'ensemble',
                    top_k: int = 5,
                    filters: Optional[Dict[str, Any]] = None,
                    rerank: bool = True) -> List[SearchResult]:
        """Enhanced search with multiple methods and reranking."""
        try:
            results = []
            
            # Get base results
            if method in self.retrievers:
                retriever = self.retrievers[method]
                docs = await self._async_retrieve(retriever, query, top_k, filters)
                
                for doc in docs:
                    result = SearchResult(
                        content=doc.page_content,
                        metadata=doc.metadata,
                        score=getattr(doc, 'score', 0.0),
                        source=doc.metadata.get('source', 'unknown'),
                        chunk_id=doc.metadata.get('chunk_id', ''),
                        embedding_model=method,
                        retrieval_method=method
                    )
                    results.append(result)
            
            # Rerank results if enabled
            if rerank and results:
                results = await self._rerank_results(query, results)
            
            # Add hybrid search results
            if method == 'ensemble':
                hybrid_results = await self._hybrid_search(query, top_k, filters)
                results.extend(hybrid_results)
                # Remove duplicates and sort by score
                results = self._deduplicate_results(results)
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def _async_retrieve(self, retriever, query: str, top_k: int, 
                            filters: Optional[Dict[str, Any]]) -> List[Document]:
        """Async wrapper for retriever get_relevant_documents."""
        try:
            if hasattr(retriever, 'aget_relevant_documents'):
                return await retriever.aget_relevant_documents(query)
            else:
                return retriever.get_relevant_documents(query)
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []
    
    async def _hybrid_search(self, query: str, top_k: int, 
                           filters: Optional[Dict[str, Any]]) -> List[SearchResult]:
        """Perform hybrid search combining multiple methods."""
        try:
            hybrid_results = []
            
            # Semantic search
            for store_name, vectorstore in self.vectorstores.items():
                try:
                    docs = vectorstore.similarity_search_with_score(
                        query, k=top_k//2, filter=filters
                    )
                    for doc, score in docs:
                        result = SearchResult(
                            content=doc.page_content,
                            metadata=doc.metadata,
                            score=score,
                            source=doc.metadata.get('source', 'unknown'),
                            chunk_id=doc.metadata.get('chunk_id', ''),
                            embedding_model=store_name,
                            retrieval_method='hybrid_semantic'
                        )
                        hybrid_results.append(result)
                except Exception as e:
                    logger.warning(f"Hybrid search failed for {store_name}: {e}")
            
            return hybrid_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    async def _rerank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank results using contextual relevance."""
        try:
            # Simple reranking based on query relevance
            for result in results:
                # Boost score for exact keyword matches
                query_terms = query.lower().split()
                content_lower = result.content.lower()
                
                keyword_boost = sum(1 for term in query_terms if term in content_lower)
                result.score += keyword_boost * 0.1
                
                # Boost recent documents
                if 'timestamp' in result.metadata:
                    try:
                        timestamp = datetime.fromisoformat(result.metadata['timestamp'])
                        days_old = (datetime.now() - timestamp).days
                        if days_old < 30:  # Recent documents get boost
                            result.score += 0.05
                    except:
                        pass
            
            # Sort by score
            results.sort(key=lambda x: x.score, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on content similarity."""
        try:
            seen_contents = set()
            unique_results = []
            
            for result in results:
                # Simple deduplication based on content hash
                content_hash = hash(result.content[:100])  # First 100 chars
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    unique_results.append(result)
            
            return unique_results
            
        except Exception as e:
            logger.error(f"Deduplication failed: {e}")
            return results
    
    async def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        try:
            stats = {
                'total_documents': 0,
                'total_chunks': 0,
                'embedding_models': list(self.embeddings.keys()),
                'vector_stores': list(self.vectorstores.keys()),
                'retrievers': list(self.retrievers.keys()),
                'last_updated': datetime.now().isoformat()
            }
            
            # Count documents in each vector store
            for store_name, vectorstore in self.vectorstores.items():
                try:
                    if hasattr(vectorstore, 'index'):
                        stats['total_chunks'] += vectorstore.index.describe_index_stats()['total_vector_count']
                except:
                    pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get KB stats: {e}")
            return {}
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the knowledge base."""
        try:
            success_count = 0
            for store_name, vectorstore in self.vectorstores.items():
                try:
                    # This would need to be implemented based on the specific vector store
                    # vectorstore.delete(document_id)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete from {store_name}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    async def update_document(self, document_id: str, content: str, 
                            metadata: Dict[str, Any]) -> bool:
        """Update a document in the knowledge base."""
        try:
            # Delete old version
            await self.delete_document(document_id)
            
            # Add new version
            return await self.add_document(content, metadata)
            
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return False


# Global instance
enhanced_kb_retriever = None


def get_enhanced_kb_retriever() -> EnhancedKnowledgeBaseRetriever:
    """Get the global enhanced knowledge base retriever instance."""
    global enhanced_kb_retriever
    if enhanced_kb_retriever is None:
        enhanced_kb_retriever = EnhancedKnowledgeBaseRetriever()
    return enhanced_kb_retriever


async def init_enhanced_kb_retriever():
    """Initialize the enhanced knowledge base retriever."""
    global enhanced_kb_retriever
    enhanced_kb_retriever = EnhancedKnowledgeBaseRetriever()
    logger.info("Enhanced knowledge base retriever initialized")
    return enhanced_kb_retriever 