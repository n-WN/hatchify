from app.business.models.agent import AgentTable
from app.business.repositories.agent_repository import AgentRepository
from app.business.services.base.generic_service import GenericService


class AgentService(GenericService[AgentTable]):
    def __init__(self):
        super().__init__(AgentTable, AgentRepository)
