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

        # Ensure RAG components are loaded before proceeding
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
            
            # If session has no title, set it based on the first user message
            if not session.title:
                session.title = user_message_content[:50] + "..." if len(user_message_content) > 50 else user_message_content
                session.save()

            # --- RAG Logic Starts Here ---
            retrieved_context = []
            source_citations = [] # To store details for citations (document_id, filename, etc.)

            try:
                # Get embedding for the user's query
                query_embedding = embedding_model_rag.encode([user_message_content])[0].tolist()
                print(f"RAG Debug: User query: '{user_message_content}'", flush=True)
                print(f"RAG Debug: User query embedding (first 5 values): {query_embedding[:5]}", flush=True)

                # Get IDs of documents owned by the current user for filtering in Pinecone
                relevant_docs_ids = [str(d.id) for d in session.user.documents.all()]
                print(f"RAG Debug: User {session.user.get_username()} (ID: {session.user.id}) has {len(relevant_docs_ids)} documents with IDs: {relevant_docs_ids}", flush=True)
                
                # Search Pinecone for relevant document chunks
                if relevant_docs_ids:
                    pinecone_results = pinecone_index_rag.query(
                        vector=query_embedding,
                        top_k=10, # Retrieve more candidates initially
                        include_metadata=True, # Essential to get original text content and source info
                        filter={
                             "document_id": {"$in": relevant_docs_ids} # Filter by documents owned by the user
                        }
                    )
                    
                    # Filter results by similarity score threshold
                    filtered_matches = [
                        match for match in pinecone_results.get('matches', []) 
                        if match.get('score', 0) > 0.7  # Only keep high-quality matches
                    ]
                    
                    # Limit to top 5 after filtering
                    pinecone_results['matches'] = filtered_matches[:5]
                else:
                    # If the user has no documents uploaded, we should not query Pinecone as it will return empty results and lead to an irrelevant response from the LLM.
                    # Instead, we set an empty matches list to proceed gracefully.
                    print("RAG Debug: No user-owned documents found. Setting Pinecone results to empty.", flush=True)
                    pinecone_results = {'matches': []} 

                print(f"RAG Debug: Pinecone query full response: {pinecone_results.to_dict() if hasattr(pinecone_results, 'to_dict') else pinecone_results}", flush=True)
                print(f"RAG Debug: Pinecone matches found: {len(pinecone_results.get('matches', []))}", flush=True)
                
                # Process Pinecone results to extract context and citations
                for match in pinecone_results['matches']:
                    # Use FULL CONTENT instead of snippet for better context
                    chunk_content = match.get('metadata', {}).get('full_content')
                    if not chunk_content:  # Fallback to snippet if full_content not available
                        chunk_content = match.get('metadata', {}).get('content_snippet')
                    
                    document_id_str = match.get('metadata', {}).get('document_id')
                    filename = match.get('metadata', {}).get('filename')
                    chunk_position = match.get('metadata', {}).get('chunk_position')
                    score = match.get('score') # Similarity score

                    # Only add to context/citations if all required fields are present and chunk_content is not empty
                    if chunk_content and document_id_str and filename and chunk_position is not None and score is not None:
                        retrieved_context.append(chunk_content)
                        source_citations.append({
                            "document_id": document_id_str,
                            "filename": filename,
                            "chunk_position": chunk_position,
                            "score": score
                        })
                        print(f"RAG Debug: Added chunk {chunk_position} from {filename}, score: {score:.3f}, length: {len(chunk_content)} chars", flush=True)
                    else:
                        print(f"RAG Debug: Skipping match due to missing or incomplete metadata fields: {match}", flush=True)

                # If no good matches found with high threshold, try broader search
                if not retrieved_context and relevant_docs_ids:
                    print("RAG Debug: No matches with high threshold, trying broader search...", flush=True)
                    try:
                        broader_results = pinecone_index_rag.query(
                            vector=query_embedding,
                            top_k=10,
                            include_metadata=True,
                            filter={"document_id": {"$in": relevant_docs_ids}}
                        )
                        
                        # Use matches with lower threshold
                        for match in broader_results.get('matches', [])[:3]:
                            if match.get('score', 0) > 0.5:  # Lower threshold for broader search
                                chunk_content = match.get('metadata', {}).get('full_content')
                                if not chunk_content:
                                    chunk_content = match.get('metadata', {}).get('content_snippet')
                                
                                if chunk_content:
                                    retrieved_context.append(chunk_content)
                                    source_citations.append({
                                        "document_id": match.get('metadata', {}).get('document_id'),
                                        "filename": match.get('metadata', {}).get('filename'),
                                        "chunk_position": match.get('metadata', {}).get('chunk_position'),
                                        "score": match.get('score')
                                    })
                                    print(f"RAG Debug: Added broader match, score: {match.get('score', 0):.3f}", flush=True)
                    except Exception as e:
                        print(f"RAG Debug: Broader search failed: {e}", flush=True)

                print(f"RAG Debug: Retrieved context chunks count: {len(retrieved_context)}", flush=True)
                print(f"RAG Debug: Full source_citations list before AI response: {source_citations}", flush=True)

            except Exception as e:
                print(f"RAG Debug: Error during Pinecone retrieval: {e}", flush=True)
                # Reset context and citations if retrieval fails, so LLM doesn't get bad data
                retrieved_context = []
                source_citations = []

            # Construct improved prompt for the LLM
            system_prompt = """You are a helpful AI assistant. Answer the user's question based on the provided context.

Instructions:
- Use the context provided to answer the question thoroughly and comprehensively
- If the context contains relevant information, provide a detailed answer
- If the context doesn't contain enough information, explain what you can determine from the available context and suggest what additional information might be needed
- Always be specific about which parts of the context support your answer
- Synthesize information from multiple context sections if relevant"""

            # Improved context formatting
            context_str = ""
            if retrieved_context:
                for i, context in enumerate(retrieved_context, 1):
                    context_str += f"Context {i} (Score: {source_citations[i-1]['score']:.3f}, Source: {source_citations[i-1]['filename']}):\n{context}\n\n"
            else:
                context_str = "No relevant context found in your uploaded documents."

            prompt = f"""{system_prompt}

{context_str}

User Question: {user_message_content}

Answer:"""
            print(f"RAG Debug: Full prompt sent to LLM (length: {len(prompt)} chars):\n{prompt}", flush=True)

            # Call Gemini API with improved configuration
            gemini_payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,  # Lower temperature for more focused responses
                    "maxOutputTokens": 2048,  # Allow longer responses
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
            }

            full_response_content = "Error: Could not get response from LLM." # Default error message
            try:
                gemini_api_url_with_key = f"{settings.GEMINI_API_BASE_URL}?key={settings.GEMINI_API_KEY}"
                
                gemini_response = requests.post(gemini_api_url_with_key, headers=headers, json=gemini_payload)
                gemini_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                print(f"RAG Debug: Raw Gemini API response text: {gemini_response.text}", flush=True)
                
                response_data = gemini_response.json()
                print(f"RAG Debug: Parsed Gemini API response JSON: {response_data}", flush=True)
                
                # Parse Gemini API response structure: candidates[0].content.parts[0].text
                if response_data and response_data.get('candidates'):
                    first_candidate = response_data['candidates'][0]
                    if first_candidate.get('content') and first_candidate['content'].get('parts'):
                        first_part = first_candidate['content']['parts'][0]
                        full_response_content = first_part.get('text', full_response_content)
                    else:
                        print("RAG Debug: Gemini response format unexpected: missing content or parts.")
                else:
                    print("RAG Debug: Gemini response format unexpected: missing candidates.")
                
                print(f"RAG Debug: Extracted full_response_content: {full_response_content}", flush=True)
                
            except requests.exceptions.RequestException as e:
                print(f"RAG Debug: Error calling Gemini API: Network or HTTP error: {e}", flush=True)
                full_response_content = f"Error communicating with LLM: {e}"
            except json.JSONDecodeError as e:
                print(f"RAG Debug: Error decoding JSON from Gemini API response: {e}. Response: {gemini_response.text}", flush=True)
                full_response_content = f"Error processing LLM response (JSON decode): {e}"
            except Exception as e:
                print(f"RAG Debug: An unexpected error occurred during Gemini API call or parsing: {e}", flush=True)
                full_response_content = f"An unexpected LLM error occurred: {e}"

            # --- RAG Logic Ends Here ---

            ai_response_content = full_response_content # Use the generated LLM response
            
            # 2. Save the AI's response to the database
            ai_chat_message = ChatMessage.objects.create(
                session=session,
                role='ai',
                content=ai_response_content,
                # Store retrieved source citations in the message's metadata
                metadata={'sources': source_citations} if source_citations else {}
            )
            
            # 3. Send the AI's response via Channel Layer for real-time update to frontend
            ai_message_data = ChatMessageSerializer(ai_chat_message).data # Serialize the full message object
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{session_id}',
                {
                    'type': 'chat_message', # This matches the 'type' frontend expects in onmessage
                    'message': ai_message_data # Send full serialized data, including id and timestamp
                }
            )

        # Return an HTTP 201 Created response to the client, confirming message was sent
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

