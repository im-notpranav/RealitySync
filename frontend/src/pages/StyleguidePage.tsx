import { Bell, Download, Plus } from "lucide-react";

import { Avatar, Button, Card, IconButton, PageHeader } from "../components/ui";

/** Development-only component gallery (02 §3.1). T-005 and T-043 add every component and state. */
export function Component() {
  return (
    <>
      <PageHeader
        title="Styleguide"
        subtitle="Design system v2 (06). Development only."
        actions={
          <>
            <Button>
              <Download size={16} aria-hidden="true" />
              Export report
            </Button>
            <Button variant="primary">
              <Plus size={16} aria-hidden="true" />
              New investigation
            </Button>
          </>
        }
      />
      <Card className="flex flex-wrap items-center gap-3">
        <Button variant="primary">Primary</Button>
        <Button surface="paper">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="danger">Danger</Button>
        <Button variant="destructive">Destructive</Button>
        <Button variant="primary" disabled>
          Disabled
        </Button>
        <IconButton label="Alerts" surface="paper">
          <Bell size={18} aria-hidden="true" />
        </IconButton>
        <Avatar name="Demo Admin" tone="user" />
        <Avatar name="Jonathan Smith" />
      </Card>
    </>
  );
}
