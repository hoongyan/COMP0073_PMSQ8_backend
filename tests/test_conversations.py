import pytest
from fastapi import status
import datetime
from sqlalchemy.exc import SQLAlchemyError
from app.main import app
from src.models.data_model import Conversations, Messages, SenderRole, UserRole, Users  
from app.dependencies.roles import admin_role  
from app.model import ConversationListResponse 

@pytest.mark.parametrize(
    "mock_conversations, expected_status, expected_count, expected_detail",
    [
        # Case 1: Conversations found
        ([
            Conversations(
                conversation_id=1,
                creation_datetime=datetime.datetime.fromisoformat("2023-01-01T00:00:00"),
                report_id=None,
                messages=[
                    Messages(
                        message_id=1,
                        sender_role=SenderRole.human,
                        content="Hello",
                        sent_datetime=datetime.datetime.fromisoformat("2023-01-01T00:00:00")
                    )
                ]
            )
        ], status.HTTP_200_OK, 1, None),
        # Case 2: No conversations
        ([], status.HTTP_200_OK, 0, None),
        # Case 3: DB failure
        (None, status.HTTP_500_INTERNAL_SERVER_ERROR, None, "Database error during read: DB error"),
    ]
)
def test_get_conversations_endpoint(client, mocker, mock_db, mock_conversations, expected_status, expected_count, expected_detail):
    """Test /conversations/ GET endpoint for listing conversations."""
    # Mock admin role 
    mock_user = Users(role=UserRole.admin)
    app.dependency_overrides[admin_role] = lambda db=None, current_user=None: mock_user

    if mock_conversations is None:
        mock_db.query.side_effect = SQLAlchemyError("DB error")
    else:
        mock_query_chain = mock_db.query.return_value.options.return_value.order_by.return_value.offset.return_value.limit.return_value.all
        mock_query_chain.return_value = mock_conversations

    response = client.get("/conversations/")
    assert response.status_code == expected_status
    if expected_status == status.HTTP_200_OK:
        json_response = response.json()
        assert len(json_response["conversations"]) == expected_count
        if expected_count > 0:
            conv = json_response["conversations"][0]
            assert "conversationId" in conv and conv["conversationId"] == "1"
            assert "reportId" in conv and conv["reportId"] is None
            assert "creationDate" in conv and len(conv["creationDate"]) == 14  # 'dd/mm/yy HH:MM'
            assert "messages" in conv and len(conv["messages"]) == 1
            assert "summary" in conv and "Hello" in conv["summary"]
            msg = conv["messages"][0]
            assert msg["senderRole"] == "HUMAN"
            assert len(msg["sentDate"]) == 14
    else:
        assert response.json()["detail"] == expected_detail

@pytest.mark.parametrize(
    "conversation_id, mock_delete_result, expected_status, expected_detail",
    [
        # Case 1: Delete success
        (1, 1, status.HTTP_204_NO_CONTENT, None),
        # Case 2: Not found
        (999, 0, status.HTTP_404_NOT_FOUND, "Conversation with ID 999 not found"),
        # Case 3: DB failure
        (1, None, status.HTTP_500_INTERNAL_SERVER_ERROR, "Database error during delete: DB error"),
    ]
)
def test_delete_conversation_endpoint(client, mocker, mock_db, conversation_id, mock_delete_result, expected_status, expected_detail):
    """Test /conversations/{id} DELETE endpoint."""
    # Mock admin role
    mock_user = Users(role=UserRole.admin)
    app.dependency_overrides[admin_role] = lambda db=None, current_user=None: mock_user

    mock_query = mocker.MagicMock()
    mock_filter = mocker.MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    if mock_delete_result is None:
        mock_filter.delete.side_effect = SQLAlchemyError("DB error")
    else:
        mock_filter.delete.return_value = mock_delete_result
    mock_db.commit.return_value = None

    response = client.delete(f"/conversations/{conversation_id}")
    assert response.status_code == expected_status
    if expected_status != status.HTTP_204_NO_CONTENT:
        json_response = response.json()
        assert json_response["detail"] == expected_detail.replace("999", str(conversation_id))  # Dynamic ID for detail; for 500, no replace needed but harmless