#         # Ensure RAG components are loaded before proceeding
#         if embedding_model_rag is None or pinecone_index_rag is None:
#             return Response(
#                 {'error': 'RAG system not fully initialized. Check backend logs for Pinecone/Embedding model errors.'},
#                 status=status.HTTP_503_SERVICE_UNAVAILABLE
#             )

#         with atomic():
#             # 1. Save the user's message
#             ChatMessage.objects.create(
#                 session=session,
#                 role='user',
#                 content=user_message_content
#             )
            
#             # If session has no title, set it based on the first user message
#             if not session.title:
#                 session.title = user_message_content[:50] + "..." if len(user_message_content) > 50 else user_message_content
#                 session.save()

#             # --- RAG Logic Starts Here ---
#             retrieved_context = []
#             source_citations = [] # To store details for citations (document_id, filename, etc.)

#             try:
#                 # Get embedding for the user's query
#                 query_embedding = embedding_model_rag.encode([user_message_content])[0].tolist()
#                 print(f"RAG Debug: User query embedding (first 5 values): {query_embedding[:5]}", flush=True)

#                 # Get IDs of documents owned by the current user for filtering in Pinecone
#                 relevant_docs_ids = [str(d.id) for d in session.user.documents.all()]
#                 print(f"RAG Debug: User {session.user.get_username()} (ID: {session.user.id}) has documents with IDs: {relevant_docs_ids}", flush=True)
                
