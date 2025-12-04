from hatchify.business.models.session import SessionTable
from hatchify.business.repositories.session_repository import SessionRepository
from hatchify.business.services.base.generic_service import GenericService


class SessionService(GenericService[SessionTable]):

    def __init__(self):
        super().__init__(SessionTable, SessionRepository)
