from hatchify.business.models.messages import MessageTable
from hatchify.business.repositories.message_repository import MessageRepository
from hatchify.business.services.base.generic_service import GenericService


class MessageService(GenericService[MessageTable]):

    def __init__(self):
        super().__init__(MessageTable, MessageRepository)
