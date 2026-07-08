"use client";

import { PageFrame } from "@frontend/components/layout/page-frame";
import { MissionHeader } from "@frontend/components/mission/mission-header";
import { MissionLayout } from "@frontend/components/mission/mission-layout";
import { MissionProgress } from "@frontend/components/mission/mission-progress";
import { MissionHealth } from "@frontend/components/mission/mission-health";
import { MissionTimeline } from "@frontend/components/mission/mission-timeline";
import { MissionProjects } from "@frontend/components/mission/mission-projects";
import { MissionGoals } from "@frontend/components/mission/mission-goals";
import { MissionOpenLoops } from "@frontend/components/mission/mission-open-loops";
import { MissionInsights } from "@frontend/components/mission/mission-insights";
import { MissionRecommendations } from "@frontend/components/mission/mission-recommendations";
import { sampleMission } from "@/lib/sample-data";

export function MissionPage() {
  return (
    <PageFrame eyebrow="Mission System" title="Missions">
      <MissionLayout>
        <div className="space-y-6">
          <MissionHeader mission={sampleMission} />
          <MissionProgress mission={sampleMission} />
          <MissionHealth mission={sampleMission} />
          <MissionProjects projects={sampleMission.projects} />
          <MissionGoals goals={sampleMission.goals} />
        </div>

        <div className="space-y-6">
          <MissionTimeline timeline={sampleMission.timeline} />
          <MissionOpenLoops loops={sampleMission.openLoops} />
          <MissionInsights insights={sampleMission.insights} />
          <MissionRecommendations recommendations={sampleMission.recommendations} />
        </div>
      </MissionLayout>
    </PageFrame>
  );
}
