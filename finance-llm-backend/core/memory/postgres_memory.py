"""PostgreSQL-based chat history management."""

import uuid
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

from config import config
from core.utils.logger import setup_logger

logger = setup_logger(__name__)


class PostgresChatMemory:
    """Manages chat sessions and messages in PostgreSQL."""

    def __init__(self):
        """Initialize PostgreSQL chat memory."""
        self.connection_string = config.get_db_connection_string()

    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(self.connection_string)

    def create_chat_session(self, title: Optional[str] = None) -> str:
        """
        Create a new chat session.

        Args:
            title: Optional title for the chat session

        Returns:
            chat_id: UUID string of the created session
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO chat_sessions (title)
                    VALUES (%s)
                    RETURNING chat_id
                """, (title,))
                chat_id = cursor.fetchone()[0]
                conn.commit()
                logger.info(f"Created new chat session: {chat_id}")
                return str(chat_id)
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating chat session: {e}")
            raise
        finally:
            conn.close()

    def get_all_chat_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all chat sessions ordered by most recent.

        Returns:
            List of chat sessions with metadata
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        cs.chat_id,
                        cs.title,
                        cs.created_at,
                        cs.updated_at,
                        COUNT(cm.id) as message_count,
                        MAX(cm.created_at) as last_message_at
                    FROM chat_sessions cs
                    LEFT JOIN chat_messages cm ON cs.chat_id = cm.chat_id
                    GROUP BY cs.chat_id, cs.title, cs.created_at, cs.updated_at
                    ORDER BY cs.updated_at DESC
                """)
                sessions = cursor.fetchall()

                # Convert to list of dicts with proper serialization
                result = []
                for session in sessions:
                    result.append({
                        'chat_id': str(session['chat_id']),
                        'title': session['title'],
                        'created_at': session['created_at'].isoformat() if session['created_at'] else None,
                        'updated_at': session['updated_at'].isoformat() if session['updated_at'] else None,
                        'message_count': session['message_count'],
                        'last_message_at': session['last_message_at'].isoformat() if session['last_message_at'] else None
                    })

                return result
        except Exception as e:
            logger.error(f"Error getting chat sessions: {e}")
            raise
        finally:
            conn.close()

    def get_chat_session(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific chat session with its messages.

        Args:
            chat_id: UUID string of the chat session

        Returns:
            Chat session with messages, or None if not found
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get session info
                cursor.execute("""
                    SELECT chat_id, title, created_at, updated_at
                    FROM chat_sessions
                    WHERE chat_id = %s
                """, (chat_id,))
                session = cursor.fetchone()

                if not session:
                    return None

                # Get messages
                cursor.execute("""
                    SELECT id, role, content, sources, created_at
                    FROM chat_messages
                    WHERE chat_id = %s
                    ORDER BY created_at ASC
                """, (chat_id,))
                messages = cursor.fetchall()

                return {
                    'chat_id': str(session['chat_id']),
                    'title': session['title'],
                    'created_at': session['created_at'].isoformat() if session['created_at'] else None,
                    'updated_at': session['updated_at'].isoformat() if session['updated_at'] else None,
                    'messages': [
                        {
                            'id': msg['id'],
                            'role': msg['role'],
                            'content': msg['content'],
                            'sources': msg['sources'],
                            'created_at': msg['created_at'].isoformat() if msg['created_at'] else None
                        }
                        for msg in messages
                    ]
                }
        except Exception as e:
            logger.error(f"Error getting chat session {chat_id}: {e}")
            raise
        finally:
            conn.close()

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """
        Add a message to a chat session.

        Args:
            chat_id: UUID string of the chat session
            role: 'user' or 'assistant'
            content: Message content
            sources: Optional list of source documents

        Returns:
            message_id: ID of the created message
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Import json for serialization
                import json
                sources_json = json.dumps(sources) if sources else None

                cursor.execute("""
                    INSERT INTO chat_messages (chat_id, role, content, sources)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (chat_id, role, content, sources_json))
                message_id = cursor.fetchone()[0]
                conn.commit()
                logger.debug(f"Added {role} message to chat {chat_id}")
                return message_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding message to chat {chat_id}: {e}")
            raise
        finally:
            conn.close()

    def update_chat_title(self, chat_id: str, title: str) -> bool:
        """
        Update the title of a chat session.

        Args:
            chat_id: UUID string of the chat session
            title: New title

        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE chat_sessions
                    SET title = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = %s
                """, (title, chat_id))
                conn.commit()
                logger.info(f"Updated title for chat {chat_id}")
                return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating chat title: {e}")
            return False
        finally:
            conn.close()

    def delete_chat_session(self, chat_id: str) -> bool:
        """
        Delete a chat session and all its messages.

        Args:
            chat_id: UUID string of the chat session

        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM chat_sessions
                    WHERE chat_id = %s
                """, (chat_id,))
                deleted = cursor.rowcount > 0
                conn.commit()
                if deleted:
                    logger.info(f"Deleted chat session: {chat_id}")
                else:
                    logger.warning(f"Chat session not found: {chat_id}")
                return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting chat session: {e}")
            raise
        finally:
            conn.close()

    def delete_all_chat_sessions(self) -> int:
        """
        Delete all chat sessions.

        Returns:
            Number of sessions deleted
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM chat_sessions")
                count = cursor.fetchone()[0]

                cursor.execute("DELETE FROM chat_sessions")
                conn.commit()
                logger.info(f"Deleted all {count} chat sessions")
                return count
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting all chat sessions: {e}")
            raise
        finally:
            conn.close()

    def get_chat_history(self, chat_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get chat history for a session in the format expected by LLM.

        Args:
            chat_id: UUID string of the chat session
            limit: Optional limit on number of messages to retrieve

        Returns:
            List of messages in format [{"role": "user", "content": "..."}, ...]
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                    SELECT role, content
                    FROM chat_messages
                    WHERE chat_id = %s
                    ORDER BY created_at ASC
                """

                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query, (chat_id,))
                messages = cursor.fetchall()

                return [
                    {
                        'role': msg['role'],
                        'content': msg['content']
                    }
                    for msg in messages
                ]
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
        finally:
            conn.close()
