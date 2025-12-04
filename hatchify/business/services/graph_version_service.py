from hatchify.business.models.graph_version import GraphVersionTable
from hatchify.business.repositories.graph_version_repository import GraphVersionRepository
from hatchify.business.services.base.generic_service import GenericService


class GraphVersionService(GenericService[GraphVersionTable]):

    def __init__(self):
        super().__init__(GraphVersionTable, GraphVersionRepository)
