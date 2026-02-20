# Models package — import all models so SQLAlchemy sees them
from app.models.user import User  # noqa
from app.models.note import Note, note_tags  # noqa
from app.models.mistake_item import MistakeItem  # noqa
from app.models.subject import Subject  # noqa
from app.models.tag import Tag  # noqa
from app.models.quiz import QuizSession, QuizQuestion  # noqa
from app.models.chat import ChatThread, ChatMessage  # noqa
from app.models.quota import Quota  # noqa
from app.models.embedding import Embedding  # noqa
