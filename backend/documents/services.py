import pinecone
from django.conf import settings

def initialize_pinecone_index():
    pinecone.init(
        api_key=settings.PINECONE_API_KEY,
        environment=settings.PINECONE_ENVIRONMENT
    )
    if settings.PINECONE_INDEX_NAME not in pinecone.list_indexes():
        pinecone.create_index(
            settings.PINECONE_INDEX_NAME, 
            dimension=1536  # Replace with the dimension of your embeddings model
        )
    return pinecone.Index(settings.PINECONE_INDEX_NAME)

def upload_to_pinecone(document_id, text_chunks, embeddings):
    pinecone_index = initialize_pinecone_index()
    vectors_to_upsert = []
    for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
        vectors_to_upsert.append(
            (
                f"{document_id}-{i}",  # Unique ID for the vector
                embedding,
                {'text': chunk, 'document_id': document_id}
            )
        )
    pinecone_index.upsert(vectors=vectors_to_upsert)