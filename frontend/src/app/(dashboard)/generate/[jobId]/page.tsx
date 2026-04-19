export default async function GenerationJobPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">Generating Curriculum...</h1>
      <div className="mt-8 rounded-xl border border-border bg-black/50 p-6 font-mono text-sm">
        <p className="text-muted-foreground">Job ID: {jobId}</p>
        <p className="mt-2 text-muted-foreground">Waiting for generation progress...</p>
      </div>
    </div>
  );
}
