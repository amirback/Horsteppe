import { ProjectStatus } from "./project-status";

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProjectStatus projectId={id} />;
}
