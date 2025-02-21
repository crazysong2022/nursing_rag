import pinecone
from models.database import Session
from models.project_models import ConversationHistory
from utils.embeddings import EmbeddingGenerator
import threading

# Initialize Pinecone
pinecone.init(api_key='YOUR_PINECONE_API_KEY', environment='YOUR_PINECONE_ENVIRONMENT')

# Connect to your Pinecone index
index = pinecone.Index("YOUR_PINECONE_INDEX_NAME")

# Initialize the EmbeddingGenerator
embedding_generator = EmbeddingGenerator()

def chunk_and_embed_conversation(conversation_id):
    """
    Chunk the conversation text, generate embeddings, and save them to Pinecone.
    """
    session = Session()
    conversation = session.query(ConversationHistory).get(conversation_id)
    
    # Chunk the conversation text if necessary
    chunks = [conversation.content[i:i+100] for i in range(0, len(conversation.content), 100)]
    
    # Generate embeddings for each chunk
    embeddings = embedding_generator.generate_embeddings(chunks)
    
    # Prepare the vectors to upsert into Pinecone
    vectors = [
        {
            "id": f"{conversation_id}_{i}", 
            "values": embeddings[i], 
            "metadata": {"content": chunk}
        }
        for i, chunk in enumerate(chunks)
    ]
    
    # Upsert the vectors into Pinecone
    index.upsert(vectors=vectors, namespace="ns1")
    
    session.close()

def save_to_vector_db(conversation_id):
    """
    Save the conversation to the vector database asynchronously.
    """
    # Run the chunk and embed process in a separate thread
    thread = threading.Thread(target=chunk_and_embed_conversation, args=(conversation_id,))
    thread.start()