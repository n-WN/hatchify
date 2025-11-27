from app.business.models.agent import AgentTable
from app.business.repositories.base.generic_repository import GenericRepository


class AgentRepository(GenericRepository[AgentTable]):
    def __init__(self):
        super().__init__(AgentTable)