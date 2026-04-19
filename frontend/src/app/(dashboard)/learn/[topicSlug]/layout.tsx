export default async function TopicLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ topicSlug: string }>;
}) {
  const { topicSlug } = await params;
  return <>{children}</>;
}
