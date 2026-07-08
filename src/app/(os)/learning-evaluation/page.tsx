import { PageFrame } from "@frontend/components/layout/page-frame";
import { LearningEvaluationView } from "@/components/learning-evaluation/LearningEvaluationView";

export default function LearningEvaluationPage() {
  return (
    <PageFrame eyebrow="Sprint 3" title="Learning Evaluation">
      <LearningEvaluationView />
    </PageFrame>
  );
}
