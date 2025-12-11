from hatchify.business.models.execution import ExecutionTable
from hatchify.business.repositories.base.generic_repository import GenericRepository


class ExecutionRepository(GenericRepository[ExecutionTable]):

    def __init__(self):
        super().__init__(ExecutionTable)
