# backend/chat/views.py

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer, SendMessageSerializer
from django.shortcuts import get_object_or_404
from django.db.transaction import atomic
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import requests 
import json
from pinecone import Pinecone, PodSpec
from sentence_transformers import SentenceTransformer 
from django.conf import settings 

embedding_model_rag = None
pinecone_index_rag = None
pc = None # New Pinecone client instance

try:
    embedding_model_rag = SentenceTransformer('all-MiniLM-L6-v2')
    print("RAG: SentenceTransformer model 'all-MiniLM-L6-v2' loaded for query embedding.")
except Exception as e:
    print(f"RAG: Error loading SentenceTransformer model: {e}")

try:
    # Initialize Pinecone using the new client instantiation
    # Use PodSpec if your index is not serverless, otherwise use ServerlessSpec
    pc = Pinecone(
        api_key=settings.PINECONE_API_KEY,
        environment=settings.PINECONE_ENVIRONMENT
    )
    # Access the index via the Pinecone client instance
    pinecone_index_rag = pc.Index(settings.PINECONE_INDEX_NAME)
    print(f"RAG: Pinecone initialized and connected to index: {settings.PINECONE_INDEX_NAME}")
except Exception as e:
    print(f"RAG: Error initializing Pinecone: {e}")
    pc = None # Set to None if initialization fails
    pinecone_index_rag = None # Set to None if initialization fails

# --- End Global Initialization ---


class ChatSessionCreateView(generics.CreateAPIView):
    queryset = ChatSession.objects.all()
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ChatMessagesListView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs['session_id']
        session = get_object_or_404(ChatSession, id=session_id, user=self.request.user)
        return ChatMessage.objects.filter(session=session).order_by('timestamp')
    
class ChatSessionListView(generics.ListAPIView):
    """
    API endpoint for listing all chat sessions for the authenticated user.
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This method ensures a user can only see their own chat sessions.
        """
        return ChatSession.objects.filter(user=self.request.user).order_by('-created_at')

