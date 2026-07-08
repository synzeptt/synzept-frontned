export type SynzeptObjectType = "goal" | "decision" | "task";
export type ReviewStatus = "pending" | "approved" | "rejected";

export type ObjectRelationship = {
  type: "related_to" | "created_from" | "supports" | "blocks";
  targetId: string;
  confidence: number;
  evidence?: string;
};

export type SynzeptObject = {
  id: string;
  type: SynzeptObjectType;
  title: string;
  summary: string;
  confidence: number;
  source: string;
  createdAt: string;
  updatedAt: string;
  metadata: Record<string, string | number | boolean | string[]>;
  relationships: ObjectRelationship[];
};

export type PipelineStage = {
  name: string;
  status: string;
  summary: string;
  objectCount: number;
};

export type ReviewItem = {
  id: string;
  object: SynzeptObject;
  status: ReviewStatus;
  impact: "low" | "medium" | "high";
  extractor: string;
  rationale: string;
  createdAt: string;
};

export type GraphEdge = {
  id: string;
  sourceId: string;
  targetId: string;
  type: ObjectRelationship["type"];
  confidence: number;
  evidence: string;
};

export type KnowledgeGraph = {
  nodes: SynzeptObject[];
  edges: GraphEdge[];
};

export type IntelligenceDatasetMock = {
  conversation: {
    conversationId: string;
    title: string;
    transcript: string;
  };
  stages: PipelineStage[];
  reviewItems: ReviewItem[];
  approvedObjects: SynzeptObject[];
  graph: KnowledgeGraph;
};
