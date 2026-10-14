import { Copy, KeyRound, Plus } from "lucide-react";
import { useId, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  Avatar,
  Button,
  Card,
  DataTable,
  Dialog,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Pill,
  Tabs,
  TabsContent,
  TabsList,
  toast,
} from "../../components/ui";
import { useAuditLog, useUsers } from "../../lib/api/queries";
import { humanize, relativeTime } from "../../lib/format";
import { hasRole, useSession } from "../../store/session";

function Profile() {
  const user = useSession((state) => state.user);
  const ids = { current: useId(), next: useId() };
  const [next, setNext] = useState("");
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="flex items-center gap-4">
        <Avatar name={user?.fullName ?? "Guest"} tone="user" />
        <div>
          <p className="text-h3 text-ink-950">{user?.fullName}</p>
          <p className="text-small text-ink-500">Role: {humanize(user?.role ?? "viewer")}</p>
        </div>
      </Card>
      <Card>
        <h2 className="mb-4 text-h3 text-ink-950">Change password</h2>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            toast({
              title: "Password changed",
              description: "Other sessions were signed out.",
              tone: "success",
            });
            setNext("");
          }}
        >
          <Field label="Current password" htmlFor={ids.current}>
            <Input id={ids.current} type="password" autoComplete="current-password" required />
          </Field>
          <Field label="New password" htmlFor={ids.next} hint="At least 12 characters.">
            <Input
              id={ids.next}
              type="password"
              autoComplete="new-password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              minLength={12}
              required
            />
          </Field>
          <Button type="submit" variant="primary" disabled={next.length < 12} className="self-end">
            Change password
          </Button>
        </form>
      </Card>
    </div>
  );
}

function Users() {
  const { data, isLoading } = useUsers();
  return (
    <Card className="overflow-hidden p-0">
      <DataTable
        caption="Users"
        rows={data}
        loading={isLoading}
        rowKey={(u) => u.id}
        columns={[
          {
            key: "name",
            header: "User",
            cell: (u) => (
              <div className="flex items-center gap-3">
                <Avatar name={u.full_name} size="sm" />
                <div>
                  <p className="font-medium text-ink-950">{u.full_name}</p>
                  <p className="text-small text-ink-500">{u.email}</p>
                </div>
              </div>
            ),
          },
          {
            key: "role",
            header: "Role",
            cell: (u) => (
              <Pill tone={u.role === "admin" ? "indigo" : u.role === "analyst" ? "sky" : "neutral"}>
                {humanize(u.role)}
              </Pill>
            ),
          },
          {
            key: "status",
            header: "Status",
            cell: (u) => (
              <Pill tone={u.is_active ? "moss" : "neutral"}>{u.is_active ? "Active" : "Deactivated"}</Pill>
            ),
          },
          {
            key: "login",
            header: "Last sign-in",
            hideBelow: "md",
            cell: (u) => (
              <span className="text-small text-ink-500">
                {u.last_login_at ? relativeTime(u.last_login_at) : "Never"}
              </span>
            ),
          },
        ]}
      />
    </Card>
  );
}

function ApiKeys() {
  const [open, setOpen] = useState(false);
  // Shown once after creation (04 §3). Demo value only — never a real credential.
  const secret = "rs_live_demo_0000000000";
  return (
    <>
      <Card>
        <EmptyState
          icon={KeyRound}
          title="No API keys yet"
          description="Keys let a source system send events to the ingest API. The secret is shown once."
          action={
            <Button variant="primary" onClick={() => setOpen(true)}>
              <Plus size={16} aria-hidden="true" /> Create key
            </Button>
          }
        />
      </Card>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="API key created"
        description="Copy it now — you won't be able to see it again."
        footer={
          <Button variant="primary" onClick={() => setOpen(false)}>
            Done
          </Button>
        }
      >
        <div className="flex items-center gap-2 rounded-control bg-ink-100 p-3">
          <code className="min-w-0 flex-1 truncate text-small text-ink-950">{secret}</code>
          <Button
            size="sm"
            surface="paper"
            onClick={() => {
              void navigator.clipboard?.writeText(secret);
              toast({ title: "Copied to clipboard" });
            }}
          >
            <Copy size={14} aria-hidden="true" /> Copy
          </Button>
        </div>
      </Dialog>
    </>
  );
}

function Audit() {
  const { data, isLoading } = useAuditLog();
  return (
    <Card className="overflow-hidden p-0">
      <DataTable
        caption="Audit log"
        rows={data}
        loading={isLoading}
        rowKey={(a) => a.id}
        columns={[
          {
            key: "action",
            header: "Action",
            cell: (a) => <span className="font-medium text-ink-950">{a.action}</span>,
          },
          {
            key: "actor",
            header: "By",
            cell: (a) => <span className="text-small text-ink-700">{a.actor}</span>,
          },
          {
            key: "target",
            header: "Target",
            hideBelow: "md",
            cell: (a) => (
              <span className="text-small text-ink-500">
                {humanize(a.target_type)} <span className="tabular">{a.target_id}</span>
              </span>
            ),
          },
          {
            key: "when",
            header: "When",
            cell: (a) => <span className="text-small text-ink-500">{relativeTime(a.created_at)}</span>,
          },
        ]}
      />
    </Card>
  );
}

export function Component() {
  const user = useSession((state) => state.user);
  const [searchParams, setSearchParams] = useSearchParams();
  const items = [
    { value: "profile", label: "Profile" },
    ...(hasRole(user, "admin")
      ? [
          { value: "users", label: "Users" },
          { value: "keys", label: "API keys" },
          { value: "audit", label: "Audit log" },
        ]
      : []),
  ];
  // The tab lives in the URL so the account menu can link to `?tab=users` (T-008); unknown or
  // unavailable tabs fall back to Profile.
  const requested = searchParams.get("tab");
  const tab = items.some((item) => item.value === requested) ? (requested as string) : "profile";
  const setTab = (value: string) =>
    setSearchParams(value === "profile" ? {} : { tab: value }, { replace: true });
  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="Your profile, and for admins: users, API keys and the audit log"
      />
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList items={items} value={tab} label="Settings sections" layoutId="settings-tabs" />
        <TabsContent value="profile" className="mt-5 outline-none">
          <Profile />
        </TabsContent>
        <TabsContent value="users" className="mt-5 outline-none">
          <Users />
        </TabsContent>
        <TabsContent value="keys" className="mt-5 outline-none">
          <ApiKeys />
        </TabsContent>
        <TabsContent value="audit" className="mt-5 outline-none">
          <Audit />
        </TabsContent>
      </Tabs>
    </>
  );
}