class SendMessageView(generics.CreateAPIView):
    serializer_class = SendMessageSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        session_id = kwargs['session_id']
        user_message_content = request.data.get('content')
        session = get_object_or_404(ChatSession, id=session_id, user=self.request.user)
        
        if not user_message_content:
            return Response({'error': 'Message content is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure RAG components are loaded
        if embedding_model_rag is None or pinecone_index_rag is None:
            return Response(
                {'error': 'RAG system not fully initialized. Check backend logs for Pinecone/Embedding model errors.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        with atomic():
            # 1. Save the user's message
            ChatMessage.objects.create(
                session=session,
                role='user',
                content=user_message_content
            )
            
            if not session.title:
                session.title = user_message_content[:50] + "..." if len(user_message_content) > 50 else user_message_content
                session.save()

            # --- RAG Logic Starts Here ---
            retrieved_context = []
            source_citations = [] # To store details for citations

            try:
                # Get embedding for the user's query
                query_embedding = embedding_model_rag.encode([user_message_content])[0].tolist()

                # Get IDs of documents owned by the user for filtering
                relevant_docs_ids = [str(d.id) for d in session.user.documents.all()]
                
                # Search Pinecone for relevant document chunks
                if relevant_docs_ids:
                    pinecone_results = pinecone_index_rag.query(
                        vector=query_embedding,
                        top_k=5, # Retrieve top 5 relevant chunks
                        include_metadata=True,
                        filter={
                             "document_id": {"$in": relevant_docs_ids}
                        }
                    )
                else:
                   
                    pinecone_results = pinecone_index_rag.query(
                        vector=query_embedding,
                        top_k=1, # Retrieve top 1 relevant chunk, or adjust
                        include_metadata=True
                    )


                for match in pinecone_results['matches']:
                    chunk_content = match['metadata']['content_snippet']
                    document_id_str = match['metadata'].get('document_id')
                    filename = match['metadata'].get('filename')
                    chunk_position = match['metadata'].get('chunk_position')
                    score = match['score']

                    if chunk_content:
                        retrieved_context.append(chunk_content)
                        source_citations.append({
                            "document_id": document_id_str,
                            "filename": filename,
                            "chunk_position": chunk_position,
                            "score": score
                        })
            except Exception as e:
                print(f"Error during Pinecone retrieval: {e}")
                # Continue with generic response if retrieval fails
                retrieved_context = []
                source_citations = []


            # Construct prompt for the LLM
            system_prompt = "You are a helpful AI assistant. Answer the user's question based on the provided context only. If the answer is not in the context, state that you don't have enough information."
            context_str = "\n".join(retrieved_context) if retrieved_context else "No relevant context found."

            prompt = f"""{system_prompt}

Context:
{context_str}

Question:
{user_message_content}

Answer:"""
            gemini_payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
               
            }
            
            headers = {
                'Content-Type': 'application/json',
                # The API key is added as a query parameter in the URL, not in headers, for Canvas's auto-injection.
                # If running outside Canvas, you'd typically use: 'X-goog-api-key': settings.GEMINI_API_KEY
            }

            try:
                # Use the GEMINI_API_BASE_URL which includes the model and append the API key
                gemini_api_url_with_key = f"{settings.GEMINI_API_BASE_URL}?key={settings.GEMINI_API_KEY}"
                gemini_response = requests.post(gemini_api_url_with_key, headers=headers, json=gemini_payload)
                gemini_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                response_data = gemini_response.json()
                
                # Gemini API response structure: candidates[0].content.parts[0].text
                full_response_content = "Error: Could not get response from LLM."
                if response_data and response_data.get('candidates'):
                    first_candidate = response_data['candidates'][0]
                    if first_candidate.get('content') and first_candidate['content'].get('parts'):
                        first_part = first_candidate['content']['parts'][0]
                        full_response_content = first_part.get('text', full_response_content)
                
            except requests.exceptions.RequestException as e:
                print(f"Error calling Gemini API: {e}")
                full_response_content = f"Error communicating with LLM: {e}"
            except Exception as e:
                print(f"Error parsing Gemini API response: {e}")
                full_response_content = f"Error processing LLM response: {e}"

            # --- RAG Logic Ends Here ---

            ai_response_content = full_response_content # Use the LLM's response
            
            # 2. Save the AI's response
            ai_chat_message = ChatMessage.objects.create(
                session=session,
                role='ai',
                content=ai_response_content,
                # Store citations in metadata of AI message if needed
                metadata={'sources': source_citations} if source_citations else {}
            )
            
            # 3. Send the AI's response via Channel Layer
            ai_message_data = ChatMessageSerializer(ai_chat_message).data
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{session_id}',
                {
                    'type': 'chat_message',
                    'message': ai_message_data # Send full serialized data
                }
            )

        return Response({'status': 'message sent'}, status=status.HTTP_201_CREATED)

# class SendMessageView(generics.CreateAPIView):
#     serializer_class = SendMessageSerializer
#     permission_classes = [IsAuthenticated]

#     def post(self, request, *args, **kwargs):
#         session_id = kwargs['session_id']
#         user_message_content = request.data.get('content')
#         session = get_object_or_404(ChatSession, id=session_id, user=self.request.user)
        
#         if not user_message_content:
#             return Response({'error': 'Message content is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         with atomic():
#             # 1. Save the user's message
#             ChatMessage.objects.create(
#                 session=session,
#                 role='user',
#                 content=user_message_content
#             )
            
#             if not session.title:
#                 # Use the first 50 characters of the user's message as a simple title
#                 session.title = user_message_content[:50] + "..." if len(user_message_content) > 50 else user_message_content
#                 session.save()

#             # 2. Placeholder for RAG logic
#             #    - Determine if user_message_content needs a search
#             #    - Get embeddings for the query
#             #    - Search Pinecone for relevant document chunks
#             #    - Construct a prompt for the LLM
#             #    - Get the AI response

#             ai_response_content = "This is a placeholder AI response." # Replace with actual AI response
#             ai_chat_message = ChatMessage.objects.create( # Store the created object
#                 session=session,
#                 role='ai',
#                 content=ai_response_content
#             )
#             # 3. Save the AI's response
#             # ChatMessage.objects.create(
#             #     session=session,
#             #     role='ai',
#             #     content=ai_response_content
#             # )
#             ai_message_data = ChatMessageSerializer(ai_chat_message).data
#             channel_layer = get_channel_layer()
#             # async_to_sync(channel_layer.group_send)(
#             #     f'chat_{session_id}',
#             #     {
#             #         'type': 'chat_message',
#             #         'message': {
#             #             'content': ai_response_content,
#             #             'role': 'ai'
#             #         }
#             #     }
#             # )
#             print(ai_message_data, flush=True)
#             async_to_sync(channel_layer.group_send)(
#                 f'chat_{session_id}',
#                 {
#                     'type': 'chat_message',
#                     'message': ai_message_data # Send full serialized data, including id and timestamp
#                 }
#             )

#         return Response({'status': 'message sent'}, status=status.HTTP_201_CREATED)