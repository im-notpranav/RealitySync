import { Compass } from "lucide-react";

import { ButtonLink, Card, PageHeader } from "../components/ui";

export function Component() {
  return (
    <>
      <PageHeader title="Page not found" subtitle="The address may be mistyped or the page may have moved." />
      <Card className="flex flex-col items-center gap-3 px-6 py-16 text-center">
        <span className="grid size-12 place-items-center rounded-pill bg-neutral-bg text-neutral-fg">
          <Compass size={20} strokeWidth={1.75} aria-hidden="true" />
        </span>
        <h2 className="text-h3 text-ink-950">Nothing lives here</h2>
        <ButtonLink to="/" surface="paper">
          Back to overview
        </ButtonLink>
      </Card>
    </>
  );
}
