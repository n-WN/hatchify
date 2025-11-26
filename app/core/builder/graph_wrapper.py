from typing import List

from loguru import logger
from strands.agent import AgentResult
from strands.multiagent.graph import Graph, GraphNode, GraphBuilder
from strands.types.content import ContentBlock


class GraphWrapper(Graph):
    def _build_node_input(self, node: GraphNode) -> list[ContentBlock]:
        """Build input text for a node based on dependency outputs.

        Example formatted output:
        ```
        Original Task: Analyze the quarterly sales data and create a summary report

        Inputs from previous nodes:

        From data_processor:
          - Agent: Sales data processed successfully. Found 1,247 transactions totaling $89,432.
          - Agent: Key trends: 15% increase in Q3, top product category is Electronics.

        From validator:
          - Agent: Data validation complete. All records verified, no anomalies detected.
        ```
        """
        # Get satisfied dependencies
        dependency_results = {}
        for edge in self.edges:
            if (
                    edge.to_node == node
                    and edge.from_node in self.state.completed_nodes
                    and edge.from_node.node_id in self.state.results
            ):
                if edge.should_traverse(self.state):
                    dependency_results[edge.from_node.node_id] = self.state.results[edge.from_node.node_id]

        if not dependency_results:
            # No dependencies - return task as ContentBlocks
            if isinstance(self.state.task, str):
                return [ContentBlock(text=self.state.task)]
            else:
                return self.state.task

        # Combine task with dependency outputs
        node_input = []

        # Add original task
        if isinstance(self.state.task, str):
            node_input.append(ContentBlock(text=f"Original Task: {self.state.task}"))
        else:
            # Add task content blocks with a prefix
            node_input.append(ContentBlock(text="Original Task:"))
            node_input.extend(self.state.task)

        # Add dependency outputs
        node_input.append(ContentBlock(text="\nInputs from previous nodes:"))

        for dep_id, node_result in dependency_results.items():
            node_input.append(ContentBlock(text=f"\nFrom {dep_id}:"))
            # Get all agent results from this node (flattened if nested)
            agent_results: List[AgentResult] = node_result.get_agent_results()
            for result in agent_results:
                agent_name = getattr(result, "agent_name", dep_id)
                result_text = str(result)
                if not result_text and result.structured_output:
                    result_text = result.structured_output.model_dump_json()
                else:
                    logger.warning(f"{agent_name} agent has no output!")
                    result_text = "[block]"
                node_input.append(ContentBlock(text=f"  - {agent_name}: {result_text}"))

        return node_input


class GraphBuilderAdapter(GraphBuilder):

    def build(self) -> "GraphWrapper":
        """Build and validate the graph with configured settings."""
        if not self.nodes:
            raise ValueError("Graph must contain at least one node")

        # Auto-detect entry points if none specified
        if not self.entry_points:
            self.entry_points = {node for node_id, node in self.nodes.items() if not node.dependencies}
            logger.debug(
                "entry_points=<%s> | auto-detected entrypoints", ", ".join(node.node_id for node in self.entry_points)
            )
            if not self.entry_points:
                raise ValueError("No entry points found - all nodes have dependencies")

        # Validate entry points and check for cycles
        self._validate_graph()

        return GraphWrapper(
            nodes=self.nodes.copy(),
            edges=self.edges.copy(),
            entry_points=self.entry_points.copy(),
            max_node_executions=self._max_node_executions,
            execution_timeout=self._execution_timeout,
            node_timeout=self._node_timeout,
            reset_on_revisit=self._reset_on_revisit,
            session_manager=self._session_manager,
            hooks=self._hooks,
            id=self._id,
        )