#                 # Search Pinecone for relevant document chunks
#                 if relevant_docs_ids:
#                     pinecone_results = pinecone_index_rag.query(
#                         vector=query_embedding,
#                         top_k=5, # Retrieve top 5 most relevant chunks
#                         include_metadata=True, # Essential to get original text content and source info
#                         filter={
#                              "document_id": {"$in": relevant_docs_ids} # Filter by documents owned by the user
#                         }
#                     )
#                 else:
#                     # If the user has no documents uploaded, we should not query Pinecone as it will return empty results and lead to an irrelevant response from the LLM.
#                     # Instead, we set an empty matches list to proceed gracefully.
#                     print("RAG Debug: No user-owned documents found. Setting Pinecone results to empty.", flush=True)
#                     pinecone_results = {'matches': []} 


#                 print(f"RAG Debug: Pinecone query full response: {pinecone_results.to_dict() if hasattr(pinecone_results, 'to_dict') else pinecone_results}", flush=True)
#                 print(f"RAG Debug: Pinecone matches found: {len(pinecone_results.get('matches', []))}", flush=True)
                
#                 # Process Pinecone results to extract context and citations
#                 for match in pinecone_results['matches']:
#                     # Use .get() with a default empty dict to safely access nested metadata
#                     chunk_content = match.get('metadata', {}).get('content_snippet')
#                     document_id_str = match.get('metadata', {}).get('document_id')
#                     filename = match.get('metadata', {}).get('filename')
#                     chunk_position = match.get('metadata', {}).get('chunk_position')
#                     score = match.get('score') # Similarity score

#                     # Only add to context/citations if all required fields are present and chunk_content is not empty
#                     if chunk_content and document_id_str and filename and chunk_position is not None and score is not None:
#                         retrieved_context.append(chunk_content)
#                         source_citations.append({
#                             "document_id": document_id_str,
#                             "filename": filename,
#                             "chunk_position": chunk_position,
#                             "score": score
#                         })
#                     else:
#                         print(f"RAG Debug: Skipping match due to missing or incomplete metadata fields: {match}", flush=True)

#                 print(f"RAG Debug: Retrieved context chunks count: {len(retrieved_context)}", flush=True)
#                 print(f"RAG Debug: Full source_citations list before AI response: {source_citations}", flush=True)


#             except Exception as e:
#                 print(f"RAG Debug: Error during Pinecone retrieval: {e}", flush=True)
#                 # Reset context and citations if retrieval fails, so LLM doesn't get bad data
#                 retrieved_context = []
#                 source_citations = []


#             # Construct prompt for the LLM
#             # Provide clear instructions, context, and the user's question
#             system_prompt = "You are a helpful AI assistant. Answer the user's question based on the provided context only. If the answer is not in the context, state that you don't have enough information."
#             context_str = "\n".join(retrieved_context) if retrieved_context else "No relevant context found."

#             prompt = f"""{system_prompt}

# Context:
# {context_str}

# Question:
# {user_message_content}

# Answer:"""
#             print(f"RAG Debug: Full prompt sent to LLM:\n{prompt}", flush=True)


