from app.business.models.graph import GraphTable
from app.business.repositories.base.generic_repository import GenericRepository


class GraphRepository(GenericRepository[GraphTable]):

    def __init__(self):
        super().__init__(GraphTable)
