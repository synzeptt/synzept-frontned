MOCK_SKILLS = [
  {
    "name": "Launch Planner",
    "description": "Turn a product vision into a crisp launch plan.",
    "category": "Startup",
    "inputs": ["mission", "goals", "timeline"],
    "outputs": ["launch plan", "milestones"],
    "requiredContext": ["mission", "goals"],
    "requiredPermissions": ["read:mission"],
    "steps": ["Gather mission context", "Create milestones", "Present plan for approval"],
    "completionCriteria": ["Plan reviewed", "Milestones stored"]
  },
  {
    "name": "Product Review",
    "description": "Summarize progress and identify the next product decision.",
    "category": "Startup",
    "inputs": ["project", "notes", "timeline"],
    "outputs": ["review summary", "next decision"],
    "requiredContext": ["project", "notes"],
    "requiredPermissions": ["read:project"],
    "steps": ["Gather project context", "Review recent notes", "Suggest the next decision"],
    "completionCriteria": ["Decision captured", "Review attached to memory"]
  },
  {
    "name": "Customer Interview Planner",
    "description": "Prepare for a high-signal customer conversation.",
    "category": "Startup",
    "inputs": ["goal", "memories", "people"],
    "outputs": ["interview plan", "questions"],
    "requiredContext": ["goal", "memories"],
    "requiredPermissions": ["read:memory"],
    "steps": ["Gather relevant memories", "Draft interview questions", "Present the plan"],
    "completionCriteria": ["Questions approved", "Plan stored"]
  },
  {
    "name": "Feature Prioritizer",
    "description": "Rank feature ideas by impact and effort.",
    "category": "Startup",
    "inputs": ["ideas", "goals", "context"],
    "outputs": ["prioritized list"],
    "requiredContext": ["ideas", "goals"],
    "requiredPermissions": ["read:goals"],
    "steps": ["Gather feature ideas", "Score by impact and effort", "Recommend the next move"],
    "completionCriteria": ["Ranking finalized"]
  },
  {
    "name": "Investor Update",
    "description": "Create a concise progress update for investors or advisors.",
    "category": "Startup",
    "inputs": ["milestones", "metrics", "context"],
    "outputs": ["update draft"],
    "requiredContext": ["milestones", "metrics"],
    "requiredPermissions": ["read:metrics"],
    "steps": ["Collect milestones", "Highlight evidence", "Draft update"],
    "completionCriteria": ["Draft ready"]
  },
  {
    "name": "Daily Planning",
    "description": "Turn the day's context into a clear plan.",
    "category": "Productivity",
    "inputs": ["mission", "tasks", "open_loops"],
    "outputs": ["daily plan", "top 3 actions"],
    "requiredContext": ["mission", "tasks"],
    "requiredPermissions": ["read:tasks"],
    "steps": ["Gather current context", "Pick top actions", "Present for approval"],
    "completionCriteria": ["Plan approved"]
  },
  {
    "name": "Weekly Review",
    "description": "Review the week and identify the biggest gain.",
    "category": "Productivity",
    "inputs": ["timeline", "goals", "notes"],
    "outputs": ["review summary"],
    "requiredContext": ["timeline", "goals"],
    "requiredPermissions": ["read:timeline"],
    "steps": ["Gather week context", "Summarize wins and blockers", "Recommend next focus"],
    "completionCriteria": ["Review stored"]
  },
  {
    "name": "Open Loop Cleanup",
    "description": "Help resolve the most important unresolved work.",
    "category": "Productivity",
    "inputs": ["open_loops", "tasks", "goals"],
    "outputs": ["cleanup plan"],
    "requiredContext": ["open_loops", "tasks"],
    "requiredPermissions": ["read:open_loops"],
    "steps": ["Collect unresolved items", "Prioritize by leverage", "Create cleanup plan"],
    "completionCriteria": ["Plan approved"]
  },
  {
    "name": "Project Health Check",
    "description": "Assess the health of a project and recommend the next move.",
    "category": "Productivity",
    "inputs": ["project", "tasks", "notes"],
    "outputs": ["health summary", "recommended action"],
    "requiredContext": ["project", "tasks"],
    "requiredPermissions": ["read:project"],
    "steps": ["Gather project state", "Assess health", "Recommend next action"],
    "completionCriteria": ["Recommendation written"]
  },
  {
    "name": "Organize Notes",
    "description": "Structure raw notes into a useful knowledge artifact.",
    "category": "Knowledge",
    "inputs": ["notes", "context"],
    "outputs": ["organized notes"],
    "requiredContext": ["notes"],
    "requiredPermissions": ["read:notes"],
    "steps": ["Gather notes", "Cluster ideas", "Create a structured summary"],
    "completionCriteria": ["Notes organized"]
  },
  {
    "name": "Build Knowledge Graph",
    "description": "Connect related notes, memories, and projects into a knowledge graph.",
    "category": "Knowledge",
    "inputs": ["notes", "memories", "projects"],
    "outputs": ["graph summary"],
    "requiredContext": ["notes", "memories"],
    "requiredPermissions": ["read:memory"],
    "steps": ["Gather relevant context", "Infer links", "Present graph summary"],
    "completionCriteria": ["Graph summary stored"]
  },
  {
    "name": "Find Missing Context",
    "description": "Find the missing context needed to complete a task.",
    "category": "Knowledge",
    "inputs": ["task", "memories", "notes"],
    "outputs": ["missing-context list"],
    "requiredContext": ["task", "memories"],
    "requiredPermissions": ["read:memory"],
    "steps": ["Inspect task context", "Find gaps", "Recommend missing information"],
    "completionCriteria": ["Context gaps listed"]
  },
  {
    "name": "Habit Review",
    "description": "Review current habits and suggest the next improvement.",
    "category": "Personal",
    "inputs": ["habits", "timeline"],
    "outputs": ["habit insight"],
    "requiredContext": ["habits"],
    "requiredPermissions": ["read:habits"],
    "steps": ["Review habits", "Identify momentum pattern", "Suggest the next step"],
    "completionCriteria": ["Action suggested"]
  },
  {
    "name": "Goal Review",
    "description": "Evaluate current goals and the next highest-leverage move.",
    "category": "Personal",
    "inputs": ["goals", "progress"],
    "outputs": ["goal review"],
    "requiredContext": ["goals"],
    "requiredPermissions": ["read:goals"],
    "steps": ["Gather goals", "Assess progress", "Recommend the next action"],
    "completionCriteria": ["Review documented"]
  },
  {
    "name": "Reading Summary",
    "description": "Summarize a reading or article into actionable takeaways.",
    "category": "Personal",
    "inputs": ["article", "notes"],
    "outputs": ["summary", "takeaways"],
    "requiredContext": ["article"],
    "requiredPermissions": ["read:notes"],
    "steps": ["Read and extract insights", "Summarize the article", "Store takeaways"],
    "completionCriteria": ["Summary stored"]
  }
]
