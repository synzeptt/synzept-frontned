export type DecisionGraphNode = {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp?: string;
  confidence?: number;
  status?: string;
  importance?: string;
  metadata: Record<string, string | number | boolean>;
  x: number;
  y: number;
};

export type DecisionGraphEdge = {
  id: string;
  source: string;
  target: string;
  relationship: string;
  label: string;
  strength: number;
  evidence: string[];
};

export type DecisionGraphInsight = {
  id: string;
  type: string;
  title: string;
  summary: string;
  supportingConnectionIds: string[];
  confidence: number;
  impact: number;
};

export type DecisionGraphChain = {
  id: string;
  title: string;
  nodeIds: string[];
  edgeIds: string[];
  summary: string;
};

export type DecisionGraphData = {
  generatedAt: string;
  supportedRelationships: string[];
  nodes: DecisionGraphNode[];
  edges: DecisionGraphEdge[];
  insights: DecisionGraphInsight[];
  chains: DecisionGraphChain[];
};
