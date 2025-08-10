from django.urls import path
from . import consumers
from.views import SendMessageView, ChatSessionCreateView, ChatMessagesListView, ChatSessionListView

websocket_urlpatterns = [
    path('ws/chat/<int:session_id>/', consumers.ChatConsumer.as_asgi()),
]

urlpatterns = [
    path('sessions/', ChatSessionListView.as_view(), name='chat-session-list'), # Add this line
    path('sessions/create/', ChatSessionCreateView.as_view(), name='chat-session-create'),
    path('sessions/<int:session_id>/send/', SendMessageView.as_view(), name='send_message'),
    path('sessions/<int:session_id>/messages/', ChatMessagesListView.as_view(), name='list_messages'),
]