#             # Call Gemini API
#             gemini_payload = {
#                 "contents": [
#                     {
#                         "parts": [
#                             {"text": prompt}
#                         ]
#                     }
#                 ],
#                 # Optional: Add generationConfig for model behavior control
#                 # "generationConfig": {
#                 #     "temperature": 0.7, # Control randomness (0.0-1.0)
#                 #     "maxOutputTokens": 800, # Max length of the response
#                 # }
#             }
            
#             headers = {
#                 'Content-Type': 'application/json',
#             }

#             full_response_content = "Error: Could not get response from LLM." # Default error message
#             try:
#                 gemini_api_url_with_key = f"{settings.GEMINI_API_BASE_URL}?key={settings.GEMINI_API_KEY}"
                
#                 gemini_response = requests.post(gemini_api_url_with_key, headers=headers, json=gemini_payload)
#                 gemini_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

#                 print(f"RAG Debug: Raw Gemini API response text: {gemini_response.text}", flush=True)
                
#                 response_data = gemini_response.json()
#                 print(f"RAG Debug: Parsed Gemini API response JSON: {response_data}", flush=True)
                
#                 # Parse Gemini API response structure: candidates[0].content.parts[0].text
#                 if response_data and response_data.get('candidates'):
#                     first_candidate = response_data['candidates'][0]
#                     if first_candidate.get('content') and first_candidate['content'].get('parts'):
#                         first_part = first_candidate['content']['parts'][0]
#                         full_response_content = first_part.get('text', full_response_content)
#                     else:
#                         print("RAG Debug: Gemini response format unexpected: missing content or parts.")
#                 else:
#                     print("RAG Debug: Gemini response format unexpected: missing candidates.")
                
#                 print(f"RAG Debug: Extracted full_response_content: {full_response_content}", flush=True)
                
#             except requests.exceptions.RequestException as e:
#                 print(f"RAG Debug: Error calling Gemini API: Network or HTTP error: {e}", flush=True)
#                 full_response_content = f"Error communicating with LLM: {e}"
#             except json.JSONDecodeError as e:
#                 print(f"RAG Debug: Error decoding JSON from Gemini API response: {e}. Response: {gemini_response.text}", flush=True)
#                 full_response_content = f"Error processing LLM response (JSON decode): {e}"
#             except Exception as e:
#                 print(f"RAG Debug: An unexpected error occurred during Gemini API call or parsing: {e}", flush=True)
#                 full_response_content = f"An unexpected LLM error occurred: {e}"

#             # --- RAG Logic Ends Here ---

#             ai_response_content = full_response_content # Use the generated LLM response
            
#             # 2. Save the AI's response to the database
#             ai_chat_message = ChatMessage.objects.create(
#                 session=session,
#                 role='ai',
#                 content=ai_response_content,
#                 # Store retrieved source citations in the message's metadata
#                 metadata={'sources': source_citations} if source_citations else {}
#             )
            
#             # 3. Send the AI's response via Channel Layer for real-time update to frontend
#             ai_message_data = ChatMessageSerializer(ai_chat_message).data # Serialize the full message object
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 f'chat_{session_id}',
#                 {
#                     'type': 'chat_message', # This matches the 'type' frontend expects in onmessage
#                     'message': ai_message_data # Send full serialized data, including id and timestamp
#                 }
#             )

#         # Return an HTTP 201 Created response to the client, confirming message was sent
#         return Response({'status': 'message sent'}, status=status.HTTP_201_CREATED)

# class SendMessageView(generics.CreateAPIView):
#     serializer_class = SendMessageSerializer
#     permission_classes = [IsAuthenticated]

#     def post(self, request, *args, **kwargs):
#         session_id = kwargs['session_id']
#         user_message_content = request.data.get('content')
#         session = get_object_or_404(ChatSession, id=session_id, user=self.request.user)
        
#         if not user_message_content:
#             return Response({'error': 'Message content is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         # Ensure RAG components are loaded
#         if embedding_model_rag is None or pinecone_index_rag is None:
#             return Response(
#                 {'error': 'RAG system not fully initialized. Check backend logs for Pinecone/Embedding model errors.'},
#                 status=status.HTTP_503_SERVICE_UNAVAILABLE
#             )

#         with atomic():
#             # 1. Save the user's message
#             ChatMessage.objects.create(
#                 session=session,
#                 role='user',
#                 content=user_message_content
#             )
            
#             if not session.title:
#                 session.title = user_message_content[:50] + "..." if len(user_message_content) > 50 else user_message_content
#                 session.save()

