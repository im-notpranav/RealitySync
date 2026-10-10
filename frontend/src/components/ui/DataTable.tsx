import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { cn } from "../../lib/cn";
import { Skeleton } from "./Feedback";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  /** Makes the column sortable. */
  sortValue?: (row: T) => number | string;
  className?: string;
  /** Hidden below this breakpoint. */
  hideBelow?: "md" | "lg" | "xl";
}

export interface DataTableProps<T> {
  rows: T[] | undefined;
  columns: Column<T>[];
  rowKey: (row: T) => string;
  caption: string;
  onRowClick?: (row: T) => void;
  /** Accessible name for the row action ("Open finding: …"). */
  rowLabel?: (row: T) => string;
  selectedKey?: string | null;
  /** Rows that just arrived get the 1.2 s moss flash (06 §8). */
  flashKeys?: ReadonlySet<string>;
  loading?: boolean;
  empty?: ReactNode;
  defaultSort?: { key: string; dir: "asc" | "desc" };
  className?: string;
}

const hideClass = { md: "max-md:hidden", lg: "max-lg:hidden", xl: "max-xl:hidden" } as const;

/** Paper table (06 §6): 56 px rows, no zebra, hover wash, sticky header, sortable headers. */
export function DataTable<T>({
  rows,
  columns,
  rowKey,
  caption,
  onRowClick,
  rowLabel,
  selectedKey,
  flashKeys,
  loading,
  empty,
  defaultSort,
  className,
}: DataTableProps<T>) {
  const [sort, setSort] = useState(defaultSort ?? null);

  const sorted = useMemo(() => {
    if (!rows || !sort) return rows;
    const column = columns.find((c) => c.key === sort.key);
    if (!column?.sortValue) return rows;
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const av = column.sortValue!(a);
      const bv = column.sortValue!(b);
      return (av > bv ? 1 : av < bv ? -1 : 0) * factor;
    });
  }, [rows, sort, columns]);

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[640px] border-collapse text-left">
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 z-[1] bg-paper">
          <tr>
            {columns.map((column) => {
              const active = sort?.key === column.key;
              return (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={active ? (sort!.dir === "asc" ? "ascending" : "descending") : undefined}
                  className={cn(
                    "h-10 px-5 text-caption font-medium text-ink-500 first:pl-5",
                    column.hideBelow && hideClass[column.hideBelow],
                    column.className,
                  )}
                >
                  {column.sortValue ? (
                    <button
                      type="button"
                      onClick={() =>
                        setSort((current) =>
                          current?.key === column.key
                            ? { key: column.key, dir: current.dir === "asc" ? "desc" : "asc" }
                            : { key: column.key, dir: "desc" },
                        )
                      }
                      className="-mx-1 inline-flex items-center gap-1 rounded-[6px] px-1 transition-colors duration-fast pointer:hover:text-ink-900"
                    >
                      {column.header}
                      {active ? (
                        sort!.dir === "asc" ? (
                          <ArrowUp size={12} aria-hidden="true" />
                        ) : (
                          <ArrowDown size={12} aria-hidden="true" />
                        )
                      ) : (
                        <ChevronsUpDown size={12} aria-hidden="true" className="opacity-50" />
                      )}
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {loading || !sorted
            ? Array.from({ length: 5 }, (_, index) => (
                <tr key={index} className="border-t border-ink-100">
                  {columns.map((column) => (
                    <td key={column.key} className={cn("h-14 px-5", column.hideBelow && hideClass[column.hideBelow])}>
                      <Skeleton className="h-4 w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            : null}
          {!loading && sorted && sorted.length === 0 ? (
            <tr className="border-t border-ink-100">
              <td colSpan={columns.length}>{empty}</td>
            </tr>
          ) : null}
          {!loading &&
            sorted?.map((row) => {
              const key = rowKey(row);
              const selected = selectedKey === key;
              return (
                <tr
                  key={key}
                  className={cn(
                    "relative border-t border-ink-100 transition-colors duration-fast",
                    onRowClick && "pointer:hover:bg-ink-100",
                    selected && "bg-ink-100 shadow-[inset_2px_0_0_var(--ink-950)]",
                    flashKeys?.has(key) && "row-flash",
                  )}
                >
                  {columns.map((column, index) => (
                    <td
                      key={column.key}
                      className={cn(
                        "h-14 px-5 py-3 align-middle text-body text-ink-900",
                        column.hideBelow && hideClass[column.hideBelow],
                        column.className,
                      )}
                    >
                      {index === 0 && onRowClick ? (
                        // Stretched button: the whole row is one keyboard-reachable target.
                        <button
                          type="button"
                          aria-label={rowLabel?.(row) ?? "Open row"}
                          onClick={() => onRowClick(row)}
                          className="absolute inset-0 rounded-[2px] focus-visible:outline-offset-[-2px]"
                        />
                      ) : null}
                      {column.cell(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
        </tbody>
      </table>
    </div>
  );
}
