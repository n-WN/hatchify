from hatchify.business.models.session import SessionTable
from hatchify.business.repositories.base.generic_repository import GenericRepository


class SessionRepository(GenericRepository[SessionTable]):

    def __init__(self):
        super().__init__(SessionTable)