#             # --- RAG Logic Starts Here ---
#             retrieved_context = []
#             source_citations = [] # To store details for citations

#             try:
#                 # Get embedding for the user's query
#                 query_embedding = embedding_model_rag.encode([user_message_content])[0].tolist()

#                 # Get IDs of documents owned by the user for filtering
#                 relevant_docs_ids = [str(d.id) for d in session.user.documents.all()]
                
#                 # Search Pinecone for relevant document chunks
#                 if relevant_docs_ids:
#                     pinecone_results = pinecone_index_rag.query(
#                         vector=query_embedding,
#                         top_k=5, # Retrieve top 5 relevant chunks
#                         include_metadata=True,
#                         filter={
#                              "document_id": {"$in": relevant_docs_ids}
#                         }
#                     )
#                 else:
                   
#                     pinecone_results = pinecone_index_rag.query(
#                         vector=query_embedding,
#                         top_k=1, # Retrieve top 1 relevant chunk, or adjust
#                         include_metadata=True
#                     )


#                 for match in pinecone_results['matches']:
#                     chunk_content = match['metadata']['content_snippet']
#                     document_id_str = match['metadata'].get('document_id')
#                     filename = match['metadata'].get('filename')
#                     chunk_position = match['metadata'].get('chunk_position')
#                     score = match['score']

#                     if chunk_content:
#                         retrieved_context.append(chunk_content)
#                         source_citations.append({
#                             "document_id": document_id_str,
#                             "filename": filename,
#                             "chunk_position": chunk_position,
#                             "score": score
#                         })
#             except Exception as e:
#                 print(f"Error during Pinecone retrieval: {e}")
#                 # Continue with generic response if retrieval fails
#                 retrieved_context = []
#                 source_citations = []


#             # Construct prompt for the LLM
#             system_prompt = "You are a helpful AI assistant. Answer the user's question based on the provided context only. If the answer is not in the context, state that you don't have enough information."
#             context_str = "\n".join(retrieved_context) if retrieved_context else "No relevant context found."

#             prompt = f"""{system_prompt}

# Context:
# {context_str}

# Question:
# {user_message_content}

# Answer:"""
#             gemini_payload = {
#                 "contents": [
#                     {
#                         "parts": [
#                             {"text": prompt}
#                         ]
#                     }
#                 ],
               
#             }
            
#             headers = {
#                 'Content-Type': 'application/json',
#                 # The API key is added as a query parameter in the URL, not in headers, for Canvas's auto-injection.
#                 # If running outside Canvas, you'd typically use: 'X-goog-api-key': settings.GEMINI_API_KEY
#             }

#             try:
#                 # Use the GEMINI_API_BASE_URL which includes the model and append the API key
#                 gemini_api_url_with_key = f"{settings.GEMINI_API_BASE_URL}?key={settings.GEMINI_API_KEY}"
#                 gemini_response = requests.post(gemini_api_url_with_key, headers=headers, json=gemini_payload)
#                 gemini_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

#                 response_data = gemini_response.json()
                
#                 # Gemini API response structure: candidates[0].content.parts[0].text
#                 full_response_content = "Error: Could not get response from LLM."
#                 if response_data and response_data.get('candidates'):
#                     first_candidate = response_data['candidates'][0]
#                     if first_candidate.get('content') and first_candidate['content'].get('parts'):
#                         first_part = first_candidate['content']['parts'][0]
#                         full_response_content = first_part.get('text', full_response_content)
                
#             except requests.exceptions.RequestException as e:
#                 print(f"Error calling Gemini API: {e}")
#                 full_response_content = f"Error communicating with LLM: {e}"
#             except Exception as e:
#                 print(f"Error parsing Gemini API response: {e}")
#                 full_response_content = f"Error processing LLM response: {e}"

#             # --- RAG Logic Ends Here ---

#             ai_response_content = full_response_content # Use the LLM's response
            
#             # 2. Save the AI's response
#             ai_chat_message = ChatMessage.objects.create(
#                 session=session,
#                 role='ai',
#                 content=ai_response_content,
#                 # Store citations in metadata of AI message if needed
#                 metadata={'sources': source_citations} if source_citations else {}
#             )
            
#             # 3. Send the AI's response via Channel Layer
#             ai_message_data = ChatMessageSerializer(ai_chat_message).data
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 f'chat_{session_id}',
#                 {
#                     'type': 'chat_message',
#                     'message': ai_message_data # Send full serialized data
#                 }
#             )

#         return Response({'status': 'message sent'}, status=status.HTTP_201_CREATED)

