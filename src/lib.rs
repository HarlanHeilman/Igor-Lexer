use std::collections::HashSet;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use regex::Regex;

#[derive(Debug, Eq, PartialEq, Hash)]
enum NodeType {
    Function,
    Procedure,
    Variable,
}

#[derive(Debug, Eq, PartialEq, Hash)]
struct Node {
    name: String,
    node_type: NodeType,
    children: HashSet<Node>,
}

impl Node {
    fn new(name: String, node_type: NodeType) -> Self {
        Node {
            name,
            node_type,
            children: HashSet::new(),
        }
    }

    fn add_child(&mut self, child: Node) {
        self.children.insert(child);
    }

    fn to_string(&self, level: usize) -> String {
        let mut s = format!("{}{} ({:?})\n", "   ".repeat(level), self.name, self.node_type);
        for child in &self.children {
            s += &child.to_string(level + 1);
        }
        s
    }
}

fn parse_igor_procedures() -> Node {
    let user = Path::new("/home/Documents/WaveMetrics/Igor Pro 9 User Files/User Procedures");
    let igor = Path::new("/home/Documents/WaveMetrics/Igor Pro 9 User Files/Igor Procedures");
    let mut files = Vec::new();
    files.extend(
        igor.read_dir()
            .expect("Failed to read directory")
            .map(|entry| entry.unwrap().path()),
    );
    files.extend(
        user.read_dir()
            .expect("Failed to read directory")
            .map(|entry| entry.unwrap().path()),
    );

    let func_pattern = Regex::new(r"^Function\s+(\w+)").unwrap();
    let include_pattern = Regex::new(r#"^#include\s+"(.+)""#).unwrap();

    let mut tree_pieces = HashSet::new();

    fn parse_procedure(file_path: &Path, tree_pieces: &mut HashSet<String>) -> Node {
        let procedure_name = file_path.file_stem().unwrap().to_string_lossy().into_owned();
        let mut procedure_node = Node::new(procedure_name.clone(), NodeType::Procedure);

        let file = File::open(file_path).expect("Failed to open file");
        let reader = BufReader::new(file);

        for (i, line) in reader.lines().enumerate() {
            let line = line.unwrap();
            if let Some(include_file) = include_pattern.captures(&line).map(|c| c.get(1).unwrap().as_str().to_string()) {
                if !tree_pieces.contains(&include_file) {
                    let include_file_path = user.join(format!("{}.ipf", &include_file));
                    if include_file_path.exists() {
                        let mut child_procs = parse_procedure(&include_file_path, tree_pieces);
                        procedure_node.add_child(child_procs);
                    } else {
                        procedure_node.add_child(Node::new(include_file.to_string(), NodeType::Procedure));
                    }
                } else {
                    procedure_node.add_child(Node::new(include_file.to_string(), NodeType::Procedure));
                }
            }

            if let Some(func_name) = func_pattern.captures(&line).map(|c| c.get(1).unwrap().as_str().to_string()) {
                procedure_node.add_child(Node::new(func_name, NodeType::Function));
            }
        }

        tree_pieces.insert(procedure_name);
        procedure_node
    }

    let mut root = Node::new("root".to_string(), NodeType::Procedure);  // Create a root node

    for file in files {
        if !tree_pieces.contains(file.file_stem().unwrap().to_str().unwrap()) {
            let proc_node = parse_procedure(&file, &mut tree_pieces);
            root.add_child(proc_node);
        }
    }

    root
}

fn main() {
    let root = parse_igor_procedures();
    let clustering_procs = root.children.iter().find(|x| x.name == "clusteringPanel v1");
    if let Some(node) = clustering_procs {
        println!("{}", node.to_string(0));
    } else {
        println!("Node not found");
    }
}
