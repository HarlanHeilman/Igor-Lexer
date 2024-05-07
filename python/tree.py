import itertools
import re
from enum import Enum
from pathlib import Path


class NodeType(Enum):
    FUNCTION = 1
    PROCEDURE = 2
    VARIABLE = 3


class Node:
    def __init__(self, name, node_type: NodeType, index):
        self.name = name
        self.node_type = node_type
        self.index = index
        self.children = set()

    def add_child(self, child):
        if self.node_type == NodeType.FUNCTION and isinstance(
            child, (FunctionNode, VariableNode)
        ):
            self.children.add(child)
        elif self.node_type == NodeType.PROCEDURE and isinstance(
            child, (FunctionNode, ProcedureNode)
        ):
            self.children.add(child)
        elif self.node_type == NodeType.VARIABLE and isinstance(
            child, (OperationNode, FunctionNode)
        ):
            self.children.add(child)
        else:
            raise ValueError("Invalid child type for this node")

    def __str__(self):
        return self._str_builder(0)

    def _str_builder(self, level):
        indent = "━"
        s = ""
        if level != 0:
            s = "   " * (level - 1) + "┗" + indent + "▶" f"{self.name} ({level})\n"
        for child in self.children:
            s += child._str_builder(level + 1)
        return s


class FunctionNode(Node):
    def __init__(self, name, index):
        super().__init__(name, NodeType.FUNCTION, index)
        self.variables = set()
        self.returns = set()
        self.calls = set()


class ProcedureNode(Node):
    def __init__(self, name, index):
        super().__init__(name, NodeType.PROCEDURE, index)


class VariableNode(Node):
    def __init__(self, name, index):
        super().__init__(name, NodeType.VARIABLE, index)


class OperationNode(Node):
    def __init__(self, name, index):
        super().__init__(name, NodeType.VARIABLE, index)


def parse_igor_procedures():
    """
    Parse Igor Pro procedures and build a tree structure representing the call hierarchy.

    Looks for procedures in the default Igor Pro User Procedures folder.
     * Home/Documents/WaveMetrics/Igor Pro 9 User Files/User Procedures
     * Home/Documents/WaveMetrics/Igor Pro 9 User Files/Igor Procedures

    Returns:
        A tree structure representing the call hierarchy of Igor Pro procedures.
    """

    user = (
        Path.home()
        / "Documents"
        / "WaveMetrics"
        / "Igor Pro 9 User Files"
        / "User Procedures"
    )
    igor = (
        Path.home()
        / "Documents"
        / "WaveMetrics"
        / "Igor Pro 9 User Files"
        / "Igor Procedures"
    )
    # Iterate though user first as it has higher loading priority
    files = list(itertools.chain(igor.glob("*.ipf"), user.glob("*.ipf")))

    func_pattern = re.compile(r"^Function\s+(\w+)")
    include_pattern = re.compile(r"^#include\s+\"(.+)\"")

    tree_pieces = {}  # dictionary to store compleated tree pieces

    def parse_procedure(file_path):
        """
        Iterate though lines and build the tree structure from the functions and includes.
        """
        # Construct the the procedure node
        procedure_name = file_path.stem
        procedure_node = ProcedureNode(procedure_name, len(tree_pieces))

        with open(file_path, "r") as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            # Check for include statements
            match = include_pattern.match(line)
            if match:
                include_file = match.group(1)
                if include_file not in tree_pieces:
                    include_file_path = user / f"{include_file}.ipf"
                    if include_file_path.exists():
                        child_procs = parse_procedure(include_file_path)
                        procedure_node.add_child(child_procs)
                    else:
                        procedure_node.add_child(ProcedureNode(include_file, None))
                else:
                    procedure_node.add_child(tree_pieces[include_file])

            # Check for function definitions
            match = func_pattern.match(line)
            if match:
                function_name = match.group(1)
                function_node = FunctionNode(function_name, i)
                procedure_node.add_child(function_node)
        tree_pieces[procedure_name] = procedure_node
        return procedure_node

    root = ProcedureNode("root", None)  # Create a root node

    for i, file in enumerate(files):
        if file.stem not in tree_pieces:
            proc_node = parse_procedure(file)
            root.add_child(proc_node)

    return root


if __name__ == "__main__":
    root = parse_igor_procedures()
    clustering_procs = next(
        filter(lambda x: x.name == "clusteringPanel v1", root.children), None
    )
    print(clustering_procs)
